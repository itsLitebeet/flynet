"""All Persian (Farsi) UI strings and constants in one place."""

from __future__ import annotations


# ---------- order presets ----------
VOLUME_PRESETS_GB: list[int] = [1, 2, 5, 10]      # buttons; "Custom" is a separate option
DURATION_PRESETS_DAYS: list[int] = [3, 7, 30]

CUSTOM_VOLUME_MIN_GB = 1
CUSTOM_VOLUME_MAX_GB = 500


# ---------- helpers ----------
def format_price(toman: int) -> str:
    return f"{toman:,} تومان"


def format_card_number(card: str) -> str:
    """Digits only — no dashes or spaces (easier to copy in banking apps)."""
    return "".join(ch for ch in card if ch.isdigit()) or card


def format_payment_amount(toman: int) -> str:
    """Payment line: only the numeric amounts are monospace (easy to copy)."""
    rial = toman * 10
    return f"<code>{toman}</code> تومان یا <code>{rial}</code> ریال"


def calc_price(volume_gb: int, duration_days: int,
               base: int, per_gb: int, per_day: int) -> int:
    return int(base + per_gb * volume_gb + per_day * duration_days)


def format_pricing_formula(base: int, per_gb: int, per_day: int) -> str:
    return f"base {base:,} + {per_gb:,}/GB + {per_day:,}/day"


def format_bytes(n: int) -> str:
    """Render a byte count using GB/MB units (1024-based)."""
    if n <= 0:
        return "0 MB"
    if n >= 1024 ** 3:
        return f"{n / (1024 ** 3):.2f} GB"
    return f"{n / (1024 ** 2):.1f} MB"


# ---------- buttons ----------
BTN_BUY          = "🛒 خرید سرویس"
BTN_MY_SERVICES  = "📊 سرویس‌های من"
BTN_MY_ACCOUNT   = "👤 حساب کاربری"
BTN_SUPPORT      = "💬 پشتیبانی"
BTN_HELP         = "❓ راهنما"
BTN_ABOUT        = "ℹ️ درباره ما"
BTN_BACK       = "🔙 بازگشت"
BTN_CANCEL     = "❌ انصراف"
BTN_CONFIRM    = "✅ تأیید و ادامه"
BTN_CUSTOM     = "✏️ مقدار دلخواه"
BTN_ACCEPT     = "✅ تأیید پرداخت"
BTN_DECLINE    = "❌ رد پرداخت"
BTN_VIEW_USER  = "👤 پروفایل کاربر"

# My services
BTN_VIEW_CONFIGS  = "📋 مشاهده لینک‌ها"
BTN_REFRESH_USAGE = "🔄 بروزرسانی مصرف"
BTN_TOGGLE_OFF   = "⏸ توقف موقت"
BTN_TOGGLE_ON    = "▶️ فعال‌سازی"
BTN_RENAME       = "✏️ تغییر نام"
BTN_REGEN        = "🔁 تولید مجدد"
BTN_REGEN_CONFIRM = "✅ بله، تولید مجدد کن"


# ---------- my services ----------
MY_SERVICES_EMPTY = (
    "📊 <b>سرویس‌های من</b>\n\n"
    "هنوز هیچ سفارشی ثبت نکرده‌اید.\n"
    "برای خرید اولین سرویس، از منوی اصلی روی «خرید سرویس» بزنید."
)

MY_SERVICES_HEADER = (
    "📊 <b>سرویس‌های من</b>\n\n"
    "روی هر سرویس بزنید تا جزئیات و اقدامات آن را ببینید:"
)

# Status badges used in both list and detail
STATUS_BADGE = {
    "awaiting_payment": "💳 در انتظار پرداخت",
    "awaiting_review":  "⏳ در انتظار بررسی",
    "approved":         "✅ تأییدشده",
    "declined":         "❌ ردشده",
    "provisioned":      "🟢 فعال",
    "failed":           "⚠️ خطا",
}

SERVICE_LIST_ITEM = (
    "{status_emoji} #{id} — {location} — {volume}GB / {days}d{nickname_part}"
)

