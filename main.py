import logging
import re
import os
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ===== الإعدادات =====
TOKEN = "8842494673:AAFFGWm33My7Wkca6dS3JOgD5qIr08ff_uQ"
DEVELOPER_ID = 8909680386
SUPERMAX_LINK = "https://t.me/q_z_rn"
SETTINGS_FILE = Path(os.getenv("SETTINGS_FILE", "settings.json"))

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# ===== قائمة الكلمات الممنوعة =====
BAD_WORDS = [
    "كس", "كسمك", "كسم", "كسها", "كسمو", "كسمك", "كس امك", "كسم ابوك",
    "عرص", "يعرص", "شرموط", "شرموطة", "قحبة", "قحب", "عاهر", "عاهرة",
    "خول", "خولات", "منيك", "منيوك", "زبي", "زب", "طيز", "طيزك",
    "كلب", "كلبة", "حمار", "حمارة", "غبي", "غبية", "حقير", "حقيرة",
    "تافه", "خرا", "زبالة", "قذر", "قذرة", "وسخ", "وسخة", "حقير"
]

# ===== تحميل وحفظ البيانات =====
def load_json(file_path, default):
    try:
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return default
    except:
        return default

def save_json(file_path, data):
    try:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving: {e}")

settings = load_json(SETTINGS_FILE, {"required_channel": ""})

# ===== زر السوبر ماكس =====
def get_supermax_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ꜱᴜᴘᴇʀ ᴍᴀx", url=SUPERMAX_LINK)]
    ])

# ===== الأزرار الثلاثة التي تحتوي على style =====
def get_start_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="زر أخضر", callback_data="test1", style="success")],
        [InlineKeyboardButton(text="زر أزرق", callback_data="test2", style="primary")],
        [InlineKeyboardButton(text="زر أحمر", callback_data="test3", style="danger")]
    ])

# ===== التحقق من الاشتراك =====
async def check_subscription(user_id: int, bot: Bot) -> bool:
    channel = settings.get("required_channel", "")
    if not channel:
        return True
    try:
        member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def is_admin(message: Message, bot: Bot) -> bool:
    if not message.from_user: return False
    if message.from_user.id == DEVELOPER_ID: return True
    if message.chat.type == "private": return False
    try:
        member = await bot.get_chat_member(message.chat.id, message.from_user.id)
        return member.status in ["administrator", "creator"]
    except: return False

# ===== أوامر الحماية =====
async def mute_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, ChatPermissions(can_send_messages=False))
        await message.reply(f"<blockquote>✅ تم كتم {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل الكتم.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

async def kick_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"<blockquote>✅ تم طرد {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل الطرد.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

async def ban_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"<blockquote>✅ تم حظر {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل الحظر.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

async def restrict_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, ChatPermissions(can_send_messages=False, can_send_media_messages=False, can_send_other_messages=False, can_add_web_page_previews=False))
        await message.reply(f"<blockquote>✅ تم تقييد {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل التقييد.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

async def unrestrict_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, ChatPermissions(can_send_messages=True, can_send_media_messages=True, can_send_other_messages=True, can_add_web_page_previews=True))
        await message.reply(f"<blockquote>✅ تم رفع القيود عن {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل رفع القيود.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

async def unban_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"<blockquote>✅ تم إلغاء الحظر عن {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل إلغاء الحظر.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

# ===== أمر البدء =====
@router.message(Command("start"))
async def start(update: Message, bot: Bot):
    user_id = update.from_user.id
    if not await check_subscription(user_id, bot):
        channel = settings.get("required_channel", "")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]
        ])
        await update.reply("⚠️ يجب عليك الاشتراك في القناة أولاً.", reply_markup=keyboard)
        return

    # إرسال رسالة الترحيب مع الأزرار الثلاثة (الملونة)
    await update.reply("مرحباً بك", reply_markup=get_start_buttons())

# ===== معالجة أزرار test =====
@router.callback_query(F.data.startswith("test"))
async def test_buttons(call: CallbackQuery):
    await call.answer()
    if call.data == "test1":
        await call.message.reply("<blockquote>ضغطت على الزر الأخضر</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    elif call.data == "test2":
        await call.message.reply("<blockquote>ضغطت على الزر الأزرق</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    elif call.data == "test3":
        await call.message.reply("<blockquote>ضغطت على الزر الأحمر</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

# ===== معالجة الرسائل =====
@router.message(F.text)
async def handle_message(message: Message, bot: Bot):
    if not message.text: return
    text = message.text.strip()

    # تجاهل رسائل القنوات والبوتات
    if message.sender_chat:
        if message.sender_chat.username == "q_z_rn":
            return
    if message.from_user and message.from_user.is_bot:
        return

    # عرض الأوامر
    if text == "الاوامر":
        if not await is_admin(message, bot): return
        text_cmd = (
            "🛡️ <b>قائمة أوامر الحماية:</b>\n"
            "قم بالرد على رسالة العضو واكتب:\n"
            "🔹 كتم\n🔹 طرد\n🔹 حظر\n🔹 تقيد\n🔹 رفع القيود\n"
            "🔹 الغاء كتم\n🔹 الغاء الحظر\n🔹 الغاء التقيد\n\n"
        )
        await message.reply(f"<blockquote>{text_cmd}</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
        return

    # تنفيذ الأوامر للمشرفين
    if await is_admin(message, bot):
        if text == "كتم": await mute_user(message, bot)
        elif text == "طرد": await kick_user(message, bot)
        elif text == "حظر": await ban_user(message, bot)
        elif text == "تقيد": await restrict_user(message, bot)
        elif text == "رفع القيود": await unrestrict_user(message, bot)
        elif text == "الغاء كتم": await unrestrict_user(message, bot)
        elif text == "الغاء الحظر": await unban_user(message, bot)
        elif text == "الغاء التقيد": await unrestrict_user(message, bot)
        return

    # منع الشتائم للمستخدمين العاديين
    for word in BAD_WORDS:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, re.IGNORECASE):
            try:
                await message.delete()
                await message.answer(f"<blockquote>⚠️ {message.from_user.first_name}، تم حذف رسالتك لاحتوائها على ألفاظ غير لائقة.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
            except: pass
            return

    # منع غير المشتركين
    if not await check_subscription(message.from_user.id, bot):
        channel = settings.get("required_channel", "")
        try:
            await message.delete()
        except: pass
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]
        ])
        try:
            await message.answer(f"<blockquote>⚠️ {message.from_user.first_name}، يجب عليك الاشتراك في القناة أولاً.</blockquote>", reply_markup=keyboard, parse_mode="HTML")
        except: pass
        return

# ===== التشغيل =====
async def main():
    if not TOKEN: return
    bot = Bot(token=TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("Protection bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
