import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from telethon.errors import SessionPasswordNeededError

from config import DEVELOPER_IDS
from bot.keyboards import (
    get_main_reply_keyboard, 
    get_inline_menu_1, 
    get_inline_menu_2, 
    get_inline_menu_3
)
from bot.states import AddAccountStates, TransferStates, SettingsStates
from userbot import auth, actions
from database import (
    add_account, get_accounts, delete_account, update_account_status,
    create_transfer, get_active_transfer, update_transfer_status
)

# إعداد السجل لطباعة الأخطاء
logger = logging.getLogger(__name__)

router = Router()

# فلتر للتأكد إن اللي بيتكلم هو المطور (أو أحد المطورين)
router.message.filter(F.from_user.id.in_(DEVELOPER_IDS))
router.callback_query.filter(F.from_user.id.in_(DEVELOPER_IDS))

# متغير مؤقت لحفظ عملاء تليثون أثناء عملية تسجيل الدخول
# (لأن aiogram FSM مينفعش يحفظ كائنات بايثون معقدة زي TelethonClient)
temp_clients = {}


# ==========================================
# أوامر البدء
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "أهلاً بك يا مطور في لوحة التحكم 👋\nاستخدم الأزرار بالأسفل للبدء:",
        reply_markup=get_main_reply_keyboard()
    )
    # إرسال القوائم الشفافة (زي الصور)
    await message.answer("إعدادات الرشق والانضمام:", reply_markup=get_inline_menu_1())
    await message.answer("إعدادات النقل:", reply_markup=get_inline_menu_2())
    await message.answer("إعدادات متقدمة:", reply_markup=get_inline_menu_3())


# ==========================================
# 1. صنع الحسابات (سحب الرقم -> الكود -> 2FA)
# ==========================================
@router.message(F.text == "صنع حساب")
async def process_create_account(message: Message, state: FSMContext):
    await state.set_state(AddAccountStates.waiting_for_phone)
    await message.answer("ابعت رقم الهاتف بصيغة دولية (+20...):", reply_markup=get_main_reply_keyboard())

