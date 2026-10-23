import os
import re
import json
import html
import logging

from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== الإعدادات =====
TOKEN = "8793121138:AAEFXs2NQB4FPxpZT4f-8Yi30TgFFpbsw8A"
DEVELOPER_ID = 8909680386
SUPERMAX_LINK = "https://t.me/q_z_rn"
SETTINGS_FILE = Path(os.getenv("SETTINGS_FILE", "settings.json"))
WAIT_FOR_CHANNEL_LINK = 1

# ===== تحميل وحفظ البيانات =====
def load_json(file_path, default):
    try:
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return default
    except Exception as e:
        return default

def save_json(file_path, data):
    try:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving: {e}")

settings = load_json(SETTINGS_FILE, {"required_channel": ""})

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
    if not await is_admin(update, context): 
        return ConversationHandler.END
    await update.effective_message.reply_text(
        "📢 أرسل الآن رابط القناة أو يوزرها (مثلاً: `@MyChannel`).\n⚠️ يجب أن يكون البوت مشرفاً في القناة.",
        parse_mode=ParseMode.MARKDOWN
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
            await update.message.reply_text("⚠️ البوت ليس مشرفاً في هذه القناة!")
            return WAIT_FOR_CHANNEL_LINK
        
        settings["required_channel"] = channel_username
        save_json(SETTINGS_FILE, settings)
        await update.message.reply_text(f"✅ تم تفعيل الاشتراك الإجباري على: {channel_username}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ تعذر الوصول للقناة: {e}")
        return WAIT_FOR_CHANNEL_LINK

async def cancel(update, context):
    context.user_data.clear()
    await update.message.reply_text("تم الإلغاء.")
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

# ===== أمر البدء وعرض الأوامر =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        channel = settings.get("required_channel", "")
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]]
        await update.effective_message.reply_text("⚠️ يجب عليك الاشتراك في القناة أولاً.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await send_msg(
        update.effective_message,
        "أهلاً بك في بوت الحماية (TORKE-v5).\nللمشرفين: اكتب **الاوامر** لعرض قائمة التحكم."
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

# ===== معالجة الرسائل (الحذف + إرسال رسالة مستقلة) =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not message.text: return
    text = message.text.strip()

    if text == "الاوامر":
        await show_commands(update, context)
        return

    # التحقق من الاشتراك للمستخدمين العاديين في المجموعة
    if update.effective_chat.type in ("group", "supergroup"):
        user_id = update.effective_user.id
        
        # إذا كان المستخدم مشرفاً، لا تحذف رسالته
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

        # للمستخدم العادي: التحقق من الاشتراك
        if not await check_subscription(user_id, context):
            channel = settings.get("required_channel", "")
            
            # 1. حذف رسالة المستخدم
            try:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id)
            except Exception as e:
                logger.error(f"Failed to delete message: {e}")

            # 2. إرسال رسالة تنبيه مستقلة في المجموعة (وليس كرد)
            keyboard = [[InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]]
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"⚠️ {update.effective_user.first_name}، يجب عليك الاشتراك في القناة أولاً لتتمكن من إرسال الرسائل.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
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
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(sub_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Protection bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
