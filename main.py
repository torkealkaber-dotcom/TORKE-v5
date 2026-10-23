import os
import re
import json
import html
import logging

from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== الإعدادات =====
TOKEN = "8793121138:AAEFXs2NQB4FPxpZT4f-8Yi30TgFFpbsw8A"
DEVELOPER_ID = 8909680386
SUPERMAX_LINK = "https://t.me/q_z_rn"
SETTINGS_FILE = Path(os.getenv("SETTINGS_FILE", "settings.json"))

# ===== حالات المحادثة =====
WAIT_FOR_CHANNEL_LINK = 1
WAIT_FOR_NEW_COLOR = 2

# ===== تحميل وحفظ البيانات =====
def load_json(file_path, default):
    try:
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return default
    except Exception:
        return default

def save_json(file_path, data):
    try:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving: {e}")

# الإعدادات الافتراضية
DEFAULT_SETTINGS = {
    "required_channel": "",
    "emoji_order": "🟦🟩",
    "emoji_channel": "🟥🟨",
    "emoji_charge": "🟦🟩",
    "emoji_terms": "🟥🟨",
    "emoji_stats": "🟩"
}

settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
for k, v in DEFAULT_SETTINGS.items():
    if k not in settings: settings[k] = v

# ===== لوحة المطور =====
def get_dev_keyboard():
    return ReplyKeyboardMarkup([["⚙️ إعدادات الألوان"]], resize_keyboard=True)

# ===== أزرار القائمة الرئيسية =====
def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"{settings['emoji_order']} فحص طلبي", callback_data="check_order"), 
            InlineKeyboardButton(f"{settings['emoji_channel']} قناة البوت", url=SUPERMAX_LINK)
        ],
        [
            InlineKeyboardButton(f"{settings['emoji_charge']} شحن الكوكيز", callback_data="charge_cookies"), 
            InlineKeyboardButton(f"{settings['emoji_terms']} شروط الاستخدام", callback_data="terms")
        ],
        [
            InlineKeyboardButton(f"{settings['emoji_stats']} ✅ عدد الطلبات المكتملة: 24193328", callback_data="no_action")
        ]
    ])

# ===== زر السوبر ماكس =====
def get_supermax_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("ꜱᴜᴘᴇʀ ᴍᴀx", url=SUPERMAX_LINK)]])

async def send_msg(message, text, reply_markup=None):
    kb = reply_markup if reply_markup else get_supermax_keyboard()
    await message.reply_text(f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML, reply_markup=kb)

# ===== التحقق من الاشتراك =====
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channel = settings.get("required_channel", "")
    if not channel:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

async def is_admin(update, context):
    user = update.effective_user
    if not user: return False
    if user.id == DEVELOPER_ID: return True
    chat = update.effective_chat
    if not chat or chat.type == "private": return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except: return False

# ===== إعداد الاشتراك الإجباري =====
async def set_forced_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return ConversationHandler.END
    await update.effective_message.reply_text(
        "<blockquote>📢 أرسل الآن رابط القناة أو يوزرها (مثلاً: `@MyChannel`).</blockquote>",
        parse_mode=ParseMode.HTML
    )
    return WAIT_FOR_CHANNEL_LINK

async def set_forced_sub_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.startswith("https://t.me/"):
        channel_username = "@" + text.replace("https://t.me/", "").strip("/")
    elif text.startswith("@"):
        channel_username = text
    else:
        channel_username = f"@{text}"
    
    try:
        bot_member = await context.bot.get_chat_member(chat_id=channel_username, user_id=context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            await update.message.reply_text("<blockquote>⚠️ البوت ليس مشرفاً في هذه القناة!</blockquote>", parse_mode=ParseMode.HTML)
            return WAIT_FOR_CHANNEL_LINK
        
        settings["required_channel"] = channel_username
        save_json(SETTINGS_FILE, settings)
        await update.message.reply_text(f"<blockquote>✅ تم تفعيل الاشتراك الإجباري على: {channel_username}</blockquote>", parse_mode=ParseMode.HTML)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"<blockquote>⚠️ تعذر الوصول للقناة: {e}</blockquote>", parse_mode=ParseMode.HTML)
        return WAIT_FOR_CHANNEL_LINK

