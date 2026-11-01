import os
from dotenv import load_dotenv

load_dotenv()

# بيانات API الأساسية
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEVELOPER_ID = int(os.getenv("DEVELOPER_ID"))

# المسارات
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "./sessions")
DB_PATH = os.getenv("DB_PATH", "./bot.db")

# إعدادات النقل
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 50))
DELAY_MIN = int(os.getenv("DELAY_MIN", 45))
DELAY_MAX = int(os.getenv("DELAY_MAX", 90))

# إنشاء مجلد الجلسات لو مش موجود
os.makedirs(SESSIONS_DIR, exist_ok=True)

# التحقق من وجود البيانات الأساسية
if not API_ID or not API_HASH:
    raise ValueError("API_ID و API_HASH مطلوبين في ملف .env")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN مطلوب في ملف .env")

if not DEVELOPER_ID:
    raise ValueError("DEVELOPER_ID مطلوب في ملف .env")
