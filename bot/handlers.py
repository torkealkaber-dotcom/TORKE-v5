import asyncio
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from telethon.errors import SessionPasswordNeededError

from config import DEVELOPER_IDS
from bot.keyboards import (
    get_main_inline_keyboard, 
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

logger = logging.getLogger(__name__)
router = Router()

# فلتر للتأكد إن اللي بيتكلم هو المطور
router.message.filter(F.from_user.id.in_(DEVELOPER_IDS))
router.callback_query.filter(F.from_user.id.in_(DEVELOPER_IDS))

temp_clients = {}

# ==========================================
# أوامر البدء
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "أهلاً بك يا مطور في لوحة التحكم 👋\nاستخدم الأزرار الخضراء بالأسفل:",
        reply_markup=get_main_inline_keyboard()
    )
    await message.answer("إعدادات الرشق والانضمام:", reply_markup=get_inline_menu_1())
    await message.answer("إعدادات النقل:", reply_markup=get_inline_menu_2())
    await message.answer("إعدادات متقدمة:", reply_markup=get_inline_menu_3())


# ==========================================
# 1. أزرار القائمة الرئيسية
# ==========================================
@router.callback_query(F.data == "btn_create_account")
async def cb_create_account(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddAccountStates.waiting_for_phone)
    await callback.message.answer("ابعت رقم الهاتف بصيغة دولية (+20...):")
    await callback.answer()

@router.callback_query(F.data.in_({"btn_accounts_created", "btn_accounts_banned", "btn_accounts_frozen", "btn_accounts_restricted"}))
async def cb_show_accounts(callback: CallbackQuery):
    status_map = {
        "btn_accounts_created": ('created', "الحسابات المصنوعة"),
        "btn_accounts_banned": ('banned', "الحسابات المحظورة"),
        "btn_accounts_frozen": ('frozen', "الحسابات المجمدة"),
        "btn_accounts_restricted": ('restricted', "الحسابات المقيدة")
    }
    status_filter, title = status_map[callback.data]
    accounts = await get_accounts(status_filter)
    
    if not accounts:
        await callback.message.answer(f"لا توجد حسابات في قسم {title}.")
    else:
        text = f"📊 {title} ({len(accounts)}):\n\n"
        for i, acc in enumerate(accounts, 1):
            text += f"{i}. {acc['phone']}\n"
        await callback.message.answer(text)
    await callback.answer()

@router.callback_query(F.data == "btn_delete_account")
async def cb_delete_account(callback: CallbackQuery):
    await callback.message.answer("ميزة حذف الحساب قيد التطوير.")
    await callback.answer()


# ==========================================
# 2. مسار النقل (Transfer Flow)
# ==========================================
@router.callback_query(F.data.in_({"btn_transfer_hidden_v1", "btn_transfer_visible_v1"}))
async def cb_transfer_start(callback: CallbackQuery, state: FSMContext):
    mode = "hidden" if "hidden" in callback.data else "visible"
    await state.update_data(mode=mode)
    await state.set_state(TransferStates.waiting_for_source)
    await callback.message.answer("ابعت رابط/معرف المجموعة المصدر (اللي هنسحب منها):")
    await callback.answer()

@router.message(TransferStates.waiting_for_source)
async def process_transfer_source(message: Message, state: FSMContext):
    await state.update_data(source=message.text.strip())
    await state.set_state(TransferStates.waiting_for_target)
    await message.answer("ابعت رابط/معرف المجموعة الهدف (اللي هنضيف فيها):")

@router.message(TransferStates.waiting_for_target)
async def process_transfer_target(message: Message, state: FSMContext):
    await state.update_data(target=message.text.strip())
    await state.set_state(TransferStates.waiting_for_total_limit)
    await message.answer("إجمالي عدد الأعضاء المطلوب نقلهم من المصدر (أو 0 لنقل الكل):")

@router.message(TransferStates.waiting_for_total_limit)
async def process_transfer_total_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ ابعت رقم صحيح (أو 0 للكل):")
    await state.update_data(total_limit=int(message.text))
    await state.set_state(TransferStates.waiting_for_account_limit)
    await message.answer("👤 الحساب الواحد يضيف كام عضو قبل ما ننتقل للحساب اللي بعده؟\n(مثلاً: 50، أو 100)")

@router.message(TransferStates.waiting_for_account_limit)
async def process_transfer_account_limit(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) == 0:
        return await message.answer("❌ ابعت رقم صحيح أكبر من صفر:")
    await state.update_data(account_limit=int(message.text))
    await state.set_state(TransferStates.waiting_for_delay)
    await message.answer("ارسل عدد ثواني الانتظار بين كل عضو (أو 0 للانتظار العشوائي):")

