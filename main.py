import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from bot.handlers import router as main_router

# إعداد نظام تسجيل الأخطاء (Logging)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    # 1. تهيئة قاعدة البيانات
    logger.info("⏳ جاري تهيئة قاعدة البيانات...")
    await init_db()
    logger.info("✅ تم تهيئة قاعدة البيانات بنجاح.")

    # 2. إعداد البوت والمنسق (Dispatcher)
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # 3. ربط المعالجات (Handlers) بالمنسق
    dp.include_router(main_router)

    # 4. تنظيف التحديثات القديمة وبدء التشغيل
    logger.info("🚀 جاري تشغيل البوت...")
    try:
        # مسح الرسائل القديمة العالقة لتجنب تكرار الأوامر
        await bot.delete_webhook(drop_pending_updates=True)
        
        # بدء التشغيل (Polling)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("⛔ تم إيقاف البوت.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ تم إيقاف البوت يدوياً.")
