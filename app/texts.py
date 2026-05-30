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


def calc_price(volume_gb: int, duration_days: int,
               base: int, per_gb: int, per_day: int) -> int:
    return int(base + per_gb * volume_gb + per_day * duration_days)


# ---------- buttons ----------
BTN_BUY        = "🛒 خرید سرویس"
BTN_MY_ACCOUNT = "👤 حساب کاربری"
BTN_SUPPORT    = "💬 پشتیبانی"
BTN_HELP       = "❓ راهنما"
BTN_ABOUT      = "ℹ️ درباره ما"
BTN_BACK       = "🔙 بازگشت"
BTN_CANCEL     = "❌ انصراف"
BTN_CONFIRM    = "✅ تأیید و ادامه"
BTN_CUSTOM     = "✏️ مقدار دلخواه"
BTN_ACCEPT     = "✅ تأیید پرداخت"
BTN_DECLINE    = "❌ رد پرداخت"
BTN_VIEW_USER  = "👤 پروفایل کاربر"


# ---------- top-level messages ----------
WELCOME = (
    "🛡️ <b>به ربات NetFly خوش آمدید</b>\n\n"
    "اینجا می‌توانید سرویس‌های پرسرعت و امن وی‌پی‌ان ما را خریداری "
    "و مدیریت کنید.\n\n"
    "از منوی زیر یکی از گزینه‌ها را انتخاب کنید 👇"
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
    "لطفاً مبلغ <b>{price}</b> را به کارت زیر واریز کنید:\n\n"
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
    "🔗 <b>لینک‌های اتصال:</b>\n"
    "{links}\n\n"
    "💡 لینک‌ها را در اپلیکیشن وی‌پی‌ان خود وارد کنید (V2RayNG، NekoBox، v2rayN و ...)."
)

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


# ---------- admin ----------
ADMIN_HELP = (
    "🛠 <b>دستورهای ادمین</b>\n\n"
    "<b>عمومی:</b>\n"
    "/stats — آمار کلی\n"
    "/users — ۲۰ کاربر اخیر\n"
    "/pending — سفارش‌های در انتظار بررسی\n"
    "/broadcast &lt;متن&gt; — ارسال همگانی\n\n"
    "<b>تنظیمات:</b>\n"
    "/setcard &lt;شماره کارت&gt; | &lt;نام صاحب کارت&gt;\n"
    "/setprice &lt;base&gt; &lt;per_gb&gt; &lt;per_day&gt;\n"
    "/showsettings — نمایش تنظیمات فعلی\n\n"
    "<b>لوکیشن‌ها:</b>\n"
    "/locations — لیست لوکیشن‌ها\n"
    "/addlocation &lt;name&gt; | &lt;base_url&gt; | &lt;api_token&gt; | &lt;inbound_id1,id2&gt;\n"
    "/dellocation &lt;id&gt;\n"
    "/togglelocation &lt;id&gt;"
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
SHOW_SETTINGS      = (
    "⚙️ <b>تنظیمات فعلی</b>\n\n"
    "💳 شماره کارت: <code>{card_number}</code>\n"
    "👤 صاحب کارت: <b>{card_holder}</b>\n\n"
    "💰 base = <b>{base}</b>\n"
    "💰 per_gb = <b>{per_gb}</b>\n"
    "💰 per_day = <b>{per_day}</b>"
)
ADD_LOC_USAGE   = (
    "❗ استفاده:\n"
    "<code>/addlocation Germany 🇩🇪 | https://panel.example.com | "
    "MY_API_TOKEN | 3,5</code>"
)
ADD_LOC_OK      = "✅ لوکیشن «{name}» با شناسه <code>{id}</code> اضافه شد."
DEL_LOC_USAGE   = "❗ استفاده: <code>/dellocation &lt;id&gt;</code>"
DEL_LOC_OK      = "✅ لوکیشن <code>{id}</code> حذف شد."
DEL_LOC_NOTFOUND = "❗ لوکیشنی با این شناسه پیدا نشد."
TOGGLE_LOC_USAGE = "❗ استفاده: <code>/togglelocation &lt;id&gt;</code>"
TOGGLE_LOC_OK    = "✅ لوکیشن <code>{id}</code> اکنون <b>{state}</b> است."
LOC_LIST_EMPTY  = "هیچ لوکیشنی ثبت نشده است. با <code>/addlocation</code> یکی اضافه کنید."
LOC_LIST_HEADER = "📍 <b>لوکیشن‌های ثبت‌شده</b>\n"
LOC_LIST_ITEM   = (
    "• <code>#{id}</code> {state_emoji} <b>{name}</b>\n"
    "    base: <code>{base_url}</code>\n"
    "    inbounds: <code>{inbounds}</code>"
)

PENDING_EMPTY  = "هیچ سفارشی در انتظار بررسی نیست."
PENDING_HEADER = "🔍 <b>سفارش‌های در انتظار بررسی</b>\n"
PENDING_ITEM   = (
    "• سفارش <code>#{id}</code> — کاربر <code>{user_id}</code> — "
    "{volume}GB / {days}d — <b>{price}</b> ({created_at})"
)

REVIEW_ALREADY = "⚠️ این سفارش قبلاً بررسی شده است."
REVIEW_DECLINE_PROMPT = (
    "❌ دلیل رد را در یک پیام ارسال کنید (یا /cancel برای انصراف).\n"
    "این متن برای کاربر ارسال می‌شود."
)
REVIEW_DECLINE_SENT  = "✅ سفارش رد شد و کاربر مطلع شد."
REVIEW_ACCEPTED      = "✅ سفارش تأیید شد. در حال ساخت کانفیگ روی پنل..."
REVIEW_PROVISION_OK  = "🎉 سفارش با موفقیت فعال و برای کاربر ارسال شد."
REVIEW_PROVISION_ERR = "⚠️ خطا در فعال‌سازی روی پنل:\n<code>{error}</code>"
