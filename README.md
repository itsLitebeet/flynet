# NetFly — Telegram VPN Bot

A Telegram bot that sells VPN access by talking to a 3x-ui-style panel.
UI is in Persian (فارسی). Runs with long polling — no public server required.

## How a purchase works

1. User opens the bot and presses **خرید سرویس**.
2. **Pick a location** (each location = one 3x-ui panel + a list of inboundIds).
3. **Pick a volume** (1 / 2 / 5 / 10 GB or a custom value, e.g. 25).
4. **Pick a duration** (3 / 7 / 30 days).
5. Bot calculates the price using the formula
   `price = base + per_gb·GB + per_day·days` (all admin-editable).
6. After user confirms, bot shows the **card number** (admin-editable).
7. User uploads a **payment screenshot**.
8. Bot DMs every admin the photo with **✅ تأیید پرداخت / ❌ رد پرداخت** buttons.
9. On **Accept**, the bot calls 3x-ui:
   - `POST /panel/api/clients/add` to create the client
   - `GET /panel/api/clients/get/{email}` (fallback if `subId` isn't in the add response)
   - `GET /panel/api/clients/subLinks/{subId}` to fetch the configs
   - DMs the user the subscription links.
10. On **Decline**, the bot asks the admin for a reason, then forwards it to the user.

## Quick start

1. Create a bot via [@BotFather](https://t.me/BotFather) and copy the token.
2. Find your Telegram user id with [@userinfobot](https://t.me/userinfobot).
3. Set up the project:

   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux:
   # source .venv/bin/activate

   pip install -r requirements.txt
   copy .env.example .env       # PowerShell. On macOS/Linux: cp ...
   ```

4. Edit `.env` and fill in `BOT_TOKEN` and `ADMIN_IDS`.
5. Run the bot:

   ```bash
   python bot.py
   ```

6. In Telegram, message your bot with `/admin` to see all admin commands, then:

   ```text
   /addlocation Germany 🇩🇪 | https://panel.example.com | YOUR_API_TOKEN | 3,5
   /setcard 6037-9912-3456-7890 | NetFly
   /setprice 20000 8000 1500
   ```

   That seeds one location + your card details + pricing formula. The user
   flow is now live.

## Admin commands

```
/admin            show this help
/stats            counts of users / orders / tickets
/users            20 most recent users
/pending          orders awaiting payment review
/broadcast TEXT   DM every (non-banned) user

/setcard NUMBER | HOLDER          update the card shown to buyers
/setprice BASE PER_GB PER_DAY     update the pricing formula
/showsettings                     dump current settings

/locations                                          list all locations
/addlocation NAME | BASE_URL | API_TOKEN | IDS      add one (IDs is comma-separated)
/dellocation ID                                     remove one
/togglelocation ID                                  enable/disable one
```

## Project layout

```
NetFly/
├── bot.py                 # entry point (polling)
├── requirements.txt
├── .env.example
└── app/
    ├── config.py          # loads BOT_TOKEN / ADMIN_IDS from .env
    ├── db.py              # SQLite: users, orders, locations, settings, tickets
    ├── xui.py             # async 3x-ui API client
    ├── texts.py           # all Persian copy + presets + price formula
    ├── keyboards.py       # inline keyboards & callback constants
    ├── middlewares.py     # auto-register users, block banned, inject db
    └── handlers/
        ├── start.py       # /start, /help, /cancel, main menu, account
        ├── order.py       # FSM order flow (location → volume → duration → receipt)
        ├── review.py      # admin Accept/Decline → calls XuiClient.provision()
        ├── support.py     # support ticket flow
        └── admin.py       # /stats, /users, /pending, /broadcast, settings, locations
```

## About the 3x-ui API

The client in `app/xui.py` targets the spec you provided:

- `POST /panel/api/clients/add?email=…` with body `{client:{…}, inboundIds:[…]}`
- `GET  /panel/api/clients/get/{email}`
- `GET  /panel/api/clients/subLinks/{subId}`

Auth is sent as `Authorization: Bearer <api_token>`. If your fork uses a
different header (e.g. `X-API-Token`), change `_auth_headers` in
`app/xui.py` (it's two lines).

The `add` response shape isn't documented, so `XuiClient.provision()` is
defensive: it first looks for `subId`/`uuid` in the add response, and if
they aren't there, falls back to `GET /panel/api/clients/get/{email}`
before fetching sub links. Adjust if your panel behaves differently.

### Client email convention

Each order creates a client with email `netfly_<telegram_user_id>_<order_id>`,
which guarantees uniqueness per order and lets you trace clients back to
both the buyer and the order row.