SERVICE_DETAIL = (
    "📦 <b>سرویس #{order_id}</b>{nickname_part}\n\n"
    "📍 لوکیشن: <b>{location}</b>\n"
    "💾 حجم سفارش: <b>{volume} گیگابایت</b>\n"
    "📅 مدت سفارش: <b>{days} روز</b>\n"
    "💰 مبلغ: <b>{price}</b>\n"
    "🏷 وضعیت: <b>{status}</b>\n"
    "{panel_id_line}"
    "{usage_block}"
    "🗓 تاریخ ثبت: {created_at}"
)

SERVICE_DETAIL_USAGE_BLOCK = (
    "📊 <b>مصرف و اعتبار (زنده)</b>\n"
    "🔌 اتصال: <b>{enabled}</b>\n"
    "💾 مصرف: <b>{used}</b> از <b>{total}</b>\n"
    "📈 باقیمانده: <b>{remaining}</b>\n"
    "⏳ اعتبار تا: <b>{expiry}</b> ({time_left})\n\n"
)

SERVICE_DETAIL_USAGE_ERROR = (
    "📊 <b>مصرف و اعتبار</b>\n"
    "⚠️ دریافت از پنل ناموفق: <code>{error}</code>\n\n"
)

SERVICE_NOT_PROVISIONED_ACTIONS = (
    "\n\nℹ️ این سرویس هنوز فعال نشده، بنابراین گزینه‌های مدیریت در دسترس نیستند."
)

VIEW_CONFIGS_TITLE = (
    "🔗 <b>اطلاعات اتصال — سرویس #{order_id}</b>\n\n{configs_block}"
)

VIEW_USAGE_TITLE = (
    "📊 <b>وضعیت سرویس #{order_id}</b>\n\n"
    "🟢 وضعیت: <b>{enabled}</b>\n"
    "💾 مصرف: <b>{used}</b> از <b>{total}</b>\n"
    "📈 باقیمانده: <b>{remaining}</b>\n"
    "⏳ اعتبار تا: <b>{expiry}</b> ({time_left})"
)
VIEW_USAGE_UNLIMITED_TRAFFIC = "نامحدود"
VIEW_USAGE_NEVER_EXPIRES     = "بدون انقضا"
VIEW_USAGE_EXPIRED           = "منقضی شده"
VIEW_USAGE_ENABLED           = "فعال"
VIEW_USAGE_DISABLED          = "غیرفعال"
VIEW_USAGE_FETCH_FAILED      = (
    "⚠️ دریافت اطلاعات مصرف از پنل ممکن نشد:\n<code>{error}</code>\n\n"
    "ممکن است سرویس از پنل حذف شده باشد یا پنل در دسترس نباشد."
)

TOGGLE_OK_DISABLED = "⏸ سرویس #{order_id} موقتاً متوقف شد."
TOGGLE_OK_ENABLED  = "▶️ سرویس #{order_id} دوباره فعال شد."
TOGGLE_FAILED      = "⚠️ تغییر وضعیت ممکن نشد:\n<code>{error}</code>"

RENAME_PROMPT = (
    "✏️ <b>تغییر نام سرویس #{order_id}</b>\n\n"
    "یک نام کوتاه بفرستید (فقط حروف انگلیسی، عدد، <code>-</code> و <code>_</code>).\n"
    "مثال: <code>phone</code> → شناسه پنل: <code>nf{order_id}-phone</code>\n\n"
    "حداکثر ۳۰ کاراکتر. حذف نام محلی: <code>-</code>\n"
    "انصراف: /cancel"
)
RENAME_TOO_LONG = "❗ نام نباید بیشتر از ۳۰ کاراکتر باشد."
RENAME_INVALID_LABEL = (
    "❗ نام نامعتبر است.\n"
    "فقط حروف انگلیسی کوچک، عدد، خط‌تیره و زیرخط مجاز است."
)
RENAME_PANEL_FAILED = "⚠️ تغییر نام روی پنل ناموفق بود:\n<code>{error}</code>"
RENAME_OK = "✅ نام نمایشی سرویس به‌روز شد."
RENAME_OK_PANEL = (
    "✅ نام سرویس به‌روز شد.\n"
    "🏷 برچسب: <b>{label}</b>\n"
    "🆔 شناسه پنل: <code>{panel_id}</code>"
)
RENAME_CLEARED  = "✅ نام سرویس حذف شد."

