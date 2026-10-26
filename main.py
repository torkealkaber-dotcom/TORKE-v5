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
# التوكن الجديد الخاص بك
TOKEN = "8834987117:AAHf4z7mdbCHbiTdHPRfjxDGfKBZki969Fg"
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

# ===== حالات المحادثة =====
class SubStates(StatesGroup):
    waiting_for_channel = State()

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

# ===== زر السوبر ماكس (أزرق) =====
def get_supermax_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ꜱᴜᴘᴇʀ ᴍᴀx", url=SUPERMAX_LINK, style="primary")]
    ])

# ===== الأزرار الثلاثة (الألوان الأساسية) =====
def get_start_buttons():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="زر أخضر", callback_data="btn_success", style="success")],
        [InlineKeyboardButton(text="زر أزرق", callback_data="btn_primary", style="primary")],
        [InlineKeyboardButton(text="زر أحمر", callback_data="btn_danger", style="danger")]
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

# ===== إعداد الاشتراك الإجباري =====
@router.message(F.text == "تفعيل الاشتراك")
async def set_forced_sub_start(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message, bot): return
    await message.reply("📢 أرسل الآن رابط القناة أو يوزرها (مثلاً: `@MyChannel`).\n⚠️ يجب أن يكون البوت مشرفاً في القناة.")
    await state.set_state(SubStates.waiting_for_channel)

@router.message(SubStates.waiting_for_channel)
async def set_forced_sub_save(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if text.startswith("https://t.me/"):
        channel_username = "@" + text.replace("https://t.me/", "").strip("/")
    elif text.startswith("@"):
        channel_username = text
    else:
        channel_username = f"@{text}"
    
    try:
        bot_member = await bot.get_chat_member(chat_id=channel_username, user_id=bot.id)
        if bot_member.status not in ["administrator", "creator"]:
            await message.reply("⚠️ البوت ليس مشرفاً في هذه القناة!")
            return
        
        settings["required_channel"] = channel_username
        save_json(SETTINGS_FILE, settings)
        await message.reply(f"✅ تم تفعيل الاشتراك الإجباري على: {channel_username}", reply_markup=get_supermax_keyboard())
    except Exception as e:
        await message.reply(f"⚠️ تعذر الوصول للقناة: {e}")
    await state.clear()

# ===== أوامر الحماية =====
@router.message(F.text == "كتم")
async def mute_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.restrict_chat_member(message.chat.id, target.id, ChatPermissions(can_send_messages=False))
        await message.reply(f"<blockquote>✅ تم كتم {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل الكتم.</blockquote>", parse_mode="HTML")

@router.message(F.text == "طرد")
async def kick_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.reply(f"<blockquote>✅ تم طرد {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل الطرد.</blockquote>", parse_mode="HTML")

@router.message(F.text == "حظر")
async def ban_user(message: Message, bot: Bot):
    if not await is_admin(message, bot) or not message.reply_to_message: return
    target = message.reply_to_message.from_user
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await message.reply(f"<blockquote>✅ تم حظر {target.first_name}.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    except: await message.reply("<blockquote>❌ فشل الحظر.</blockquote>", parse_mode="HTML")

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

    await update.reply("مرحباً بك", reply_markup=get_start_buttons())

@router.message(F.text == "الاوامر")
async def show_commands(message: Message, bot: Bot):
    if not await is_admin(message, bot): return
    text = (
        "🛡️ <b>قائمة أوامر الحماية:</b>\n"
        "قم بالرد على رسالة العضو واكتب:\n"
        "🔹 كتم\n🔹 طرد\n🔹 حظر\n\n"
        "👨‍💻 <b>للمشرفين فقط:</b>\n"
        "🔸 تفعيل الاشتراك: لتعيين قناة الاشتراك الإجباري."
    )
    await message.reply(f"<blockquote>{text}</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

# ===== معالجة ضغطات الأزرار =====
@router.callback_query(F.data.startswith("btn_"))
async def test_buttons(call: CallbackQuery):
    await call.answer()
    if call.data == "btn_success":
        await call.message.reply("<blockquote>ضغطت على الزر الأخضر</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    elif call.data == "btn_primary":
        await call.message.reply("<blockquote>ضغطت على الزر الأزرق</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
    elif call.data == "btn_danger":
        await call.message.reply("<blockquote>ضغطت على الزر الأحمر</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())

# ===== معالجة الرسائل (الشتائم + الاشتراك) =====
@router.message(F.text)
async def handle_message(message: Message, bot: Bot):
    if not message.text: return
    text = message.text.strip()

    if message.sender_chat:
        if message.sender_chat.username == "q_z_rn": return
    if message.from_user and message.from_user.is_bot: return

    if await is_admin(message, bot): return

    for word in BAD_WORDS:
        if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, re.IGNORECASE):
            try:
                await message.delete()
                await message.answer(f"<blockquote>⚠️ {message.from_user.first_name}، تم حذف رسالتك لاحتوائها على ألفاظ غير لائقة.</blockquote>", parse_mode="HTML", reply_markup=get_supermax_keyboard())
            except: pass
            return

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
