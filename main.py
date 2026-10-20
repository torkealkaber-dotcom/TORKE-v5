import os
import logging
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# ========== الإعدادات ==========
# توكن البوت الثاني (الحماية)
TOKEN = "8772095954:AAFPp0GOiVJKYpodkCSd3PEFv-RvKTFWUwA"
DEVELOPER_ID = 8909680386

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== المتغيرات ==========
REQUIRED_CHANNEL = ""  # سيتم تعيينه من قبل المطور
SUPERMAX_LINK = "https://t.me/q_z_rn"

# حالات إعداد الاشتراك الإجباري
WAIT_FOR_CHANNEL = 1

# ========== الزر المزخرف ==========
def get_supermax_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ꜱᴜᴘᴇʀ ᴍᴀx", url=SUPERMAX_LINK)]
    ])

# ========== دالة إرسال الرسائل مع الزر ==========
async def send_msg(update: Update, text: str, reply_to: bool = False):
    kb = get_supermax_keyboard()
    if reply_to and update.message:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.effective_chat.send_message(text, reply_markup=kb, parse_mode="Markdown")

# ========== التحقق من الاشتراك ==========
async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ========== التحقق من صلاحيات المشرف ==========
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    user = update.effective_user
    if chat.type == "private":
        return user.id == DEVELOPER_ID
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

# ========== أمر البدء ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_subscribed(user_id, context):
        await send_msg(update, "⚠️ يجب الاشتراك في القناة أولاً.", reply_to=True)
        return
    
    await send_msg(update, "أهلاً بك في بوت الحماية (TORKE-v5).\nللمشرفين: اكتب **الاوامر** لعرض قائمة التحكم.", reply_to=True)

# ========== عرض الأوامر للمشرفين ==========
async def show_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return  # يتجاهل الرسالة إذا لم يكن مشرفاً

    text = (
        "🛡️ **قائمة أوامر الحماية:**\n"
        "قم بالرد على رسالة العضو واكتب:\n"
        "🔹 كتم\n"
        "🔹 طرد\n"
        "🔹 حظر\n"
        "🔹 تقيد\n"
        "🔹 رفع القيود\n"
        "🔹 الغاء كتم\n"
        "🔹 الغاء الحظر\n"
        "🔹 الغاء التقيد\n\n"
        "👨‍💻 **للمطور فقط:**\n"
        "🔸 تفعيل الاشتراك: لتعيين قناة الاشتراك الإجباري."
    )
    await send_msg(update, text, reply_to=True)

# ========== إعداد الاشتراك الإجباري ==========
async def set_required_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await send_msg(update, "⚠️ هذا الأمر للمطور فقط.", reply_to=True)
        return ConversationHandler.END

    await send_msg(update, "أرسل يوزر القناة (مثلاً `@MyChannel`) لتفعيل الاشتراك الإجباري.\nأو أرسل `الغاء` للإلغاء.", reply_to=True)
    return WAIT_FOR_CHANNEL

async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global REQUIRED_CHANNEL
    text = update.message.text.strip()
    
    if text == "الغاء":
        await send_msg(update, "✅ تم إلغاء العملية.", reply_to=True)
        return ConversationHandler.END
    
    channel = text if text.startswith("@") else f"@{text}"
    
    try:
        # التحقق من أن البوت مشرف في القناة
        bot_member = await context.bot.get_chat_member(chat_id=channel, user_id=context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            await send_msg(update, "⚠️ يجب أن يكون البوت **مشرفاً** في هذه القناة أولاً.", reply_to=True)
            return WAIT_FOR_CHANNEL
        
        REQUIRED_CHANNEL = channel
        await send_msg(update, f"✅ تم تفعيل الاشتراك الإجباري في القناة: {channel}", reply_to=True)
        
    except Exception as e:
        await send_msg(update, "⚠️ تعذر الوصول للقناة. تأكد من اليوزر وأن البوت مشرف فيها.", reply_to=True)
        return WAIT_FOR_CHANNEL

    return ConversationHandler.END

# ========== أوامر الحماية ==========
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, target.id, ChatPermissions(can_send_messages=False))
        await send_msg(update, f"✅ تم كتم {target.first_name}.", reply_to=True)
    except: await send_msg(update, "❌ فشل الكتم.", reply_to=True)

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await send_msg(update, f"✅ تم طرد {target.first_name}.", reply_to=True)
    except: await send_msg(update, "❌ فشل الطرد.", reply_to=True)

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, target.id)
        await send_msg(update, f"✅ تم حظر {target.first_name}.", reply_to=True)
    except: await send_msg(update, "❌ فشل الحظر.", reply_to=True)

async def restrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id, 
            ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False)
        )
        await send_msg(update, f"✅ تم تقييد {target.first_name}.", reply_to=True)
    except: await send_msg(update, "❌ فشل التقييد.", reply_to=True)

async def unrestrict_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id, target.id, 
            ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await send_msg(update, f"✅ تم رفع القيود عن {target.first_name}.", reply_to=True)
    except: await send_msg(update, "❌ فشل رفع القيود.", reply_to=True)

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context) or not update.message.reply_to_message: return
    target = update.message.reply_to_message.from_user
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, target.id)
        await send_msg(update, f"✅ تم إلغاء الحظر عن {target.first_name}.", reply_to=True)
    except: await send_msg(update, "❌ فشل إلغاء الحظر.", reply_to=True)

# ========== التشغيل ==========
def main():
    app = Application.builder().token(TOKEN).build()

    # محادثة إعداد الاشتراك الإجباري
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^تفعيل الاشتراك$"), set_required_channel)],
        states={
            WAIT_FOR_CHANNEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel)],
        },
        fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    # عرض الأوامر
    app.add_handler(MessageHandler(filters.Regex(r"^الاوامر$"), show_commands))
    
    # أوامر الحماية (تعمل بالرد)
    app.add_handler(MessageHandler(filters.Regex(r"^كتم$"), mute_user))
    app.add_handler(MessageHandler(filters.Regex(r"^طرد$"), kick_user))
    app.add_handler(MessageHandler(filters.Regex(r"^حظر$"), ban_user))
    app.add_handler(MessageHandler(filters.Regex(r"^تقيد$"), restrict_user))
    app.add_handler(MessageHandler(filters.Regex(r"^رفع القيود$"), unrestrict_user))
    app.add_handler(MessageHandler(filters.Regex(r"^الغاء كتم$"), unrestrict_user))
    app.add_handler(MessageHandler(filters.Regex(r"^الغاء الحظر$"), unban_user))
    app.add_handler(MessageHandler(filters.Regex(r"^الغاء التقيد$"), unrestrict_user))

    logger.info("TORKE-v5 Protection Bot is starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
