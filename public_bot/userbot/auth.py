import os
import sys
from telethon import TelegramClient

# عشان يقرأ من الكونفيج الأساسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_ID, API_HASH, SESSIONS_DIR

def get_session_path(phone: str) -> str:
    """توليد مسار ملف الجلسة بناءً على رقم الهاتف"""
    clean_phone = phone.replace("+", "").replace(" ", "")
    return os.path.join(SESSIONS_DIR, clean_phone)

async def create_client(phone: str):
    """إنشاء عميل تليثون وتسجيل الاتصال"""
    session_path = get_session_path(phone)
    client = TelegramClient(session_path, API_ID, API_HASH)
    await client.connect()
    return client, session_path

async def send_code(client: TelegramClient, phone: str):
    """إرسال كود التحقق للرقم المدخل"""
    return await client.send_code_request(phone)

async def sign_in_code(client: TelegramClient, phone: str, code: str):
    """تسجيل الدخول بالكود (يرمي SessionPasswordNeededError لو فيه 2FA)"""
    return await client.sign_in(phone=phone, code=code)

async def sign_in_password(client: TelegramClient, password: str):
    """إكمال تسجيل الدخول بكلمة مرور التحقق بخطوتين"""
    return await client.sign_in(password=password)

async def is_authorized(client: TelegramClient) -> bool:
    """هل الحساب مسجل دخول بالفعل؟"""
    return await client.is_user_authorized()

async def safe_disconnect(client: TelegramClient):
    """قطع الاتصال بأمان لتجنب أخطاء الذاكرة"""
    try:
        if client.is_connected():
            await client.disconnect()
    except Exception:
        pass
