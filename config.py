import os
from dotenv import load_dotenv

load_dotenv()

# بيانات API الأساسية
API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# قائمة المطورين
DEVELOPER_IDS_STR = os.getenv("DEVELOPER_IDS", "")
DEVELOPER_IDS = [int(x.strip()) for x in DEVELOPER_IDS_STR.split(",") if x.strip().isdigit()]

# المسارات
SESSIONS_DIR = os.getenv("SESSIONS_DIR", "./sessions")
DB_PATH = os.getenv("DB_PATH", "./bot.db")

# إعدادات النقل
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 50))
DELAY_MIN = int(os.getenv("DELAY_MIN", 45))
DELAY_MAX = int(os.getenv("DELAY_MAX", 90))

# إنشاء مجلد الجلسات لو مش موجود
os.makedirs(SESSIONS_DIR, exist_ok=True)

# التحقق من البيانات
if not API_ID or not API_HASH:
    raise ValueError("API_ID و API_HASH مطلوبين في ملف .env")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN مطلوب في ملف .env")

if not DEVELOPER_IDS:
    raise ValueError("DEVELOPER_IDS مطلوب في ملف .env (مفصولين بفاصلة)")
