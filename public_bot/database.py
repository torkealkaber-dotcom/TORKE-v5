import aiosqlite
import sys
import os

# عشان يقرأ من الكونفيج الأساسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import PUBLIC_DB

async def init_db():
    async with aiosqlite.connect(PUBLIC_DB) as db:
        # جدول المستخدمين اللي ضافوا حساباتهم في البوت الفرعي
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # جدول الحسابات اللي الناس ضافتها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS client_accounts (
                phone TEXT PRIMARY KEY,
                session_path TEXT NOT NULL,
                owner_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_client_user(user_id, username, first_name):
    async with aiosqlite.connect(PUBLIC_DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user_id, username, first_name)
        )
        await db.commit()

async def add_client_account(phone, session_path, owner_id):
    async with aiosqlite.connect(PUBLIC_DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO client_accounts (phone, session_path, owner_id) VALUES (?, ?, ?)",
            (phone, session_path, owner_id)
        )
        await db.commit()

async def get_client_accounts(owner_id=None):
    async with aiosqlite.connect(PUBLIC_DB) as db:
        db.row_factory = aiosqlite.Row
        if owner_id:
            cursor = await db.execute("SELECT * FROM client_accounts WHERE owner_id = ?", (owner_id,))
        else:
            cursor = await db.execute("SELECT * FROM client_accounts")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