# ===== إعدادات الألوان (للمطور) =====
async def color_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID: return
    keyboard = [
        [InlineKeyboardButton("تغيير لون (فحص طلبي)", callback_data="color_emoji_order")],
        [InlineKeyboardButton("تغيير لون (قناة البوت)", callback_data="color_emoji_channel")],
        [InlineKeyboardButton("تغيير لون (شحن الكوكيز)", callback_data="color_emoji_charge")],
        [InlineKeyboardButton("تغيير لون (شروط الاستخدام)", callback_data="color_emoji_terms")],
        [InlineKeyboardButton("تغيير لون (الإحصائيات)", callback_data="color_emoji_stats")],
        [InlineKeyboardButton("🔙 إغلاق", callback_data="close_colors")]
    ]
    await update.message.reply_text("<blockquote>⚙️ <b>إعدادات ألوان الأزرار (الإيموجي):</b></blockquote>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

async def color_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "close_colors":
        await query.message.delete()
        return ConversationHandler.END
    
    key = query.data.replace("color_", "")
    context.user_data['color_key'] = key
    
    current_val = settings.get(key, "")
    await query.message.edit_text(
        f"<blockquote>القيمة الحالية:\n<code>{html.escape(current_val)}</code>\n\nأرسل <b>الإيموجي الجديد</b> (مثلاً 🟥 أو 🟦 أو 🟩):</blockquote>",
        parse_mode=ParseMode.HTML
    )
    return WAIT_FOR_NEW_COLOR

async def save_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get('color_key')
    if not key: return ConversationHandler.END
    
    new_emoji = update.message.text.strip()
    settings[key] = new_emoji
    save_json(SETTINGS_FILE, settings)
    
    await update.message.reply_text(f"<blockquote>✅ تم تغيير اللون إلى: {new_emoji}</blockquote>", reply_markup=get_dev_keyboard(), parse_mode=ParseMode.HTML)
    context.user_data.clear()
    return ConversationHandler.END

# ===== أوامر الحماية =====
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=False))
        await send_msg(update.effective_message, f"✅ تم كتم {target.first_name}.")
    except: await send_msg(update.effective_message, "❌ فشل الكتم.")

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await send_msg(update.effective_message, f"✅ تم طرد {target.first_name}.")
    except: await send_msg(update.effective_message, "❌ فشل الطرد.")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await send_msg(update.effective_message, f"✅ تم حظر {target.first_name}.")
    except: await send_msg(update.effective_message, "❌ فشل الحظر.")

async def restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id, 
            ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False)
        )
        await send_msg(update.effective_message, f"✅ تم تقييد {target.first_name}.")
    except: await send_msg(update.effective_message, "❌ فشل التقييد.")