REGEN_CONFIRM = (
    "⚠️ <b>تولید مجدد لینک‌ها</b>\n\n"
    "این کار:\n"
    "• سرویس فعلی روی پنل را <b>غیرفعال</b> می‌کند (لینک‌های فعلی دیگر کار نخواهند کرد)\n"
    "• یک سرویس جدید با ترافیک باقیمانده و همان تاریخ انقضا می‌سازد\n"
    "• شمارنده مصرف <b>صفر</b> می‌شود اما مهلت زمانی تغییر نمی‌کند\n\n"
    "این کار <b>قابل بازگشت نیست</b>. آیا مطمئن هستید؟"
)
REGEN_IN_PROGRESS = "⏳ در حال ساخت مجدد سرویس..."
REGEN_OK          = "🎉 سرویس با موفقیت بازسازی شد.\n\n{configs_block}"
REGEN_FAILED      = "⚠️ بازسازی ناموفق بود:\n<code>{error}</code>\n\nسرویس قبلی شما همچنان فعال است."
REGEN_NOT_SUPPORTED = (
    "ℹ️ این سرویس هنوز روی پنل ساخته نشده یا اطلاعات کافی ندارد."
)


# ---------- top-level messages ----------
WELCOME = (
    "🛡️ <b>به ربات NetFly خوش آمدید</b>\n\n"
    "اینجا می‌توانید سرویس‌های پرسرعت و امن وی‌پی‌ان ما را خریداری "
    "و مدیریت کنید.\n\n"
    "از <b>دکمه‌های پایین صفحه</b> یکی از گزینه‌ها را انتخاب کنید 👇"
)

HELP = (
    "📖 <b>راهنمای استفاده از NetFly</b>\n\n"
    "<b>برای خرید:</b>\n"
    "۱) لوکیشن سرور را انتخاب کنید\n"
    "۲) حجم ترافیک را مشخص کنید (یا «مقدار دلخواه»)\n"
    "۳) مدت اعتبار را انتخاب کنید\n"
    "۴) پس از تأیید قیمت، مبلغ را به شماره کارت اعلام‌شده واریز کنید\n"
    "۵) اسکرین‌شات رسید را در ربات ارسال کنید\n"
    "۶) پس از تأیید توسط ادمین، لینک اتصال برای شما ارسال می‌شود\n\n"
    "دستورها:\n"
    "/start — منوی اصلی\n"
    "/help — همین راهنما\n"
    "/cancel — لغو عملیات در حال انجام"
)

ABOUT = (
    "ℹ️ <b>درباره NetFly</b>\n\n"
    "NetFly سرویس وی‌پی‌ان امن، سریع و پایدار با پشتیبانی ۲۴ ساعته است.\n\n"
    "✅ سرورهای پرسرعت در چند لوکیشن\n"
    "✅ بدون لاگ، با تضمین حریم خصوصی\n"
    "✅ پشتیبانی از تمامی پلتفرم‌ها"
)

ACCOUNT_INFO = (
    "👤 <b>حساب کاربری شما</b>\n\n"
    "شناسه عددی: <code>{user_id}</code>\n"
    "نام کاربری: {username}\n"
    "نام: {full_name}\n"
    "عضو از: {created_at}\n"
)


# ---------- order flow ----------
ORDER_PICK_LOCATION = "📍 <b>لوکیشن سرور را انتخاب کنید:</b>"

NO_LOCATIONS_USER = (
    "⛔ در حال حاضر هیچ لوکیشنی فعال نیست. لطفاً بعداً دوباره تلاش کنید "
    "یا با پشتیبانی در تماس باشید."
)

ORDER_PICK_VOLUME = (
    "📦 لوکیشن انتخاب‌شده: <b>{location}</b>\n\n"
    "💾 <b>حجم ترافیک را انتخاب کنید:</b>"
)

ORDER_ASK_CUSTOM_VOLUME = (
    "✏️ <b>حجم دلخواه</b>\n\n"
    "لطفاً عدد را به گیگابایت ارسال کنید "
    "(بین {min_gb} تا {max_gb} گیگابایت).\n\n"
    "مثال: <code>25</code>\n"
    "برای انصراف: /cancel"
)

ORDER_CUSTOM_VOLUME_INVALID = (
    "❗ لطفاً یک عدد صحیح بین {min_gb} تا {max_gb} وارد کنید."
)

ORDER_PICK_DURATION = (
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n\n"
    "📅 <b>مدت اعتبار را انتخاب کنید:</b>"
)

