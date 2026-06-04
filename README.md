# NetFly — Telegram VPN Bot

**NetFly** is a feature-rich, fully localized (Persian/فارسی) Telegram bot designed for selling and managing VPN access. It directly integrates with **X-UI / 3x-ui** panels to automatically provision, manage, and monitor VPN subscriptions via a sleek, modern inline-keyboard-driven interface.

## 🌟 Key Features

### For Users (Buyers)
* **Seamless Purchasing Flow**: Interactive step-by-step wizard to pick server locations, data volumes, and durations.
* **Pre-defined Packages**: Choose from curated VIP packages or build a custom plan.
* **My Services Dashboard**: Users can manage their active configs directly inside the bot:
  * View subscription links and configurations.
  * 🔄 Refresh live usage stats (data consumed, remaining).
  * ✏️ Rename configs.
  * 🔄 Regenerate configs (creates a new UUID).
  * 🟢/🔴 Toggle config status (enable/disable).
* **Support Ticket System**: Direct communication with admins.

### For Admins
* **Inline Dashboard (`/admin`)**: A complete admin panel built entirely with modern Telegram Inline Keyboards (utilizing Bot API 7.0+ color styles).
* **Manual Provisioning**: Easily create clients manually and attach them to a user by providing their Telegram ID or simply forwarding a message from them.
* **User Management**: Track users, view their purchase history, update their latest username/name from Telegram, and ban/unban them.
* **Location Management**: Add, edit, disable, or delete server locations directly from the bot.
* **Order Review System**: Receive payment screenshots in a dedicated channel or admin DM, and approve/decline with a single tap.
* **Broadcast Engine**: Send rich messages (text, photos, files) to all users.
* **Dynamic Pricing**: Configure base prices, price per GB, and price per day on the fly.
* **Discount System**: Apply global percentage-based discounts to all purchases.

## 🛠 Prerequisites

* Python 3.10+
* A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
* A running X-UI / 3x-ui panel with API access.

## 🚀 Quick Start (Manual Setup)

1. Clone the repository and navigate to the directory:
   ```bash
   git clone https://github.com/yourusername/NetFly.git
   cd NetFly
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. Setup your environment variables:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and fill in your `BOT_TOKEN` and `ADMIN_IDS` (comma-separated).

4. Run the bot:
   ```bash
   python bot.py
   ```

5. **First Setup**: Go to your bot in Telegram and send `/admin`. Navigate to **Locations** to add your first server, and **Settings** to set your card number and pricing formula.

## 🐳 Docker Deployment

NetFly includes a `docker-compose.yml` for easy deployment.

1. Configure your `.env` file with `BOT_TOKEN` and `ADMIN_IDS`.
2. Run the stack:
   ```bash
   docker-compose up -d --build
   ```

## 🏗 Architecture & Tech Stack

* **Framework**: `aiogram 3.x` (Asynchronous Telegram Bot API wrapper).
* **Database**: `sqlite3` for lightweight, zero-setup persistent storage (users, orders, locations, settings, tickets).
* **Panel Integration**: `aiohttp` for asynchronous communication with the X-UI panel API.
* **UI**: Extensive use of Aiogram's FSM (Finite State Machine) for wizards and Telegram's latest Inline Keyboard color styles (`success`, `danger`, `primary`).

### Project Layout
```text
NetFly/
├── bot.py                 # Bot entry point (starts long-polling)
├── docker-compose.yml     # Docker deployment config
├── Dockerfile             # Docker build instructions
└── app/
    ├── config.py          # Environment variable management
    ├── db.py              # SQLite database layer
    ├── xui.py             # X-UI API client wrapper
    ├── texts.py           # Localization and copy (Persian)
    ├── keyboards.py       # Inline keyboard builders and constants
    ├── middlewares.py     # Auth and DB injection middlewares
    └── handlers/          # Logic separated by domain (admin, orders, etc.)
```

## 🔌 X-UI API Integration

The bot integrates with the standard 3x-ui API. When an order is approved, the bot:
1. Calls `POST /panel/api/clients/add` to create the client.
2. Calls `GET /panel/api/clients/get/{email}` to confirm creation.
3. Calls `GET /panel/api/clients/subLinks/{subId}` to fetch the subscription URLs.

**Client Naming Convention**: The bot creates clients with the email format `nf<order_id>` (e.g. `nf101`) for clear tracking between your bot's database and the X-UI panel.

## 📝 License

This project is open-source and available under the MIT License.
