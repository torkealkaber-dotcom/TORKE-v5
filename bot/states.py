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

# ==========================================
# حالات الأزرار والعمليات الجديدة
# ==========================================
class ActionStates(StatesGroup):
    # الانضمام والخروج
    waiting_for_join_link = State()
    waiting_for_leave_link = State()
    
    # الرشق (تفاعل، مشاهدات، تصويت)
    waiting_for_spam_link = State()
    waiting_for_spam_count = State()
    
    # تغيير التحقق (2FA)
    waiting_for_old_password = State()
    waiting_for_new_password = State()
    
    # فحص روابط توثيق
    waiting_for_check_link = State()

# ==========================================
# حالات الإعدادات المتقدمة
# ==========================================
class SettingsStates(StatesGroup):
    waiting_for_verification_change = State() 
    waiting_for_account_data = State()        