ORDER_REVIEW = (
    "🧾 <b>خلاصه سفارش</b>\n\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n"
    "📅 مدت اعتبار: <b>{days} روز</b>\n"
    "💰 مبلغ قابل پرداخت: <b>{price}</b>\n\n"
    "در صورت تأیید، دستور پرداخت برای شما ارسال می‌شود."
)

ORDER_PAYMENT_INSTRUCTIONS = (
    "💳 <b>دستور پرداخت — سفارش #{order_id}</b>\n\n"
    "لطفاً مبلغ {amount} را به کارت زیر واریز کنید:\n\n"
    "<code>{card_number}</code>\n"
    "به نام: <b>{card_holder}</b>\n\n"
    "✅ پس از واریز، <b>اسکرین‌شات رسید</b> را در همین چت ارسال کنید "
    "(به‌صورت عکس، نه فایل).\n\n"
    "⏳ پس از بررسی توسط ادمین، لینک اتصال برای شما ارسال خواهد شد.\n"
    "برای انصراف: /cancel"
)

ORDER_RECEIPT_NEED_PHOTO = (
    "❗ لطفاً <b>اسکرین‌شات رسید</b> را به‌صورت عکس ارسال کنید."
)

ORDER_RECEIPT_RECEIVED = (
    "✅ رسید شما دریافت شد و در حال بررسی توسط ادمین است.\n"
    "به‌محض تأیید، لینک اتصال برای شما ارسال می‌شود."
)

ORDER_DECLINED_NOTIFY = (
    "❌ <b>سفارش #{order_id} رد شد</b>\n\n"
    "{reason}\n\n"
    "در صورت سؤال، با پشتیبانی در تماس باشید."
)
ORDER_DECLINED_DEFAULT_REASON = "متأسفانه رسید پرداخت شما توسط ادمین تأیید نشد."

ORDER_PROVISIONED_NOTIFY = (
    "🎉 <b>سفارش #{order_id} با موفقیت فعال شد!</b>\n\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n"
    "📅 مدت اعتبار: <b>{days} روز</b>\n\n"
    "{configs_block}\n\n"
    "💡 پیشنهاد می‌شود از <b>لینک اشتراک</b> استفاده کنید — کافی است یک‌بار در "
    "اپلیکیشن وی‌پی‌ان وارد شود، کانفیگ‌ها به‌صورت خودکار به‌روزرسانی می‌شوند.\n"
    "اپلیکیشن‌های پیشنهادی: V2RayNG، NekoBox، v2rayN، Streisand."
)


def format_configs_block(sub_url: str | None, sub_links: list[str]) -> str:
    """Build the connection-info block used in both the order completion message
    and the My Services detail view.
    """
    parts: list[str] = []
    if sub_url:
        parts.append("🔔 <b>لینک اشتراک:</b>")
        parts.append(f"<code>{sub_url}</code>")
        parts.append("")
    if sub_links:
        parts.append("📋 <b>لینک‌های جداگانه:</b>")
        for link in sub_links:
            parts.append(f"<code>{link}</code>")
    if not parts:
        parts.append("—")
    return "\n".join(parts)

ORDER_PROVISION_FAILED_USER = (
    "⚠️ پرداخت شما تأیید شد، اما در ساخت کانفیگ روی پنل مشکلی پیش آمد. "
    "تیم پشتیبانی به‌زودی موضوع را پیگیری خواهد کرد."
)


# ---------- support ----------
SUPPORT_PROMPT = (
    "💬 <b>پشتیبانی NetFly</b>\n\n"
    "لطفاً پیام، سؤال یا توضیح مشکل خود را در یک پیام ارسال کنید.\n"
    "پیام شما به تیم پشتیبانی ارسال خواهد شد.\n\n"
    "برای انصراف، دستور /cancel را بفرستید."
)
SUPPORT_SENT     = "✅ پیام شما با موفقیت برای پشتیبانی ارسال شد. به‌زودی پاسخ خواهیم داد."
SUPPORT_TOO_LONG = "❗ پیام شما خیلی طولانی است. لطفاً آن را کوتاه‌تر کنید."
SUPPORT_EMPTY    = "❗ لطفاً یک پیام متنی ارسال کنید."

CANCELLED   = "❌ عملیات لغو شد."
NOT_ADMIN   = "⛔ این دستور فقط برای ادمین‌ها در دسترس است."
USER_BANNED = "⛔ دسترسی شما به ربات مسدود شده است."


