"""Async client for the 3x-ui-style panel API.

The endpoints implemented here mirror the spec the user provided:

    POST /panel/api/clients/add?email=<email>     body: { client: {...}, inboundIds: [...] }
    GET  /panel/api/clients/get/{email}           -> { success, obj }
    GET  /panel/api/clients/subLinks/{subId}      -> { success, obj: [link, ...] }

Auth is sent as a Bearer token in the `Authorization` header. If your fork
uses a different header (e.g. `X-API-Token`), edit `_auth_headers` below.
"""

from __future__ import annotations

import logging
import time
import uuid as _uuid
from dataclasses import dataclass
from typing import Any

import httpx


log = logging.getLogger(__name__)

GIB_IN_BYTES = 1024 ** 3
DAY_IN_SECONDS = 24 * 60 * 60
REQUEST_TIMEOUT = 20.0  # seconds


class XuiError(RuntimeError):
    """Raised when the panel returns success=false or an HTTP error."""


@dataclass
class ProvisionedClient:
    email: str
    sub_id: str | None
    client_uuid: str | None
    sub_links: list[str]
    raw_get_response: dict[str, Any] | None = None


@dataclass
class ClientUsage:
    """Snapshot of a client's traffic + limits from the panel.

    All byte fields are best-effort: different 3x-ui forks return the
    information in slightly different shapes, so the helper that builds
    this is defensive and may return zeros if a field can't be found.
    """
    up_bytes: int
    down_bytes: int
    total_bytes: int        # totalGB limit, in bytes (0 = unlimited)
    expiry_time_ms: int     # 0 = never
    enable: bool

    @property
    def used_bytes(self) -> int:
        return max(0, self.up_bytes + self.down_bytes)

    @property
    def remaining_bytes(self) -> int:
        if self.total_bytes <= 0:
            return 0  # unlimited; caller treats this specially
        return max(0, self.total_bytes - self.used_bytes)

    @property
    def is_unlimited_traffic(self) -> bool:
        return self.total_bytes <= 0

    @property
    def is_never_expires(self) -> bool:
        return self.expiry_time_ms <= 0


def _auth_headers(api_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_token}",
        "Accept": "application/json",
    }


def _expiry_ms_from_days(days: int) -> int:
    return int((time.time() + days * DAY_IN_SECONDS) * 1000)


def _gb_to_bytes(gb: int) -> int:
    return gb * GIB_IN_BYTES


def build_client_email(user_id: int, order_id: int) -> str:
    """A unique identifier for the 3x-ui client (panel uses 'email' as the key)."""
    return f"netfly_{user_id}_{order_id}"


def _extract_sub_id(obj: Any) -> str | None:
    """Look for a subId field in a possibly-nested response payload."""
    if isinstance(obj, dict):
        if "subId" in obj and obj["subId"]:
            return str(obj["subId"])
        for v in obj.values():
            found = _extract_sub_id(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _extract_sub_id(item)
            if found:
                return found
    return None


def _extract_int(obj: Any, *keys: str) -> int:
    """Walk a nested dict/list looking for the first key in `keys` with an int value."""
    if isinstance(obj, dict):
        for k in keys:
            if k in obj:
                try:
                    return int(obj[k])
                except (TypeError, ValueError):
                    pass
        for v in obj.values():
            n = _extract_int(v, *keys)
            if n:
                return n
    elif isinstance(obj, list):
        for item in obj:
            n = _extract_int(item, *keys)
            if n:
                return n
    return 0


def _extract_bool(obj: Any, key: str, default: bool = True) -> bool:
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], bool):
            return obj[key]
        for v in obj.values():
            if isinstance(v, dict) and key in v and isinstance(v[key], bool):
                return v[key]
    return default


def _parse_usage(raw: Any) -> ClientUsage:
    """Best-effort extraction of usage stats from a get/list response payload.

    The 3x-ui `get/{email}` endpoint sometimes wraps the client object inside
    `obj` as a JSON-encoded string; handle both shapes.
    """
    if isinstance(raw, dict) and isinstance(raw.get("obj"), str):
        try:
            import json as _json
            raw = {"obj": _json.loads(raw["obj"])}
        except (ValueError, TypeError):
            pass

    return ClientUsage(
        up_bytes=_extract_int(raw, "up"),
        down_bytes=_extract_int(raw, "down"),
        total_bytes=_extract_int(raw, "totalGB", "total"),
        expiry_time_ms=_extract_int(raw, "expiryTime"),
        enable=_extract_bool(raw, "enable", default=True),
    )


def _extract_uuid(obj: Any) -> str | None:
    if isinstance(obj, dict):
        if "uuid" in obj and obj["uuid"]:
            return str(obj["uuid"])
        # Some panels nest it inside settings/clients JSON strings; best-effort only.
        for v in obj.values():
            found = _extract_uuid(v)
            if found:
                return found
    elif isinstance(obj, list):
        for item in obj:
            found = _extract_uuid(item)
            if found:
                return found
    return None


