import asyncio
import logging
import sys
import os

# عشان البوت يقدر يقرأ الملفات من الفولدر الأساسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from main_bot.database import init_db
from main_bot.bot.handlers import router as main_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - MASTER BOT - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("⏳ جاري تهيئة قاعدة بيانات البوت الأساسي...")
    await init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات.")

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(main_router)

    logger.info("🚀 جاري تشغيل البوت الأساسي...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("⛔ تم إيقاف البوت الأساسي.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ تم إيقاف البوت الأساسي يدوياً.")
