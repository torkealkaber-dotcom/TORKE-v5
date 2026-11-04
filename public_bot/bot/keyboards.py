from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

# ==========================================
# القائمة الرئيسية للبوت الفرعي (مطمنة واحترافية)
# ==========================================
def get_public_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ إضافة حساب جديد", callback_data="pub_add_account", style="success")
        ],
        [
            InlineKeyboardButton(text="📊 حساباتي المسجلة", callback_data="pub_my_accounts", style="primary")
        ],
        [
            InlineKeyboardButton(text="ℹ️ عن البوت", callback_data="pub_about", style="primary")
        ]
    ])

# ==========================================
# زرار إلغاء العملية
# ==========================================
def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ إلغاء", callback_data="pub_cancel", style="danger")]
    ])