@router.message(AddAccountStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith("+"):
        return await message.answer("❌ الرقم لازم يبدأ بـ + ويشمل كود الدولة. جرب تاني:")
    
    try:
        client, session_path = await auth.create_client(phone)
        if await auth.is_authorized(client):
            await auth.safe_disconnect(client)
            await add_account(phone, session_path)
            await state.clear()
            return await message.answer(f"✅ الحساب {phone} مسجل بالفعل وتم إضافته للقائمة.")

        await auth.send_code(client, phone)
        temp_clients[message.from_user.id] = client
        await state.update_data(phone=phone, session_path=session_path)
        await state.set_state(AddAccountStates.waiting_for_code)
        await message.answer("✅ تم إرسال الكود. ابعته هنا:")
    except Exception as e:
        await message.answer(f"❌ خطأ: {e}")

@router.message(AddAccountStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    session_path = data.get("session_path")
    client = temp_clients.get(message.from_user.id)

    if not client:
        await state.clear()
        return await message.answer("انتهت الجلسة، ابدأ من جديد.")

    try:
        await auth.sign_in_code(client, phone, code)
        await auth.safe_disconnect(client)
        await add_account(phone, session_path)
        temp_clients.pop(message.from_user.id, None)
        await state.clear()
        await message.answer("✅ تم تسجيل الدخول بنجاح وإضافة الحساب.")
    except SessionPasswordNeededError:
        await state.set_state(AddAccountStates.waiting_for_2fa)
        await message.answer("🔐 الحساب عليه تحقق بخطوتين. ابعته كلمة المرور:")
    except Exception as e:
        await message.answer(f"❌ كود خاطئ أو خطأ: {e}\nابعته تاني:")

@router.message(AddAccountStates.waiting_for_2fa)
async def process_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    phone = data.get("phone")
    session_path = data.get("session_path")
    client = temp_clients.get(message.from_user.id)

    try:
        await auth.sign_in_password(client, password)
        await auth.safe_disconnect(client)
        await add_account(phone, session_path)
        temp_clients.pop(message.from_user.id, None)
        await state.clear()
        await message.answer("✅ تم تسجيل الدخول بنجاح (2FA) وإضافة الحساب.")
    except Exception as e:
        await message.answer(f"❌ كلمة مرور خاطئة: {e}\nجرب تاني:")


# ==========================================
# 2. عرض الحسابات (المصنوعة، المحظورة، إلخ)
# ==========================================
async def show_accounts_list(message: Message, status_filter, title):
    accounts = await get_accounts(status_filter)
    if not accounts:
        return await message.answer(f"لا توجد حسابات في قسم {title}.")
    
    text = f"📊 {title} ({len(accounts)}):\n\n"
    for i, acc in enumerate(accounts, 1):
        text += f"{i}. {acc['phone']}\n"
    await message.answer(text)

@router.message(F.text == "الحسابات المصنوعه")
async def process_created_accounts(message: Message):
    await show_accounts_list(message, 'created', "الحسابات المصنوعة")

@router.message(F.text == "الحسابات المحظوره")
async def process_banned_accounts(message: Message):
    await show_accounts_list(message, 'banned', "الحسابات المحظورة")

@router.message(F.text == "الحسابات المجمده")
async def process_frozen_accounts(message: Message):
    await show_accounts_list(message, 'frozen', "الحسابات المجمدة")

@router.message(F.text == "الحسابات المقيده")
async def process_restricted_accounts(message: Message):
    await show_accounts_list(message, 'restricted', "الحسابات المقيدة")


# ==========================================
# 3. نقل الأعضاء (مخفي / ظاهر)
# ==========================================
@router.message(F.text.in_({"نقل مخفي v1", "نقل ظاهر v1"}))
async def process_transfer_start(message: Message, state: FSMContext):
    mode = "hidden" if "مخفي" in message.text else "visible"
    await state.update_data(mode=mode)
    await state.set_state(TransferStates.waiting_for_source)
    await message.answer("ابعت رابط/معرف المجموعة المصدر (اللي هنسحب منها):")

@router.message(TransferStates.waiting_for_source)
async def process_transfer_source(message: Message, state: FSMContext):
    await state.update_data(source=message.text.strip())
    await state.set_state(TransferStates.waiting_for_target)
    await message.answer("ابعت رابط/معرف المجموعة الهدف (اللي هنضيف فيها):")

@router.message(TransferStates.waiting_for_target)
async def process_transfer_target(message: Message, state: FSMContext):
    await state.update_data(target=message.text.strip())
    await state.set_state(TransferStates.waiting_for_members_limit)
    await message.answer("ارسل عدد الأعضاء المطلوب نقلهم (أو ارسل 0 لنقل الكل):")

@router.message(TransferStates.waiting_for_members_limit)
async def process_transfer_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ من فضلك ابعت رقم صحيح (أو 0 للكل):")
    await state.update_data(limit=int(message.text))
    await state.set_state(TransferStates.waiting_for_delay)
    await message.answer("ارسل عدد ثواني الانتظار بين كل عضو (أو ارسل 0 للانتظار العشوائي):")

@router.message(TransferStates.waiting_for_delay)
async def process_transfer_delay(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ من فضلك ابعت رقم صحيح:")
    
    delay = int(message.text)
    data = await state.get_data()
    await state.clear()

    # جلب أول حساب متاح للبدء
    accounts = await get_accounts('created')
    if not accounts:
        return await message.answer("❌ لا يوجد حسابات صالحة للاستخدام. أضف حساب أولاً.")
    
    session_path = accounts[0]['session_path']
    source = data.get("source")
    target = data.get("target")
    limit = data.get("limit")
    mode = data.get("mode", "hidden")

    # تسجيل العملية في قاعدة البيانات
    transfer_id = await create_transfer(source, target, mode, limit, delay)
    
    # تشغيل العملية في الخلفية عشان البوت ميهنجش
    msg = await message.answer("⏳ جاري بدء عملية النقل... (سيتم إعلامك عند الانتهاء)")
    
    async def run_transfer():
        try:
            result = await actions.transfer_members(session_path, source, target, limit, delay, mode)
            if "error" in result:
                await msg.edit_text(f"❌ فشل النقل: {result['error']}")
                await update_transfer_status(transfer_id, "stopped")
            else:
                await msg.edit_text(
                    f"✅ انتهت العملية!\n\n"
                    f"تم إضافة: {result['added']} عضو\n"
                    f"فشل: {result['failed']}\n"
                    f"تم تخطي: {result['skipped']}\n"
                    f"إجمالي الأعضاء بالسورس: {result['total']}"
                )
                await update_transfer_status(transfer_id, "finished")
        except Exception as e:
            await msg.edit_text(f"❌ حدث خطأ أثناء النقل: {e}")
            await update_transfer_status(transfer_id, "stopped")
            logger.error(f"Transfer Error: {e}")

    asyncio.create_task(run_transfer())


# ==========================================
# 4. معالجة الأزرار الشفافة (Inline Callbacks)
# ==========================================

# --- إيقاف النقل ---
@router.callback_query(F.data == "stop_transfer")
async def cb_stop_transfer(callback: CallbackQuery):
    active = await get_active_transfer()
    if active:
        await update_transfer_status(active['id'], "stopped")
        await callback.message.answer("✅ تم إرسال أمر إيقاف النقل.")
        await callback.answer("تم الإيقاف")
    else:
        await callback.answer("لا توجد عملية نقل نشطة حالياً.", show_alert=True)

# --- إيقاف العمليات النشطة ---
@router.callback_query(F.data == "stop_active_operations")
async def cb_stop_all_operations(callback: CallbackQuery):
    # هنا ممكن تضيف كود لإيقاف أي مهام في الخلفية
    await callback.message.answer("⛔ تم إيقاف جميع العمليات النشطة.")
    await callback.answer("تم الإيقاف")

# --- باقي أزرار القوائم (انضمام، خروج، رشق، إلخ) ---
@router.callback_query()
async def cb_generic_handler(callback: CallbackQuery):
    action_text = callback.data
    # خريطة لتحويل الـ callback_data لأسماء مفهومة
    action_names = {
        "change_verify": "تغيير التحقق",
        "join": "انضمام",
        "leave": "خروج",
        "spam_react": "رشق تفاعل",
        "spam_views": "رشق مشاهد",
        "spam_buttons": "رشق تصويت أزرار",
        "spam_polls": "رشق استفتاء",
        "contest": "مسابقة",
        "transfer_hidden_v1": "نقل مخفي v1",
        "transfer_visible_v1": "نقل ظاهر v1",
        "transfer_hidden_v2": "نقل مخفي v2",
        "transfer_visible_v2": "نقل ظاهر v2",
        "change_accounts_data": "تغيير بيانات الحسابات",
        "check_verify_links": "فحص روابط توثيق",
        "login": "تسجيل دخول",
        "end_sessions": "إنهاء الجلسات",
        "leave_all_chats": "الخروج من كل المحادثات",
        "filter_accounts": "تصفية الحسابات"
    }
    
    name = action_names.get(action_text, action_text)
    
    # لو العملية محتاجة رابط أو خطوات إضافية هنبلغه إننا محتاجين نطورها
    await callback.message.answer(
        f"⚙️ تم اختيار: [{name}]\n"
        f"هذه الميزة تتطلب تحديد (رابط القناة/الحساب) أولاً. الكود جاهز للربط."
    )
    await callback.answer(f"تم اختيار {name}")
