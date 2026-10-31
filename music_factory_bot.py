import asyncio
import logging
import os
import re

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream
from yt_dlp import YoutubeDL

OWNER_ID = 8909680386
FACTORY_BOT_TOKEN = os.getenv("FACTORY_BOT_TOKEN", "").strip()

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("pytgcalls").setLevel(logging.WARNING)

router = Router()
steps = {}
credentials = {}
workers = {}

HELP = (
    "🎵 مصنع بوتات الموسيقى\n"
    "/create - إنشاء بوت\n"
    "/cancel - إلغاء\n\n"
    "سيطلب المصنع Bot Token ثم API_ID ثم API_HASH ثم Session String."
)


def make_keyboard():
    # تمت إزالة style لأنه غير مدعوم في aiogram الرسمي
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="زر أخضر", callback_data="test1")],
        [InlineKeyboardButton(text="زر أزرق", callback_data="test2")],
        [InlineKeyboardButton(text="زر أحمر", callback_data="test3")],
    ])


async def delete_secret(message: Message):
    try:
        await message.delete()
    except Exception:
        pass


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
            "/stop إيقاف التشغيل",
            reply_markup=make_keyboard()
        )

    @music.callback_query(F.data.in_({"test1", "test2", "test3"}))
    async def music_buttons(callback: CallbackQuery):
        labels = {
            "test1": "زر أخضر",
            "test2": "زر أزرق",
            "test3": "زر أحمر"
        }
        await callback.answer(f"ضغطت على {labels[callback.data]}")

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
            await status.edit_text(
                "تعذر التشغيل. تأكد أن الحساب المساعد والبوت "
                "داخل المجموعة وأن المكالمة الصوتية متاحة."
            )

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

    dp.include_router(music)

    task = asyncio.create_task(dp.start_polling(bot))
    workers[owner_id] = (bot, assistant, calls, task)

    return bot_info.username or str(bot_info.id)


@router.message(Command("start", "help"))
async def start_factory(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        await message.answer("هذا المصنع مخصص للمطور فقط.")
        return

    await message.answer(HELP, reply_markup=make_keyboard())


@router.callback_query(F.data.in_({"test1", "test2", "test3"}))
async def factory_buttons(callback: CallbackQuery):
    if not callback.from_user or callback.from_user.id != OWNER_ID:
        await callback.answer("غير مسموح.", show_alert=True)
        return

    labels = {
        "test1": "زر أخضر",
        "test2": "زر أزرق",
        "test3": "زر أحمر"
    }

    await callback.answer(f"ضغطت على {labels[callback.data]}")


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
    await message.answer("أرسل Bot Token في الخاص.")


@router.message(Command("cancel"))
async def cancel_cmd(message: Message):
    if not message.from_user or message.from_user.id != OWNER_ID:
        return

    uid = message.from_user.id
    steps.pop(uid, None)
    credentials.pop(uid, None)

    await message.answer("تم الإلغاء.")


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

    if step == "token":
        if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{20,}", value):
            await message.answer("التوكن غير صحيح شكليًا. أعد إرساله أو /cancel.")
            return

        credentials[uid] = {"token": value}
        steps[uid] = "api_id"
        await message.answer("أرسل API_ID (أرقام فقط).")

    elif step == "api_id":
        if not value.isdigit():
            await message.answer("API_ID يجب أن يكون أرقامًا. حاول مرة أخرى.")
            return

        credentials[uid]["api_id"] = int(value)
        steps[uid] = "api_hash"
        await message.answer("أرسل API_HASH.")

    elif step == "api_hash":
        if len(value) < 20:
            await message.answer("API_HASH غير مكتمل على ما يبدو. أعد المحاولة.")
            return

        credentials[uid]["api_hash"] = value
        steps[uid] = "session"
        await message.answer("أرسل Session String للحساب المساعد.")

    elif step == "session":
        if len(value) < 40:
            await message.answer("Session String غير مكتملة على ما يبدو. أعد المحاولة.")
            return

        credentials[uid]["session"] = value
        steps[uid] = "creating"

        status = await message.answer(
            "⏳ جاري إنشاء البوت والتحقق من البيانات..."
        )

        try:
            username = await create_music_bot(uid, credentials[uid])

            await status.edit_text(
                f"✅ تم تشغيل بوت الموسيقى @{username}\n"
                "أضف البوت والحساب المساعد إلى مجموعة، "
                "وابدأ مكالمة صوتية جماعية، ثم استخدم /play."
            )

        except Exception as exc:
            logging.warning("Creation failed: %s: %s", type(exc).__name__, exc)

            await status.edit_text(
                "❌ فشل الإنشاء. راجع التوكن وبيانات API والجلسة، "
                "وتأكد من توافق إصدار المكتبات."
            )

        finally:
            credentials.pop(uid, None)
            steps.pop(uid, None)


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
