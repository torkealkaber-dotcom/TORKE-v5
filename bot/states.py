from aiogram.fsm.state import State, StatesGroup

# ==========================================
# حالات إضافة وتصنيع الحسابات
# ==========================================
class AddAccountStates(StatesGroup):
    waiting_for_phone = State()    # انتظار رقم الهاتف
    waiting_for_code = State()     # انتظار كود التحقق
    waiting_for_2fa = State()      # انتظار كلمة مرور التحقق بخطوتين

# ==========================================
# حالات النقل (سحب وإضافة الأعضاء)
# ==========================================
class TransferStates(StatesGroup):
    waiting_for_source = State()        # انتظار رابط المجموعة المصدر
    waiting_for_target = State()        # انتظار رابط المجموعة الهدف
    waiting_for_total_limit = State()   # إجمالي عدد الأعضاء اللي هنسحبهم من السورس
    waiting_for_account_limit = State() # عدد الأعضاء لكل حساب (اللي إنت طالبه)
    waiting_for_delay = State()         # انتظار عدد ثواني الانتظار

# ==========================================
# حالات الإعدادات المتقدمة
# ==========================================
class SettingsStates(StatesGroup):
    waiting_for_verification_change = State() 
    waiting_for_account_data = State()        
