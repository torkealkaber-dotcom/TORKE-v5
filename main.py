import asyncio
from telethon import TelegramClient
from config import BOT_TOKEN, API_ID, API_HASH
from database import init_db
from bot.handlers import register_handlers


async def main():
    # تهيئة قاعدة البيانات
    init_db()
    print("✅ تم تهيئة قاعدة البيانات")

    # إنشاء البوت
    bot = TelegramClient("control_bot", API_ID, API_HASH)

    # تسجيل المعالجات
    register_handlers(bot)

    # تشغيل البوت
    await bot.start(bot_token=BOT_TOKEN)
    print("🤖 البوت شغال...")

    await bot.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⛔ تم إيقاف البوت.")
