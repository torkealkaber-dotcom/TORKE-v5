import sqlite3
from datetime import datetime, date
from config import DB_PATH


def init_db():
    """إنشاء الجداول لو مش موجودة"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            phone TEXT PRIMARY KEY,
            session_path TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0,
            banned_until TIMESTAMP,
            daily_count INTEGER DEFAULT 0,
            last_reset DATE
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            target TEXT,
            added INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            skipped INTEGER DEFAULT 0,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_account(phone, session_path):
    """إضافة حساب جديد أو تحديثه"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR REPLACE INTO accounts (phone, session_path) VALUES (?, ?)",
        (phone, session_path)
    )
    conn.commit()
    conn.close()


def get_accounts(include_banned=False):
    """جلب الحسابات المتاحة"""
    conn = sqlite3.connect(DB_PATH)
    if include_banned:
        rows = conn.execute(
            "SELECT phone, session_path FROM accounts"
        ).fetchall()
    else:
        now = datetime.now().isoformat()
        rows = conn.execute(
            """SELECT phone, session_path FROM accounts
               WHERE is_banned = 0
               OR banned_until IS NULL
               OR banned_until < ?""",
            (now,)
        ).fetchall()
    conn.close()
    return rows


def delete_account(phone):
    """حذف حساب"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM accounts WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()


def ban_account(phone, hours=24):
    """حظر حساب مؤقتاً"""
    from datetime import timedelta
    until = (datetime.now() + timedelta(hours=hours)).isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE accounts SET is_banned = 1, banned_until = ? WHERE phone = ?",
        (until, phone)
    )
    conn.commit()
    conn.close()


def increment_daily(phone):
    """زيادة العداد اليومي وإعادة تعيينه لو يوم جديد"""
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT daily_count, last_reset FROM accounts WHERE phone = ?",
        (phone,)
    ).fetchone()
    if not row:
        conn.close()
        return 0

    count, last_reset = row
    if last_reset != today:
        conn.execute(
            "UPDATE accounts SET daily_count = 1, last_reset = ? WHERE phone = ?",
            (today, phone)
        )
        conn.commit()
        conn.close()
        return 1

    new_count = count + 1
    conn.execute(
        "UPDATE accounts SET daily_count = ? WHERE phone = ?",
        (new_count, phone)
    )
    conn.commit()
    conn.close()
    return new_count


def get_daily_count(phone):
    """جلب العداد اليومي الحالي"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT daily_count, last_reset FROM accounts WHERE phone = ?",
        (phone,)
    ).fetchone()
    conn.close()
    if not row:
        return 0
    count, last_reset = row
    if last_reset != date.today().isoformat():
        return 0
    return count


def create_transfer(source, target):
    """تسجيل عملية نقل جديدة"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "INSERT INTO transfers (source, target) VALUES (?, ?)",
        (source, target)
    )
    transfer_id = cur.lastrowid
    conn.commit()
    conn.close()
    return transfer_id


def update_transfer(transfer_id, added, failed, skipped):
    """تحديث نتائج النقل"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """UPDATE transfers SET added = ?, failed = ?, skipped = ?,
           finished_at = ? WHERE id = ?""",
        (added, failed, skipped, datetime.now().isoformat(), transfer_id)
    )
    conn.commit()
    conn.close()


def count_accounts():
    """عدد الحسابات المسجلة"""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()
    conn.close()
    return row[0] if row else 0
