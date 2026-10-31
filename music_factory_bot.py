import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardMarkup, KeyboardButton
)
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneCodeExpired
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from yt_dlp import YoutubeDL

# ⚠️ تنبيه: قم بتغيير هذا التوكن لأنه أصبح مكشوفاً
OWNER_ID = 8909680386
FACTORY_BOT_TOKEN = "9044536453:AAFAAXVPZZv1zQ2BWldjCeiYNfVS3caRxT4"

# ⬇️⬇️ ضع بيانات API الخاصة بك هنا (مرة واحدة فقط) ⬇️⬇️
GLOBAL_API_ID = 1234567              # <--- ضع الـ API_ID هنا (أرقام فقط)
GLOBAL_API_HASH = "ضع_الـ_API_HASH_هنا" # <--- ضع الـ API_HASH هنا (بين علامات التنصيص)
# ⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️⬆️

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)

router = Router()
steps = {}
credentials = {}
workers = {}
temp_clients = {}

HELP = (
    "🎵 مصنع بوتات الموسيقى\n"
    "/create - إنشاء بوت\n"
    "/cancel - إلغاء\n\n"
    "سيطلب المصنع: التوكن، رقم الهاتف، كود التحقق فقط."
)

# ==========================================
# 1. الأزرار
# ==========================================

