from __future__ import annotations

import logging
import httpx
from app.config import Settings

log = logging.getLogger(__name__)


async def send_pending_order_sms(
    settings: Settings,
    order_id: int,
    price: int,
    location_name: str,
) -> None:
    """Send an SMS notification to admins when an order is pending review.

    Supports both bulk send and template-based send (SMS.ir).
    """
    if not settings.sms_api_key or not settings.sms_admin_mobiles:
        return

    # Check if we should use Template Send (verify) or Bulk Send
    if settings.sms_template_id:
        url = "https://api.sms.ir/v1/send/verify"
        headers = {
            "X-API-KEY": settings.sms_api_key,
            "Content-Type": "application/json",
            "Accept": "text/plain",
        }

        # Send to each mobile individually for /verify template endpoint
        async with httpx.AsyncClient(timeout=10.0) as client:
            for mobile in settings.sms_admin_mobiles:
                payload = {
                    "mobile": mobile,
                    "templateId": settings.sms_template_id,
                    "parameters": [
                        {"name": "ORDERID", "value": str(order_id)},
                        {"name": "PRICE", "value": f"{price:,}"},
                        {"name": "LOCATION", "value": location_name[:20]},
                    ]
                }
                try:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        log.info("Successfully sent pending order template SMS to %s", mobile)
                    else:
                        log.warning(
                            "Failed to send template SMS to %s: HTTP %d, Response: %s",
                            mobile,
                            resp.status_code,
                            resp.text[:200],
                        )
                except Exception as e:
                    log.exception("Error sending template SMS to %s: %s", mobile, e)
    else:
        # Standard bulk send
        url = "https://api.sms.ir/v1/send/bulk"
        headers = {
            "X-API-KEY": settings.sms_api_key,
            "Content-Type": "application/json",
            "Accept": "text/plain",
        }

        message_text = (
            f"سفارش جدید در ربات نت‌فلای منتظر تایید است.\n"
            f"شناسه سفارش: #{order_id}\n"
            f"مبلغ: {price:,} تومان\n"
            f"لوکیشن: {location_name}"
        )

        payload = {
            "lineNumber": settings.sms_line_number or "",
            "messageText": message_text,
            "mobiles": settings.sms_admin_mobiles,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    log.info("Successfully sent pending order bulk SMS to admins")
                else:
                    log.warning(
                        "Failed to send bulk SMS: HTTP %d, Response: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
        except Exception as e:
            log.exception("Error sending bulk SMS to admins: %s", e)