# ---------- admin panel (buttons) ----------
ADMIN_BTN_DASHBOARD = "📊 داشبورد"
ADMIN_BTN_PENDING   = "🔍 بررسی پرداخت‌ها"
ADMIN_BTN_SETTINGS  = "⚙️ تنظیمات"
ADMIN_BTN_LOCATIONS = "📍 لوکیشن‌ها"
ADMIN_BTN_TOOLS     = "🛠 ابزارها"
ADMIN_BTN_USERS     = "👥 کاربران"
ADMIN_BTN_PANEL     = "🏠 پنل ادمین"
ADMIN_BTN_REFRESH   = "🔄 بروزرسانی"

ADMIN_PANEL_HOME = (
    "🛠 <b>پنل مدیریت NetFly</b>\n\n"
    "از <b>دکمه‌های پایین صفحه</b> یا منوی زیر استفاده کنید.\n"
    "دستورات متنی همچنان کار می‌کنند — <code>/admin</code> برای راهنمای کامل."
)

ADMIN_DASHBOARD_HEADER = (
    "📊 <b>داشبورد</b>\n\n"
    "{stats}\n\n"
    "👇 برای بررسی رسیدها، دکمه «بررسی پرداخت‌ها» را بزنید."
)

ADMIN_SETTINGS_VIEW = (
    "⚙️ <b>تنظیمات فعلی</b>\n\n"
    "💳 شماره کارت: <code>{card_number}</code>\n"
    "👤 صاحب کارت: <b>{card_holder}</b>\n\n"
    "💰 قیمت پیش‌فرض:\n"
    "base = <b>{base}</b> | per_gb = <b>{per_gb}</b> | per_day = <b>{per_day}</b>\n\n"
    "<b>ویرایش با دستور:</b>\n"
    "<code>/setcard 6037... | نام</code>\n"
    "<code>/setprice 20000 8000 1500</code>"
)

ADMIN_SETTINGS_MENU = (
    "⚙️ <b>تنظیمات</b>\n\n"
    "برای تغییر، دستورات زیر را در چت بفرستید (مثال‌ها در راهنما)."
)

ADMIN_TOOLS_MENU = (
    "🛠 <b>ابزارها</b>\n\n"
    "از دکمه‌های زیر استفاده کنید یا دستور متنی بفرستید."
)

ADMIN_LOCATIONS_MENU = (
    "📍 <b>لوکیشن‌ها</b> ({count} مورد)\n\n"
    "روی هر لوکیشن بزنید برای جزئیات. 🔁 = فعال/غیرفعال."
)

ADMIN_LOC_EMPTY = "هیچ لوکیشنی ثبت نشده است.\n\n<code>/addlocation ...</code>"

ADMIN_LOC_DETAIL = (
    "📍 <b>لوکیشن #{id}</b> {state_emoji} <b>{name}</b>\n\n"
    "🔗 <code>{base_url}</code>\n"
    "📡 inbounds: <code>{inbounds}</code>\n"
    "🔔 sub: <code>{sub}</code>\n"
    "💰 {pricing}\n\n"
    "<b>دستورات:</b>\n"
    "<code>/setlocationprice {id} base per_gb per_day</code>\n"
    "<code>/setsuburl {id} https://host:2096/sub/{{subId}}</code>\n"
    "<code>/purgelocation {id}</code>"
)

ADMIN_PENDING_HEADER = (
    "🔍 <b>سفارش‌های در انتظار بررسی</b> — <b>{count}</b> مورد\n\n"
    "روی هر سفارش بزنید تا رسید و دکمه‌های تأیید/رد نمایش داده شود."
)

ADMIN_PENDING_EMPTY = "✅ هیچ سفارشی در انتظار بررسی نیست."

ADMIN_PENDING_BTN = "🔍 #{id} · {price} · کاربر {user_id}"

ADMIN_USERS_HEADER = "👥 <b>۲۰ کاربر اخیر</b>\n"
ADMIN_USER_ITEM = "• <code>{user_id}</code> — {name} ({username}) — {created_at}"

ADMIN_TOOL_SYNC_DONE = "✅ همگام‌سازی پنل انجام شد (همان نتیجه <code>/syncpanel</code>)."

ADMIN_CMD_HELP_BTN = "📖 راهنمای دستورات"