def make_inline_keyboard():
    """الأزرار المضمنة (بدون style لتجنب خطأ ImportError)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="زر أخضر", callback_data="test1")],
        [InlineKeyboardButton(text="زر أزرق", callback_data="test2")],
        [InlineKeyboardButton(text="زر أحمر", callback_data="test3")]
    ])

def make_reply_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 تشغيل"), KeyboardButton(text="⏸ إيقاف مؤقت")],
            [KeyboardButton(text="▶️ استكمال"), KeyboardButton(text="⏹ إيقاف")]
        ],
        resize_keyboard=True,
        input_field_placeholder="اكتب اسم الأغنية هنا..."
    )

async def delete_secret(message: Message):
    try:
        await message.delete()
    except Exception:
        pass

# ==========================================
# 2. إنشاء بوت الموسيقى
# ==========================================

async def create_music_bot(owner_id, data):
    bot = Bot(data["token"])
    bot_info = await bot.get_me()

    assistant = Client(
        name=f"assistant_{owner_id}",
        api_id=data["api_id"],
        api_hash=data["api_hash"],
        session_string=data["session"],
        in_memory=True,
    )

    await assistant.start()

    calls = PyTgCalls(assistant)
    await calls.start()

    dp = Dispatcher()
    music = Router()

    @music.message(Command("start", "help"))
    async def help_cmd(message: Message):
        await message.answer(
            "🎶 أوامر الموسيقى:\n"
            "/play اسم الأغنية أو الرابط\n"
            "/pause إيقاف مؤقت\n"
            "/resume استكمال\n"
            "/stop إيقاف التشغيل\n\n"
            "استخدم الأزرار بالأسفل للتحكم السريع.",
            reply_markup=make_reply_keyboard()
        )

    @music.message(F.text == "🎵 تشغيل")
    async def play_text_btn(message: Message):
        await message.answer("للتشغيل يرجى كتابة الأمر هكذا:\n`/play اسم الأغنية`")

    @music.message(Command("play"))
    async def play_cmd(message: Message):
        if message.chat.type not in ("group", "supergroup"):
            await message.answer("استخدم الأمر داخل مجموعة.")
            return

        query = message.text.partition(" ")[2].strip() if message.text else ""

        if not query:
            await message.answer("اكتب: /play اسم الأغنية أو الرابط")
            return

        status = await message.answer("🔎 جاري البحث...")

        try:
            def get_audio():
                opts = {
                    "format": "bestaudio/best",
                    "quiet": True,
                    "no_warnings": True,
                    "noplaylist": True,
                    "default_search": "ytsearch",
                }
                with YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(query, download=False)
                    if info.get("entries"):
                        info = next(x for x in info["entries"] if x)
                    return info["url"], info.get("title", "Audio")

            url, title = await asyncio.to_thread(get_audio)

            await calls.play(message.chat.id, MediaStream(url))
            await status.edit_text(f"▶️ بدأ التشغيل: {title}")

        except Exception as exc:
            logging.warning("Playback error: %s: %s", type(exc).__name__, exc)
            await status.edit_text("تعذر التشغيل. تأكد من وجود مكالمة صوتية.")

    @music.message(Command("pause"))
    async def pause_cmd(message: Message):
        try:
            await calls.pause(message.chat.id)
            await message.answer("⏸ تم الإيقاف المؤقت.")
        except Exception:
            await message.answer("لا يوجد تشغيل نشط.")

    @music.message(Command("resume"))
    async def resume_cmd(message: Message):
        try:
            await calls.resume(message.chat.id)
            await message.answer("▶️ تم الاستكمال.")
        except Exception:
            await message.answer("لا يوجد تشغيل متوقف مؤقتًا.")

    @music.message(Command("stop"))
    async def stop_cmd(message: Message):
        try:
            await calls.leave_call(message.chat.id)
            await message.answer("⏹ تم إيقاف التشغيل.")
        except Exception:
            await message.answer("لا يوجد تشغيل نشط.")

    @music.callback_query(F.data.in_({"test1", "test2", "test3"}))
    async def music_buttons(callback: CallbackQuery):
        labels = {"test1": "زر أخضر", "test2": "زر أزرق", "test3": "زر أحمر"}
        await callback.answer(f"ضغطت على {labels[callback.data]}")

    dp.include_router(music)

    task = asyncio.create_task(dp.start_polling(bot))
    workers[owner_id] = (bot, assistant, calls, task)

    return bot_info.username or str(bot_info.id)

# ==========================================
# 3. أوامر المصنع الأساسي
# ==========================================

@router.message(Command("start", "help"))
async def start_factory(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.answer("هذا المصنع مخصص للمطور فقط.")
        return

    await message.answer(HELP, reply_markup=make_inline_keyboard())

@router.callback_query(F.data.in_({"test1", "test2", "test3"}))
async def factory_buttons(callback: CallbackQuery):
    if not callback.from_user or callback.from_user.id != OWNER_ID:
        await callback.answer("غير مسموح.", show_alert=True)
        return
    labels = {"test1": "زر أخضر", "test2": "زر أزرق", "test3": "زر أحمر"}
    await callback.answer(f"ضغطت على {labels[callback.data]}")

@router.message(Command("cancel"))
async def cancel_cmd(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    uid = message.from_user.id
    steps.pop(uid, None)
    credentials.pop(uid, None)
    
    if uid in temp_clients:
        try:
            await temp_clients[uid].disconnect()
        except:
            pass
        del temp_clients[uid]

    await message.answer("تم الإلغاء.")

@router.message(Command("create"))
async def create_cmd(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.answer("غير مسموح لك باستخدام المصنع.")
        return

    if message.chat.type != "private":
        await message.answer("استخدم /create في الخاص مع المصنع.")
        return

    uid = message.from_user.id

    if uid in workers:
        await message.answer("لديك بوت موسيقى يعمل بالفعل.")
        return

    steps[uid] = "token"
    await message.answer("1️⃣ أرسل Bot Token الخاص بالبوت الجديد في الخاص.")

# ==========================================
# 4. استقبال البيانات (تسجيل الدخول برقم الهاتف)
# ==========================================

@router.message(F.text)
async def collect(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    uid = message.from_user.id
    step = steps.get(uid)

    if not step or message.chat.type != "private":
        return

    value = (message.text or "").strip()
    await delete_secret(message)

    # --- الخطوة 1: التوكن ---
    if step == "token":
        if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{20,}", value):
            await message.answer("التوكن غير صحيح. أعد إرساله أو /cancel.")
            return

        credentials[uid] = {
            "token": value,
            "api_id": GLOBAL_API_ID,      # استخدام القيمة الثابتة
            "api_hash": GLOBAL_API_HASH   # استخدام القيمة الثابتة
        }
        steps[uid] = "phone"
        await message.answer("2️⃣ أرسل رقم هاتف الحساب المساعد مع رمز الدولة.\nمثال: +201012345678")

    # --- الخطوة 2: رقم الهاتف ---
    elif step == "phone":
        phone = value.replace(" ", "")
        if not phone.startswith("+"):
            phone = "+" + phone
            
        await message.answer("⏳ جاري إرسال كود التحقق إلى تيليجرام...")
        
        try:
            client = Client(
                name=f"temp_{uid}",
                api_id=credentials[uid]["api_id"],
                api_hash=credentials[uid]["api_hash"],
                in_memory=True
            )
            await client.connect()
            
            sent_code = await client.send_code(phone)
            temp_clients[uid] = client
            credentials[uid]["phone"] = phone
            credentials[uid]["phone_code_hash"] = sent_code.phone_code_hash
            
            steps[uid] = "code"
            await message.answer("3️⃣ أرسل كود التحقق الذي وصلك في تيليجرام (أرقام فقط).\nمثال: 12345")
            
        except Exception as e:
            logging.error(f"Phone error: {e}")
            await message.answer(f"❌ حدث خطأ أثناء إرسال الكود. تأكد من الرقم.\n{type(e).__name__}")
            steps.pop(uid, None)
            credentials.pop(uid, None)

    # --- الخطوة 3: كود التحقق ---
    elif step == "code":
        client = temp_clients.get(uid)
        if not client:
            await message.answer("حدث خطأ. أعد البدء بـ /create")
            return

        try:
            await client.sign_in(
                phone_number=credentials[uid]["phone"],
                phone_code_hash=credentials[uid]["phone_code_hash"],
                phone_code=value
            )
            
            session_string = await client.export_session_string()
            credentials[uid]["session"] = session_string
            steps[uid] = "creating"
            await message.answer("✅ تم تسجيل الدخول بنجاح! ⏳ جاري إنشاء البوت...")
            
            username = await create_music_bot(uid, credentials[uid])
            await message.answer(
                f"✅ تم تشغيل بوت الموسيقى @{username}\n"
                "أضف البوت والحساب المساعد إلى مجموعة، وابدأ مكالمة صوتية، ثم استخدم /play."
            )
            
            await client.disconnect()
            del temp_clients[uid]
            credentials.pop(uid, None)
            steps.pop(uid, None)

        except SessionPasswordNeeded:
            steps[uid] = "password"
            await message.answer("🔐 حسابك محمي بالتحقق بخطوتين.\n4️⃣ أرسل كلمة مرور تيليجرام (2FA Password).")
        except (PhoneCodeInvalid, PhoneCodeExpired) as e:
            await message.answer("❌ الكود غير صحيح أو منتهي الصلاحية. أعد إرساله أو /cancel.")
        except Exception as e:
            logging.error(f"Code error: {e}")
            await message.answer(f"❌ حدث خطأ: {type(e).__name__}")
            steps.pop(uid, None)
            credentials.pop(uid, None)
            if uid in temp_clients:
                await temp_clients[uid].disconnect()
                del temp_clients[uid]

    # --- الخطوة 4: التحقق بخطوتين (2FA) ---
    elif step == "password":
        client = temp_clients.get(uid)
        if not client:
            await message.answer("حدث خطأ. أعد البدء بـ /create")
            return

        try:
            await client.check_password(value)
            
            session_string = await client.export_session_string()
            credentials[uid]["session"] = session_string
            steps[uid] = "creating"
            await message.answer("✅ تم تسجيل الدخول بنجاح! ⏳ جاري إنشاء البوت...")
            
            username = await create_music_bot(uid, credentials[uid])
            await message.answer(
                f"✅ تم تشغيل بوت الموسيقى @{username}\n"
                "أضف البوت والحساب المساعد إلى مجموعة، وابدأ مكالمة صوتية، ثم استخدم /play."
            )
            
            await client.disconnect()
            del temp_clients[uid]
            credentials.pop(uid, None)
            steps.pop(uid, None)

        except Exception as e:
            logging.error(f"2FA error: {e}")
            await message.answer("❌ كلمة المرور غير صحيحة. حاول مرة أخرى أو /cancel.")

# ==========================================
# 5. تشغيل المصنع
# ==========================================

async def main():
    if not FACTORY_BOT_TOKEN:
        raise RuntimeError("Set FACTORY_BOT_TOKEN in the environment.")

    factory = Bot(FACTORY_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    try:
        await dp.start_polling(factory)
    finally:
        for bot, assistant, calls, task in workers.values():
            task.cancel()
            try:
                await bot.session.close()
            except Exception:
                pass
            try:
                await calls.stop()
            except Exception:
                pass
            try:
                await assistant.stop()
            except Exception:
                pass

if __name__ == "__main__":
    asyncio.run(main())
