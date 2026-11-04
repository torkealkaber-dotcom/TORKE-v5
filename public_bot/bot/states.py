from aiogram.fsm.state import State, StatesGroup

# ==========================================
# حالات تسجيل الحساب في البوت الفرعي
# ==========================================
class AddAccountStates(StatesGroup):
    waiting_for_phone = State()    # انتظار رقم الهاتف
    waiting_for_code = State()     # انتظار كود التحقق
    waiting_for_2fa = State()      # انتظار كلمة مرور التحقق بخطوتين