# ---------- admin commands (reference) ----------
ADMIN_HELP = (
    "🛠 <b>دستورهای ادمین</b>\n\n"
    "💡 <b>پنل دکمه‌ای:</b> <code>/admin</code> — منوی پایین + دکمه‌های شیشه‌ای\n\n"
    "<b>عمومی:</b>\n"
    "/stats — آمار کلی\n"
    "/users — ۲۰ کاربر اخیر\n"
    "/pending — سفارش‌های در انتظار بررسی\n"
    "/broadcast &lt;متن&gt; — ارسال همگانی\n\n"
    "<b>تنظیمات:</b>\n"
    "/setcard &lt;شماره کارت&gt; | &lt;نام صاحب کارت&gt;\n"
    "/setprice &lt;base&gt; &lt;per_gb&gt; &lt;per_day&gt; — قیمت پیش‌فرض (لوکیشن‌های جدید)\n"
    "/setlocationprice &lt;id&gt; &lt;base&gt; &lt;per_gb&gt; &lt;per_day&gt; — قیمت یک لوکیشن\n"
    "/setlocationprice &lt;id&gt; - — بازگشت لوکیشن به قیمت پیش‌فرض\n"
    "/showsettings — نمایش تنظیمات فعلی\n\n"
    "<b>لوکیشن‌ها:</b>\n"
    "/locations — لیست لوکیشن‌ها\n"
    "/addlocation &lt;name&gt; | &lt;base_url&gt; | &lt;api_token&gt; | &lt;inbound_id1,id2&gt;\n"
    "/dellocation &lt;id&gt; — حذف اگر سفارشی ندارد، در غیر این صورت غیرفعال\n"
    "/purgelocation &lt;id&gt; — ⚠️ حذف کامل لوکیشن و همه سفارش‌های آن\n"
    "/togglelocation &lt;id&gt;\n"
    "/setsuburl &lt;id&gt; &lt;template&gt; — تنظیم لینک اشتراک\n\n"
    "<b>همگام‌سازی پنل:</b>\n"
    "/clearorder &lt;order_id&gt; — حذف یک سفارش از دیتابیس\n"
    "/syncpanel — حذف سفارش‌های یتیم (پنل) + همه رد‌شده‌ها\n"
    "/syncpanel &lt;location_id&gt; — فقط یک لوکیشن\n"
    "/cleardeclined — حذف سفارش‌های رد‌شده و پرداخت‌نشده"
)

ADMIN_STATS = (
    "📊 <b>آمار NetFly</b>\n\n"
    "👥 کاربران: <b>{users}</b>\n"
    "🛒 کل سفارش‌ها: <b>{orders}</b>\n"
    "⏳ در انتظار پرداخت: <b>{awaiting_payment}</b>\n"
    "🔍 در انتظار بررسی: <b>{awaiting_review}</b>\n"
    "🎉 فعال‌شده: <b>{provisioned}</b>\n"
    "❌ رد‌شده: <b>{declined}</b>\n"
    "⚠️ خطا در فعال‌سازی: <b>{failed}</b>\n"
    "💬 تیکت‌های پشتیبانی: <b>{tickets}</b>"
)

CLEAR_ORDER_USAGE    = "❗ استفاده: <code>/clearorder &lt;order_id&gt;</code>"
CLEAR_ORDER_OK       = "✅ سفارش <code>#{id}</code> از دیتابیس حذف شد."
CLEAR_ORDER_NOTFOUND = "❗ سفارشی با این شناسه پیدا نشد."

CLEAR_DECLINED_OK = (
    "✅ از دیتابیس حذف شد:\n"
    "❌ رد‌شده: <b>{declined}</b>\n"
    "💳 پرداخت‌نشده: <b>{unpaid}</b>\n"
    "جمع: <b>{total}</b>"
)
CLEAR_DECLINED_NONE = "ℹ️ سفارش رد‌شده یا پرداخت‌نشده‌ای در دیتابیس نیست."

