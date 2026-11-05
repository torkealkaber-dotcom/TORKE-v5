import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
PUBLIC_BOT_TOKEN = os.getenv("PUBLIC_BOT_TOKEN", "")

DEVELOPER_IDS_STR = os.getenv("DEVELOPER_IDS", "")
DEVELOPER_IDS = [int(x.strip()) for x in DEVELOPER_IDS_STR.split(",") if x.strip().isdigit()]

SESSIONS_DIR = os.getenv("SESSIONS_DIR", "./sessions")
MASTER_DB = os.getenv("MASTER_DB", "./bot.db")
PUBLIC_DB = os.getenv("PUBLIC_DB", "./public_bot.db")

DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", 50))
DELAY_MIN = int(os.getenv("DELAY_MIN", 45))
DELAY_MAX = int(os.getenv("DELAY_MAX", 90))

os.makedirs(SESSIONS_DIR, exist_ok=True)

if not API_ID or not API_HASH:
    raise ValueError("API_ID and API_HASH are required")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required")
if not PUBLIC_BOT_TOKEN:
    raise ValueError("PUBLIC_BOT_TOKEN is required")
