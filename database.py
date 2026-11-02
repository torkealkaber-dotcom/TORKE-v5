import aiosqlite
from datetime import datetime
from config import DB_PATH


async def init_db():
    """إنشاء الجداول لو مش موجودة"""
    async with aiosqlite.connect(DB_PATH) as db:
        # جدول الحسابات
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                phone TEXT PRIMARY KEY,
                session_path TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_banned INTEGER DEFAULT 0,
                is_frozen INTEGER DEFAULT 0,
                is_restricted INTEGER DEFAULT 0,
                banned_until TIMESTAMP,
                daily_count INTEGER DEFAULT 0,
                last_reset DATE
            )
        """)
        
        # جدول عمليات النقل
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transfers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                target TEXT,
                mode TEXT DEFAULT 'hidden',
                total_limit INTEGER DEFAULT 0,
                account_limit INTEGER DEFAULT 50,
                delay_seconds INTEGER DEFAULT 0,
                added INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                skipped INTEGER DEFAULT 0,
                status TEXT DEFAULT 'running',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP
            )
        """)
        
        # جدول الإعدادات العامة
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.commit()


# ================== إدارة الحسابات ==================

async def add_account(phone, session_path):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO accounts (phone, session_path) VALUES (?, ?)",
            (phone, session_path)
        )
        await db.commit()


async def get_accounts(status_filter=None):
    """
    status_filter:
    None = كل الحسابات
    'created' = المصنوعة
    'banned' = المحظورة
    'frozen' = المجمدة
    'restricted' = المقيدة
    """
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        query = "SELECT * FROM accounts"
        params = ()
        
        if status_filter == 'banned':
            query += " WHERE is_banned = 1"
        elif status_filter == 'frozen':
            query += " WHERE is_frozen = 1"
        elif status_filter == 'restricted':
            query += " WHERE is_restricted = 1"
        elif status_filter == 'created':
            query += " WHERE is_banned = 0 AND is_frozen = 0 AND is_restricted = 0"
            
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def update_account_status(phone, status, value):
    """تحديث حالة حساب (is_banned, is_frozen, is_restricted)"""
    allowed_statuses = ['is_banned', 'is_frozen', 'is_restricted']
    if status not in allowed_statuses:
        return False
        
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE accounts SET {status} = ? WHERE phone = ?",
            (value, phone)
        )
        await db.commit()
        return True


async def delete_account(phone):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM accounts WHERE phone = ?", (phone,))
        await db.commit()


# ================== إدارة عمليات النقل ==================

async def create_transfer(source, target, mode, total_limit, account_limit, delay_seconds):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO transfers (source, target, mode, total_limit, account_limit, delay_seconds) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (source, target, mode, total_limit, account_limit, delay_seconds)
        )
        await db.commit()
        return cursor.lastrowid


async def get_active_transfer():
    """جلب عملية نقل شغالة حالياً"""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM transfers WHERE status = 'running' ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def update_transfer_status(transfer_id, status):
    async with aiosqlite.connect(DB_PATH) as db:
        finished_at = datetime.now().isoformat() if status in ['finished', 'stopped'] else None
        await db.execute(
            "UPDATE transfers SET status = ?, finished_at = ? WHERE id = ?",
            (status, finished_at, transfer_id)
        )
        await db.commit()


async def update_transfer_stats(transfer_id, added, failed, skipped):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """UPDATE transfers 
               SET added = added + ?, failed = failed + ?, skipped = skipped + ? 
               WHERE id = ?""",
            (added, failed, skipped, transfer_id)
        )
        await db.commit()


# ================== إعدادات عامة ==================

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )
        await db.commit()


async def get_setting(key, default=None):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row[0] if row else default