SYNC_PANEL_USAGE    = (
    "❗ استفاده:\n"
    "<code>/syncpanel</code> — همه لوکیشن‌ها\n"
    "<code>/syncpanel 2</code> — فقط لوکیشن ۲"
)
SYNC_PANEL_START    = "⏳ در حال همگام‌سازی با پنل..."
SYNC_PANEL_NONE = (
    "✅ همه سفارش‌های فعال در پنل موجودند.\n"
    "سفارش رد‌شده حذف‌شده: <b>{declined}</b>"
)
SYNC_PANEL_DONE = (
    "✅ همگام‌سازی پایان یافت.\n\n"
    "🗑 حذف از دیتابیس (یتیم پنل): <b>{orphan_count}</b>\n"
    "<code>{orphan_ids}</code>\n\n"
    "❌ حذف سفارش‌های رد‌شده: <b>{declined}</b>"
)
SYNC_PANEL_LOC_ERR  = "⚠️ خطا در لوکیشن <code>#{id}</code> ({name}):\n<code>{error}</code>"

BROADCAST_EMPTY   = "❗ استفاده: <code>/broadcast متن پیام</code>"
BROADCAST_STARTED = "📣 شروع ارسال همگانی به {count} کاربر..."
BROADCAST_DONE    = "✅ ارسال همگانی پایان یافت.\nموفق: <b>{ok}</b> | ناموفق: <b>{fail}</b>"

NEW_TICKET_NOTIFY = (
    "🆕 <b>تیکت پشتیبانی جدید #{ticket_id}</b>\n"
    "از طرف: <a href='tg://user?id={user_id}'>{full_name}</a> "
    "(<code>{user_id}</code>)\n\n"
    "{message}"
)

NEW_RECEIPT_NOTIFY = (
    "💳 <b>رسید پرداخت جدید — سفارش #{order_id}</b>\n\n"
    "👤 کاربر: <a href='tg://user?id={user_id}'>{full_name}</a> (<code>{user_id}</code>)\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n"
    "📅 مدت: <b>{days} روز</b>\n"
    "💰 مبلغ: <b>{price}</b>"
)

# Settings / locations admin replies
SET_CARD_OK        = "✅ شماره کارت به‌روزرسانی شد:\n<code>{number}</code>\nبه نام: <b>{holder}</b>"
SET_CARD_USAGE     = "❗ استفاده:\n<code>/setcard 6037-9912-3456-7890 | NetFly</code>"
SET_PRICE_OK       = ("✅ فرمول قیمت به‌روزرسانی شد:\n"
                     "base = <b>{base}</b> | per_gb = <b>{per_gb}</b> | per_day = <b>{per_day}</b>")
SET_PRICE_USAGE    = "❗ استفاده:\n<code>/setprice 20000 8000 1500</code>"
SHOW_SETTINGS      = ADMIN_SETTINGS_VIEW  # alias for /showsettings command

SET_LOC_PRICE_USAGE = (
    "❗ استفاده:\n"
    "<code>/setlocationprice 2 25000 10000 2000</code>\n\n"
    "برای استفاده از قیمت پیش‌فرض سراسری:\n"
    "<code>/setlocationprice 2 -</code>"
)
SET_LOC_PRICE_OK = (
    "✅ قیمت لوکیشن <code>#{id}</code> «{name}»:\n"
    "base = <b>{base}</b> | per_gb = <b>{per_gb}</b> | per_day = <b>{per_day}</b>"
)
SET_LOC_PRICE_DEFAULT_OK = (
    "✅ لوکیشن <code>#{id}</code> «{name}» از قیمت پیش‌فرض سراسری استفاده می‌کند."
)
ADD_LOC_USAGE   = (
    "❗ استفاده:\n"
    "<code>/addlocation Germany 🇩🇪 | https://panel.example.com | "
    "MY_API_TOKEN | 3,5</code>\n\n"
    "می‌توانید فیلد پنجم اختیاری را برای لینک اشتراک اضافه کنید:\n"
    "<code>... | 3,5 | https://panel.example.com:2096/sub/{subId}</code>"
)
ADD_LOC_OK      = (
    "✅ لوکیشن «{name}» با شناسه <code>{id}</code> اضافه شد.\n"
    "💰 قیمت: {pricing}"
)

