from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# 1. الأزرار اللي تحت الشات (Reply Keyboard)
# ==========================================
def get_main_reply_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="صنع حساب"), KeyboardButton(text="حذف حساب")],
            [KeyboardButton(text="الحسابات المصنوعه")],
            [KeyboardButton(text="الحسابات المحظوره")],
            [KeyboardButton(text="الحسابات المجمده"), KeyboardButton(text="الحسابات المقيده")],
            [KeyboardButton(text="نقل مخفي v1"), KeyboardButton(text="نقل ظاهر v1")]
        ],
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة..."
    )
    return keyboard

# ==========================================
# 2. الأزرار الشفافة (Inline Keyboards) - كلها زرقاء
# ==========================================

# القائمة الأولى (الخاصة بالرشق والانضمام - الصورة الثانية)
def get_inline_menu_1():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تغير التحقق", callback_data="change_verify", style="primary")],
        [
            InlineKeyboardButton(text="انضمام", callback_data="join", style="primary"),
            InlineKeyboardButton(text="خروج", callback_data="leave", style="primary")
        ],
        [
            InlineKeyboardButton(text="رشق تفاعل", callback_data="spam_react", style="primary"),
            InlineKeyboardButton(text="رشق مشاهد", callback_data="spam_views", style="primary")
        ],
        [
            InlineKeyboardButton(text="رشق تصويت ازرار", callback_data="spam_buttons", style="primary"),
            InlineKeyboardButton(text="رشق استفتاء", callback_data="spam_polls", style="primary")
        ],
        [InlineKeyboardButton(text="مسابقه", callback_data="contest", style="primary")]
    ])

# القائمة الثانية (الخاصة بالنقل - الصورة الثالثة)
def get_inline_menu_2():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="نقل مخفي v1", callback_data="transfer_hidden_v1", style="primary"),
            InlineKeyboardButton(text="نقل ظاهر v1", callback_data="transfer_visible_v1", style="primary")
        ],
        [
            InlineKeyboardButton(text="نقل مخفي v2", callback_data="transfer_hidden_v2", style="primary"),
            InlineKeyboardButton(text="نقل ظاهر v2", callback_data="transfer_visible_v2", style="primary")
        ],
        [InlineKeyboardButton(text="ايقاف النقل", callback_data="stop_transfer", style="primary")],
        [InlineKeyboardButton(text="تغيير بيانات الحسابات", callback_data="change_accounts_data", style="primary")],
        [InlineKeyboardButton(text="تغير التحقق", callback_data="change_verify", style="primary")]
    ])

# القائمة الثالثة (الإعدادات المتقدمة - الصورة الرابعة)
def get_inline_menu_3():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="فحص روابط توثيق", callback_data="check_verify_links", style="primary")],
        [
            InlineKeyboardButton(text="تسجيل دخول", callback_data="login", style="primary"),
            InlineKeyboardButton(text="انهاء الجلسات", callback_data="end_sessions", style="primary")
        ],
        [InlineKeyboardButton(text="الخروج من كل المحادثات", callback_data="leave_all_chats", style="primary")],
        [InlineKeyboardButton(text="تصفيه الحسابات", callback_data="filter_accounts", style="primary")],
        [InlineKeyboardButton(text="ايقاف العمليات النشطه", callback_data="stop_active_operations", style="primary")]
    ])

# أزرار تأكيد الإضافة أو الحذف
def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="إلغاء ❌", callback_data="cancel_action", style="primary")]
    ])
