from aiogram.fsm.state import State, StatesGroup

# ==========================================
# حالات إضافة وتصنيع الحسابات
# ==========================================
class AddAccountStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()

# ==========================================
# حالات النقل (سحب وإضافة الأعضاء)
# ==========================================
class TransferStates(StatesGroup):
    waiting_for_source = State()
    waiting_for_target = State()
    waiting_for_total_limit = State()
    waiting_for_account_limit = State()
    waiting_for_delay = State()
    waiting_for_filter_online = State()
    waiting_for_filter_premium = State()

# ==========================================
# حالات الأزرار والعمليات الجديدة
# ==========================================
class ActionStates(StatesGroup):
    waiting_for_join_link = State()
    waiting_for_leave_link = State()
    waiting_for_spam_link = State()
    waiting_for_spam_count = State()
    waiting_for_old_password = State()
    waiting_for_new_password = State()
    waiting_for_check_link = State()

# ==========================================
# حالات الإعدادات المتقدمة
# ==========================================
class SettingsStates(StatesGroup):
    waiting_for_verification_change = State() 
    waiting_for_account_data = State()        