SET_SUBURL_USAGE = (
    "❗ استفاده:\n"
    "<code>/setsuburl &lt;id&gt; https://host:2096/sub/{subId}</code>\n\n"
    "برای حذف الگو: <code>/setsuburl &lt;id&gt; -</code>\n"
    "متن باید شامل <code>{subId}</code> باشد (محل قرارگیری شناسه اشتراک)."
)
SET_SUBURL_OK       = "✅ الگوی لینک اشتراک برای لوکیشن <code>#{id}</code> تنظیم شد:\n<code>{template}</code>"
SET_SUBURL_CLEARED  = "✅ الگوی لینک اشتراک برای لوکیشن <code>#{id}</code> حذف شد."
SET_SUBURL_BAD      = "❗ الگو باید شامل <code>{subId}</code> باشد."
DEL_LOC_USAGE     = "❗ استفاده: <code>/dellocation &lt;id&gt;</code>"
DEL_LOC_OK        = "✅ لوکیشن <code>{id}</code> حذف شد."
DEL_LOC_DISABLED  = (
    "ℹ️ لوکیشن <code>{id}</code> سفارش‌های ثبت‌شده دارد و قابل حذف کامل نیست؛ "
    "به‌جای حذف، <b>غیرفعال</b> شد و دیگر در لیست کاربر نمایش داده نمی‌شود.\n\n"
    "اگر می‌خواهید کاملاً پاک شود، ابتدا سفارش‌های مرتبط را از دیتابیس حذف کنید."
)
DEL_LOC_NOTFOUND  = "❗ لوکیشنی با این شناسه پیدا نشد."

PURGE_USAGE     = "❗ استفاده: <code>/purgelocation &lt;id&gt;</code>"
PURGE_CONFIRM   = (
    "⚠️ <b>هشدار — عملیات غیرقابل بازگشت</b>\n\n"
    "این کار لوکیشن <code>#{id}</code> «<b>{name}</b>» و "
    "<b>{count}</b> سفارش مرتبط با آن را برای همیشه از دیتابیس حذف می‌کند.\n\n"
    "آیا مطمئن هستید؟"
)
PURGE_DONE      = "✅ لوکیشن <code>#{id}</code> و <b>{count}</b> سفارش مرتبط حذف شدند."
PURGE_CANCELLED = "❌ پاک‌سازی لغو شد."
TOGGLE_LOC_USAGE = "❗ استفاده: <code>/togglelocation &lt;id&gt;</code>"
TOGGLE_LOC_OK    = "✅ لوکیشن <code>{id}</code> اکنون <b>{state}</b> است."
LOC_LIST_EMPTY  = "هیچ لوکیشنی ثبت نشده است. با <code>/addlocation</code> یکی اضافه کنید."
LOC_LIST_HEADER = "📍 <b>لوکیشن‌های ثبت‌شده</b>\n"
LOC_LIST_ITEM   = (
    "• <code>#{id}</code> {state_emoji} <b>{name}</b>\n"
    "    base: <code>{base_url}</code>\n"
    "    inbounds: <code>{inbounds}</code>\n"
    "    sub: <code>{sub_template}</code>\n"
    "    💰 {pricing}"
)

PENDING_EMPTY  = "هیچ سفارشی در انتظار بررسی نیست."
PENDING_HEADER = "🔍 <b>سفارش‌های در انتظار بررسی</b>\n"
PENDING_ITEM   = (
    "• سفارش <code>#{id}</code> — کاربر <code>{user_id}</code> — "
    "{volume}GB / {days}d — <b>{price}</b> ({created_at})"
)

REVIEW_ALREADY = (
    "⚠️ این سفارش قبلاً توسط ادمین دیگر بررسی شده است.\n"
    "وضعیت فعلی: <b>{status}</b>"
)
REVIEW_OTHER_ADMIN_DONE = (
    "ℹ️ سفارش <code>#{order_id}</code> دیگر در انتظار بررسی نیست.\n"
    "نتیجه: <b>{action}</b> (ادمین <code>{admin_id}</code>)"
)
REVIEW_DECLINE_PROMPT = (
    "❌ دلیل رد را در یک پیام ارسال کنید (یا /cancel برای انصراف).\n"
    "این متن برای کاربر ارسال می‌شود."
)
REVIEW_DECLINE_SENT  = "✅ سفارش رد شد و کاربر مطلع شد."
REVIEW_ACCEPTED      = "✅ سفارش تأیید شد. در حال ساخت کانفیگ روی پنل..."
REVIEW_PROVISION_OK  = "🎉 سفارش با موفقیت فعال و برای کاربر ارسال شد."
REVIEW_PROVISION_ERR = "⚠️ خطا در فعال‌سازی روی پنل:\n<code>{error}</code>"