async def unrestrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id, 
            ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await send_msg(update.effective_message, f"✅ تم رفع القيود عن {target.first_name}.")
    except: await send_msg(update.effective_message, "❌ فشل رفع القيود.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await send_msg(update.effective_message, f"✅ تم إلغاء الحظر عن {target.first_name}.")
    except: await send_msg(update.effective_message, "❌ فشل إلغاء الحظر.")

# ===== معالجة أزرار القائمة =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_order":
        await query.message.reply_text("<blockquote>🔍 جاري فحص طلبك...</blockquote>", parse_mode=ParseMode.HTML)
    elif query.data == "charge_cookies":
        await query.message.reply_text("<blockquote>🛒 يرجى إرسال الكمية المطلوبة.</blockquote>", parse_mode=ParseMode.HTML)
    elif query.data == "terms":
        await query.message.reply_text("<blockquote>📜 شروط الاستخدام: يرجى احترام القوانين.</blockquote>", parse_mode=ParseMode.HTML)
    
    # الأزرار test1, test2, test3 من الكود الخاص بك
    elif query.data == "test1":
        await query.answer("لقد ضغطت على الزر الأخضر", show_alert=True)
    elif query.data == "test2":
        await query.answer("لقد ضغطت على الزر الأزرق", show_alert=True)
    elif query.data == "test3":
        await query.answer("لقد ضغطت على الزر الأحمر", show_alert=True)

# ===== أمر البدء =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        channel = settings.get("required_channel", "")
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]]
        await update.effective_message.reply_text("<blockquote>⚠️ يجب عليك الاشتراك في القناة أولاً.</blockquote>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return

    # ===== الكود الذي طلبت إضافته (كما هو) =====
    start_text = "مرحباً بك"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🟩 زر لون اخضر", callback_data="test1")],
        [InlineKeyboardButton("🟦 زر لون ازرق", callback_data="test2")],
        [InlineKeyboardButton("🟥 زر لون احمر", callback_data="test3")]
    ])
    # إرسال الرسالة التي تحتوي على هذه الأزرار
    await update.message.reply_text(start_text, reply_markup=keyboard)
    # ============================================

    # إظهار لوحة المطور له فقط
    if user_id == DEVELOPER_ID:
        await update.effective_message.reply_text(
            "👨‍💻 لوحة تحكم المطور مفعلة الآن:",
            reply_markup=get_dev_keyboard()
        )

async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return
    text = (
        "🛡️ **قائمة أوامر الحماية:**\n"
        "قم بالرد على رسالة العضو واكتب:\n"
        "🔹 كتم\n🔹 طرد\n🔹 حظر\n🔹 تقيد\n🔹 رفع القيود\n"
        "🔹 الغاء كتم\n🔹 الغاء الحظر\n🔹 الغاء التقيد\n\n"
        "👨‍💻 **للمشرفين فقط:**\n🔸 تفعيل الاشتراك: لتعيين قناة الاشتراك الإجباري."
    )
    await send_msg(update.effective_message, text)

# ===== معالجة الرسائل =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text: return
    text = message.text.strip()

    if text == "الاوامر":
        await show_commands(update, context)
        return

    if text == "⚙️ إعدادات الألوان" and update.effective_user.id == DEVELOPER_ID:
        await color_settings_menu(update, context)
        return

    if update.effective_chat.type in ("group", "supergroup"):
        user_id = update.effective_user.id
        
        if await is_admin(update, context):
            if text == "كتم": await mute_user(update, context)
            elif text == "طرد": await kick_user(update, context)
            elif text == "حظر": await ban_user(update, context)
            elif text == "تقيد": await restrict_user(update, context)
            elif text == "رفع القيود": await unrestrict_user(update, context)
            elif text == "الغاء كتم": await unrestrict_user(update, context)
            elif text == "الغاء الحظر": await unban_user(update, context)
            elif text == "الغاء التقيد": await unrestrict_user(update, context)
            return

        if not await check_subscription(user_id, context):
            channel = settings.get("required_channel", "")
            
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            keyboard = [[InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]]
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"<blockquote>⚠️ {update.effective_user.first_name}، يجب عليك الاشتراك في القناة أولاً لتتمكن من إرسال الرسائل.</blockquote>",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode=ParseMode.HTML
                )
            except Exception as e:
                logger.error(f"Failed to send alert: {e}")
            return

# ===== التشغيل =====
def main():
    if not TOKEN: return

    app = Application.builder().token(TOKEN).build()

    sub_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^تفعيل الاشتراك$"), set_forced_sub_start)],
        states={WAIT_FOR_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_forced_sub_save)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    color_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(color_callback, pattern="^color_")],
        states={WAIT_FOR_NEW_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_color)]},
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(sub_conv)
    app.add_handler(color_conv)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Protection bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