@router.message(TransferStates.waiting_for_delay)
async def process_transfer_delay(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ ابعت رقم صحيح:")
    
    delay = int(message.text)
    data = await state.get_data()
    await state.clear()

    accounts = await get_accounts('created')
    if not accounts:
        return await message.answer("❌ لا يوجد حسابات صالحة. أضف حساب أولاً.", reply_markup=get_main_inline_keyboard())
    
    session_paths = [acc['session_path'] for acc in accounts]
    
    source = data.get("source")
    target = data.get("target")
    total_limit = data.get("total_limit")
    account_limit = data.get("account_limit")
    mode = data.get("mode", "hidden")

    transfer_id = await create_transfer(source, target, mode, total_limit, account_limit, delay)
    msg = await message.answer(f"⏳ جاري بدء النقل باستخدام {len(session_paths)} حساب...\n(سيتم إعلامك عند الانتهاء)")
    
    async def run_transfer():
        try:
            result = await actions.transfer_members(
                session_paths, source, target, total_limit, account_limit, delay, mode
            )
            if "error" in result:
                await msg.edit_text(f"❌ فشل النقل: {result['error']}")
                await update_transfer_status(transfer_id, "stopped")
            else:
                await msg.edit_text(
                    f"✅ انتهت العملية!\n\n"
                    f"تم إضافة: {result['added']} عضو\n"
                    f"فشل: {result['failed']}\n"
                    f"تم تخطي: {result['skipped']}\n"
                    f"إجمالي المتاح: {result['total']}",
                    reply_markup=get_main_inline_keyboard()
                )
                await update_transfer_status(transfer_id, "finished")
        except Exception as e:
            await msg.edit_text(f"❌ خطأ: {e}")
            await update_transfer_status(transfer_id, "stopped")

    asyncio.create_task(run_transfer())


# ==========================================
# 3. تسجيل الحسابات
# ==========================================
@router.message(AddAccountStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith("+"):
        return await message.answer("❌ الرقم لازم يبدأ بـ +:")
    
    try:
        client, session_path = await auth.create_client(phone)
        if await auth.is_authorized(client):
            await auth.safe_disconnect(client)
            await add_account(phone, session_path)
            await state.clear()
            return await message.answer(f"✅ الحساب {phone} مسجل ومضاف.", reply_markup=get_main_inline_keyboard())

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
    phone, session_path = data.get("phone"), data.get("session_path")
    client = temp_clients.get(message.from_user.id)

    if not client:
        await state.clear()
        return await message.answer("انتهت الجلسة.", reply_markup=get_main_inline_keyboard())

    try:
        await auth.sign_in_code(client, phone, code)
        await auth.safe_disconnect(client)
        await add_account(phone, session_path)
        temp_clients.pop(message.from_user.id, None)
        await state.clear()
        await message.answer("✅ تم تسجيل الدخول بنجاح.", reply_markup=get_main_inline_keyboard())
    except SessionPasswordNeededError:
        await state.set_state(AddAccountStates.waiting_for_2fa)
        await message.answer("🔐 الحساب عليه تحقق بخطوتين. ابعته كلمة المرور:")
    except Exception as e:
        await message.answer(f"❌ خطأ: {e}")

@router.message(AddAccountStates.waiting_for_2fa)
async def process_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    phone, session_path = data.get("phone"), data.get("session_path")
    client = temp_clients.get(message.from_user.id)

    try:
        await auth.sign_in_password(client, password)
        await auth.safe_disconnect(client)
        await add_account(phone, session_path)
        temp_clients.pop(message.from_user.id, None)
        await state.clear()
        await message.answer("✅ تم تسجيل الدخول (2FA).", reply_markup=get_main_inline_keyboard())
    except Exception as e:
        await message.answer(f"❌ كلمة مرور خاطئة: {e}")


# ==========================================
# 4. إيقاف النقل والأزرار العامة
# ==========================================
@router.callback_query(F.data == "stop_transfer")
async def cb_stop_transfer(callback: CallbackQuery):
    active = await get_active_transfer()
    if active:
        await update_transfer_status(active['id'], "stopped")
        await callback.message.answer("✅ تم إرسال أمر إيقاف النقل.")
        await callback.answer("تم الإيقاف")
    else:
        await callback.answer("لا توجد عملية نقل نشطة.", show_alert=True)

@router.callback_query()
async def cb_generic_handler(callback: CallbackQuery):
    await callback.message.answer(f"⚙️ ميزة [{callback.data}] جاهزة للربط.")
    await callback.answer()