class XuiClient:
    def __init__(self, base_url: str, api_token: str) -> None:
        # NOTE: We deliberately do NOT use httpx's `base_url=` here.
        # httpx joins request paths using RFC 3986 rules, which means a
        # request path starting with "/" (all of ours do) replaces any path
        # component of base_url. That breaks 3x-ui panels that live behind a
        # secret path prefix like https://host/SECRET — the prefix would be
        # silently dropped. Instead we build the full URL by string concat.
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers=_auth_headers(api_token),
            timeout=REQUEST_TIMEOUT,
            verify=True,
        )

    async def __aenter__(self) -> "XuiClient":
        return self

    async def __aexit__(self, *_exc_info: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    # ---------- low-level ----------
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            path = "/" + path
        url = f"{self.base_url}{path}"
        try:
            resp = await self._client.request(method, url, params=params, json=json_body)
        except httpx.HTTPError as exc:
            raise XuiError(f"HTTP error calling {method} {url}: {exc}") from exc

        if resp.status_code >= 400:
            raise XuiError(
                f"{method} {url} returned HTTP {resp.status_code}: {resp.text[:300]}"
            )

        try:
            data = resp.json()
        except ValueError as exc:
            raise XuiError(f"Non-JSON response from {url}: {resp.text[:300]}") from exc

        if isinstance(data, dict) and data.get("success") is False:
            msg = data.get("msg") or "request failed"
            raise XuiError(f"{method} {url} failed: {msg}")
        return data if isinstance(data, dict) else {"obj": data}

    # ---------- public API ----------
    async def add_client(
        self,
        *,
        email: str,
        volume_gb: int,
        duration_days: int,
        inbound_ids: list[int],
        tg_user_id: int,
    ) -> dict[str, Any]:
        body = {
            "client": {
                "email": email,
                "totalGB": _gb_to_bytes(volume_gb),
                "expiryTime": _expiry_ms_from_days(duration_days),
                "tgId": tg_user_id,
                "limitIp": 0,
                "enable": True,
            },
            "inboundIds": list(inbound_ids),
        }
        return await self._request(
            "POST",
            "/panel/api/clients/add",
            params={"email": email},
            json_body=body,
        )

    async def get_client(self, email: str) -> dict[str, Any]:
        return await self._request("GET", f"/panel/api/clients/get/{email}")

    async def update_client(
        self,
        *,
        email: str,
        volume_gb: int | None = None,
        expiry_time_ms: int | None = None,
        tg_user_id: int | None = None,
        enable: bool | None = None,
    ) -> dict[str, Any]:
        """Update a client. Only non-None fields are sent.

        Note: 3x-ui's update endpoint as documented requires the email AND
        all fields it wants to overwrite. We always send `email` so the
        panel knows which client we mean.
        """
        body: dict[str, Any] = {"email": email}
        if volume_gb is not None:
            body["totalGB"] = _gb_to_bytes(volume_gb)
        if expiry_time_ms is not None:
            body["expiryTime"] = expiry_time_ms
        if tg_user_id is not None:
            body["tgId"] = tg_user_id
        if enable is not None:
            body["enable"] = enable
        return await self._request(
            "POST", f"/panel/api/clients/update/{email}", json_body=body
        )

    async def get_usage(self, email: str) -> ClientUsage:
        data = await self.get_client(email)
        return _parse_usage(data)

    async def get_sub_links(self, sub_id: str) -> list[str]:
        data = await self._request("GET", f"/panel/api/clients/subLinks/{sub_id}")
        obj = data.get("obj")
        if isinstance(obj, list):
            return [str(x) for x in obj]
        return []

    # ---------- high-level orchestration ----------
    async def provision(
        self,
        *,
        email: str,
        volume_gb: int,
        duration_days: int,
        inbound_ids: list[int],
        tg_user_id: int,
    ) -> ProvisionedClient:
        """Create a client and fetch its subscription links.

        Steps:
          1) POST /clients/add
          2) Try to read subId/uuid from the add response.
          3) If missing, GET /clients/get/{email} to fetch them.
          4) GET /clients/subLinks/{subId} for the actual config URIs.
        """
        add_resp = await self.add_client(
            email=email,
            volume_gb=volume_gb,
            duration_days=duration_days,
            inbound_ids=inbound_ids,
            tg_user_id=tg_user_id,
        )

        sub_id = _extract_sub_id(add_resp)
        client_uuid = _extract_uuid(add_resp)
        get_resp: dict[str, Any] | None = None

        if not sub_id or not client_uuid:
            try:
                get_resp = await self.get_client(email)
                sub_id = sub_id or _extract_sub_id(get_resp)
                client_uuid = client_uuid or _extract_uuid(get_resp)
            except XuiError as exc:
                log.warning("get_client fallback failed for %s: %s", email, exc)

        # Some panels generate the UUID server-side and don't echo it; that's fine.
        if not client_uuid:
            client_uuid = str(_uuid.UUID(int=0))  # placeholder so we don't crash

        sub_links: list[str] = []
        if sub_id:
            try:
                sub_links = await self.get_sub_links(sub_id)
            except XuiError as exc:
                log.warning("get_sub_links failed for %s: %s", sub_id, exc)

        return ProvisionedClient(
            email=email,
            sub_id=sub_id,
            client_uuid=client_uuid,
            sub_links=sub_links,
            raw_get_response=get_resp,
        )
