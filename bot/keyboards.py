from telethon import Button


def main_menu():
    """القائمة الرئيسية"""
    return [
        [Button.inline("➕ إضافة حساب", b"add_account")],
        [Button.inline("📤 نقل أعضاء", b"transfer_members")],
        [Button.inline("📊 الحسابات", b"list_accounts")],
    ]


def back_menu():
    """زر الرجوع للقائمة الرئيسية"""
    return [[Button.inline("🔙 رجوع", b"back_main")]]


def confirm_menu(action):
    """أزرار تأكيد"""
    return [
        [Button.inline("✅ تأكيد", f"confirm_{action}".encode())],
        [Button.inline("❌ إلغاء", b"back_main")],
    ]
