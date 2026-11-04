from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# القائمة الرئيسية (أخضر)
# ==========================================
def get_main_inline_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="صنع حساب", callback_data="btn_create_account", style="success"),
            InlineKeyboardButton(text="حذف حساب", callback_data="btn_delete_account", style="success")
        ],
        [
            InlineKeyboardButton(text="الحسابات المصنوعه", callback_data="btn_accounts_created", style="success")
        ],
        [
            InlineKeyboardButton(text="الحسابات المحظوره", callback_data="btn_accounts_banned", style="success")
        ],
        [
            InlineKeyboardButton(text="الحسابات المجمده", callback_data="btn_accounts_frozen", style="success"),
            InlineKeyboardButton(text="الحسابات المقيده", callback_data="btn_accounts_restricted", style="success")
        ],
        [
            InlineKeyboardButton(text="نقل مخفي v1", callback_data="btn_transfer_hidden_v1", style="success"),
            InlineKeyboardButton(text="نقل ظاهر v1", callback_data="btn_transfer_visible_v1", style="success")
        ]
    ])

# ==========================================
# القائمة الأولى (الخاصة بالرشق والانضمام)
# ==========================================
def get_inline_menu_1():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تغير التحقق", callback_data="change_verify", style="success")],
        [
            InlineKeyboardButton(text="انضمام", callback_data="join", style="success"),
            InlineKeyboardButton(text="خروج", callback_data="leave", style="success")
        ],
        [
            InlineKeyboardButton(text="رشق تفاعل", callback_data="spam_react", style="success"),
            InlineKeyboardButton(text="رشق مشاهد", callback_data="spam_views", style="success")
        ],
        [
            InlineKeyboardButton(text="رشق تصويت ازرار", callback_data="spam_buttons", style="success"),
            InlineKeyboardButton(text="رشق استفتاء", callback_data="spam_polls", style="success")
        ],
        [InlineKeyboardButton(text="مسابقه", callback_data="contest", style="success")]
    ])

# ==========================================
# القائمة الثانية (الخاصة بالنقل)
# ==========================================
def get_inline_menu_2():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="نقل مخفي v1", callback_data="transfer_hidden_v1", style="success"),
            InlineKeyboardButton(text="نقل ظاهر v1", callback_data="transfer_visible_v1", style="success")
        ],
        [
            InlineKeyboardButton(text="نقل مخفي v2", callback_data="transfer_hidden_v2", style="success"),
            InlineKeyboardButton(text="نقل ظاهر v2", callback_data="transfer_visible_v2", style="success")
        ],
        [InlineKeyboardButton(text="ايقاف النقل", callback_data="stop_transfer", style="success")],
        [InlineKeyboardButton(text="تغيير بيانات الحسابات", callback_data="change_accounts_data", style="success")],
        [InlineKeyboardButton(text="تغير التحقق", callback_data="change_verify", style="success")]
    ])

# ==========================================
# القائمة الثالثة (الإعدادات المتقدمة)
# ==========================================
def get_inline_menu_3():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="فحص روابط توثيق", callback_data="check_verify_links", style="success")],
        [
            InlineKeyboardButton(text="تسجيل دخول", callback_data="login", style="success"),
            InlineKeyboardButton(text="انهاء الجلسات", callback_data="end_sessions", style="success")
        ],
        [InlineKeyboardButton(text="الخروج من كل المحادثات", callback_data="leave_all_chats", style="success")],
        [InlineKeyboardButton(text="تصفيه الحسابات", callback_data="filter_accounts", style="success")],
        [InlineKeyboardButton(text="ايقاف العمليات النشطه", callback_data="stop_active_operations", style="success")]
    ])
