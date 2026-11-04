import asyncio
import logging
import sys
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from telethon.errors import SessionPasswordNeededError

# عشان يقرأ من الفولدر الأساسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import DEVELOPER_IDS
from main_bot.bot.keyboards import (
    get_main_inline_keyboard, 
    get_inline_menu_1, 
    get_inline_menu_2, 
    get_inline_menu_3
)
from main_bot.bot.states import AddAccountStates, TransferStates, ActionStates
from main_bot.userbot import auth, actions
from main_bot.database import (
    add_account, get_accounts, delete_account,
    create_transfer, get_active_transfer, update_transfer_status
)

logger = logging.getLogger(__name__)
router = Router()

router.message.filter(F.from_user.id.in_(DEVELOPER_IDS))
router.callback_query.filter(F.from_user.id.in_(DEVELOPER_IDS))

temp_clients = {}
stop_flag = False

async def get_all_active_sessions():
    accounts = await get_accounts('created')
    return [acc['session_path'] for acc in accounts]

# ==========================================
# أوامر البدء
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("جاري تحديث القائمة...", reply_markup=ReplyKeyboardRemove())
    
    await message.answer(
        "أهلاً بك يا مطور في لوحة التحكم 👋\nاستخدم الأزرار الخضراء بالأسفل:",
        reply_markup=get_main_inline_keyboard()
    )
    await message.answer("إعدادات الرشق والانضمام:", reply_markup=get_inline_menu_1())
    await message.answer("إعدادات النقل:", reply_markup=get_inline_menu_2())
    await message.answer("إعدادات متقدمة:", reply_markup=get_inline_menu_3())

# ==========================================
# 1. أزرار القوائم الأساسية
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
    await callback.message.answer("لحذف حساب، يرجى إرسال الأمر التالي:\n`/delete_account +123456789`")
    await callback.answer()

@router.message(F.text.startswith("/delete_account"))
async def delete_acc_cmd(message: Message):
    try:
        phone = message.text.split(" ")[1]
        await delete_account(phone)
        await message.answer(f"✅ تم حذف الحساب {phone}.")
    except IndexError:
        await message.answer("❌ الصيغة غلط. اكتب: `/delete_account +123456789`")

# ==========================================
# 2. مسار النقل (Transfer Flow)
# ==========================================
@router.callback_query(F.data.in_({
    "btn_transfer_hidden_v1", "btn_transfer_visible_v1", 
    "transfer_hidden_v1", "transfer_visible_v1",
    "transfer_hidden_v2", "transfer_visible_v2"
}))
async def cb_transfer_start(callback: CallbackQuery, state: FSMContext):
    mode = "hidden" if "hidden" in callback.data else "visible"
    await state.update_data(mode=mode)
    await state.set_state(TransferStates.waiting_for_source)
    await callback.message.answer(f"تم اختيار النقل ({mode}).\nابعت رابط/معرف المجموعة المصدر:")
    await callback.answer()

@router.message(TransferStates.waiting_for_source)
async def process_transfer_source(message: Message, state: FSMContext):
    await state.update_data(source=message.text.strip())
    await state.set_state(TransferStates.waiting_for_target)
    await message.answer("ابعت رابط/معرف المجموعة الهدف:")

@router.message(TransferStates.waiting_for_target)
async def process_transfer_target(message: Message, state: FSMContext):
    await state.update_data(target=message.text.strip())
    await state.set_state(TransferStates.waiting_for_total_limit)
    await message.answer("إجمالي عدد الأعضاء المطلوب نقلهم (أو 0 للكل):")

@router.message(TransferStates.waiting_for_total_limit)
async def process_transfer_total_limit(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ ابعت رقم صحيح:")
    await state.update_data(total_limit=int(message.text))
    await state.set_state(TransferStates.waiting_for_account_limit)
    await message.answer("👤 الحساب الواحد يضيف كام عضو قبل التبديل؟")

@router.message(TransferStates.waiting_for_account_limit)
async def process_transfer_account_limit(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) == 0:
        return await message.answer("❌ ابعت رقم صحيح أكبر من صفر:")
    await state.update_data(account_limit=int(message.text))
    await state.set_state(TransferStates.waiting_for_delay)
    await message.answer("ارسل عدد ثواني الانتظار بين كل عضو (أو 0 للعشوائي):")

@router.message(TransferStates.waiting_for_delay)
async def process_transfer_delay(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ ابعت رقم صحيح:")
    
    await state.update_data(delay=int(message.text))
    await state.set_state(TransferStates.waiting_for_filter_online)
    await message.answer("🟢 هل تريد إضافة الأعضاء المتصلين (أونلاين) فقط؟\n(اكتب: اه أو لا)")

@router.message(TransferStates.waiting_for_filter_online)
async def process_filter_online(message: Message, state: FSMContext):
    ans = message.text.strip()
    filter_online = True if ans in ["اه", "نعم", "yes"] else False
    await state.update_data(filter_online=filter_online)
    
    await state.set_state(TransferStates.waiting_for_filter_premium)
    await message.answer("⭐ هل تريد إضافة الأعضاء المميزين (بريميوم/موثقين) فقط؟\n(اكتب: اه أو لا)")

@router.message(TransferStates.waiting_for_filter_premium)
async def process_filter_premium(message: Message, state: FSMContext):
    ans = message.text.strip()
    filter_premium = True if ans in ["اه", "نعم", "yes"] else False
    
    data = await state.get_data()
    await state.clear()

    session_paths = await get_all_active_sessions()
    if not session_paths:
        return await message.answer("❌ لا يوجد حسابات صالحة.", reply_markup=get_main_inline_keyboard())
    
    source = data.get("source")
    target = data.get("target")
    total_limit = data.get("total_limit")
    account_limit = data.get("account_limit")
    delay = data.get("delay")
    mode = data.get("mode", "hidden")
    filter_online = data.get("filter_online", False)

    transfer_id = await create_transfer(source, target, mode, total_limit, account_limit, delay)
    msg = await message.answer("⏳ جاري سحب الأعضاء وفلترتهم وبدء الإضافة...")
    
    global stop_flag
    stop_flag = False

    async def run_transfer():
        try:
            result = await actions.transfer_members(
                session_paths, source, target, total_limit, account_limit, delay, mode,
                filter_online=filter_online, filter_premium=filter_premium
            )
            if "error" in result:
                await msg.edit_text(f"❌ فشل: {result['error']}")
            else:
                await msg.edit_text(
                    f"✅ انتهى النقل!\n"
                    f"تم إضافة: {result['added']}\n"
                    f"فشل: {result['failed']}\n"
                    f"تخطي: {result['skipped']}\n"
                    f"إجمالي المتاح بعد الفلترة: {result['total']}"
                )
                await update_transfer_status(transfer_id, "finished")
        except Exception as e:
            await msg.edit_text(f"❌ حدث خطأ: {e}")

    asyncio.create_task(run_transfer())

# ==========================================
# 3. الانضمام والخروج
# ==========================================
@router.callback_query(F.data == "join")
async def cb_join(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ActionStates.waiting_for_join_link)
    await callback.message.answer("🔗 ابعت رابط القناة/المجموعة للانضمام:")
    await callback.answer()

@router.message(ActionStates.waiting_for_join_link)
async def process_join(message: Message, state: FSMContext):
    link = message.text.strip()
    await state.clear()
    sessions = await get_all_active_sessions()
    if not sessions:
        return await message.answer("❌ لا يوجد حسابات.")
    
    msg = await message.answer("⏳ جاري الانضمام بكل الحسابات...")
    success = 0
    for sess in sessions:
        ok, _ = await actions.join_channel(sess, link)
        if ok: success += 1
        
    await msg.edit_text(f"✅ تم انضمام {success} حساب من أصل {len(sessions)}.")

@router.callback_query(F.data == "leave")
async def cb_leave(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ActionStates.waiting_for_leave_link)
    await callback.message.answer("🔗 ابعت رابط القناة/المجموعة للخروج:")
    await callback.answer()

@router.message(ActionStates.waiting_for_leave_link)
async def process_leave(message: Message, state: FSMContext):
    link = message.text.strip()
    await state.clear()
    sessions = await get_all_active_sessions()
    if not sessions:
        return await message.answer("❌ لا يوجد حسابات.")
    
    msg = await message.answer("⏳ جاري الخروج بكل الحسابات...")
    success = 0
    for sess in sessions:
        ok, _ = await actions.leave_channel(sess, link)
        if ok: success += 1
        
    await msg.edit_text(f"✅ تم خروج {success} حساب من أصل {len(sessions)}.")

# ==========================================
# 4. الرشق
# ==========================================
@router.callback_query(F.data.in_({"spam_views", "spam_react", "spam_polls", "spam_buttons"}))
async def cb_spam_action(callback: CallbackQuery, state: FSMContext):
    action_type = callback.data
    await state.update_data(spam_type=action_type)
    await state.set_state(ActionStates.waiting_for_spam_link)
    await callback.message.answer("🔗 ابعت رابط البوست (مثال: https://t.me/channel/123):")
    await callback.answer()

@router.message(ActionStates.waiting_for_spam_link)
async def process_spam_link(message: Message, state: FSMContext):
    await state.update_data(spam_link=message.text.strip())
    await state.set_state(ActionStates.waiting_for_spam_count)
    await message.answer("🔢 ابعت عدد المرات (مثلاً 100):")

@router.message(ActionStates.waiting_for_spam_count)
async def process_spam_count(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("❌ ابعت رقم صحيح:")
    
    count = int(message.text)
    data = await state.get_data()
    spam_type = data.get("spam_type")
    link = data.get("spam_link")
    await state.clear()

    sessions = await get_all_active_sessions()
    if not sessions:
        return await message.answer("❌ لا يوجد حسابات.")

    msg = await message.answer(f"⏳ جاري تنفيذ الرشق...")
    sess = sessions[0]

    if spam_type == "spam_views":
        ok, _ = await actions.spam_views(sess, link, count)
    elif spam_type == "spam_react":
        ok, _ = await actions.spam_reactions(sess, link, "👍", count)
    elif spam_type in ["spam_polls", "spam_buttons"]:
        ok, _ = await actions.spam_poll_vote(sess, link, 0, count)
        
    if ok:
        await msg.edit_text(f"✅ تم تنفيذ {count} عملية رشق بنجاح.")
    else:
        await msg.edit_text("❌ حدث خطأ أثناء الرشق.")

# ==========================================
# 5. الإعدادات المتقدمة
# ==========================================
@router.callback_query(F.data == "change_verify")
async def cb_change_verify(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ActionStates.waiting_for_old_password)
    await callback.message.answer("🔐 ابعت كلمة المرور القديمة (أو اكتب `0` لو مفيش):")
    await callback.answer()

@router.message(ActionStates.waiting_for_old_password)
async def process_old_pass(message: Message, state: FSMContext):
    old_pass = message.text.strip()
    await state.update_data(old_pass=old_pass if old_pass != "0" else "")
    await state.set_state(ActionStates.waiting_for_new_password)
    await message.answer("🆕 ابعت كلمة المرور الجديدة:")

@router.message(ActionStates.waiting_for_new_password)
async def process_new_pass(message: Message, state: FSMContext):
    new_pass = message.text.strip()
    data = await state.get_data()
    old_pass = data.get("old_pass")
    await state.clear()

    sessions = await get_all_active_sessions()
    if not sessions:
        return await message.answer("❌ لا يوجد حسابات.")

    msg = await message.answer("⏳ جاري تغيير كلمة المرور...")
    success = 0
    for sess in sessions:
        ok, _ = await actions.change_2fa_password(sess, old_pass, new_pass)
        if ok: success += 1
        
    await msg.edit_text(f"✅ تم تغيير كلمة المرور لـ {success} حساب.")

@router.callback_query(F.data == "end_sessions")
async def cb_end_sessions(callback: CallbackQuery):
    sessions = await get_all_active_sessions()
    if not sessions:
        return await callback.answer("لا يوجد حسابات.", show_alert=True)
    
    msg = await callback.message.answer("⏳ جاري إنهاء الجلسات الأخرى...")
    success = 0
    for sess in sessions:
        ok, _ = await actions.end_all_sessions(sess)
        if ok: success += 1
    await msg.edit_text(f"✅ تم إنهاء الجلسات لـ {success} حساب.")

@router.callback_query(F.data == "leave_all_chats")
async def cb_leave_all(callback: CallbackQuery):
    sessions = await get_all_active_sessions()
    if not sessions:
        return await callback.answer("لا يوجد حسابات.", show_alert=True)
    
    msg = await callback.message.answer("⏳ جاري الخروج من كل المحادثات... (هياخد وقت)")
    success = 0
    for sess in sessions:
        ok, _ = await actions.leave_all_chats(sess)
        if ok: success += 1
    await msg.edit_text(f"✅ تم الخروج من المحادثات لـ {success} حساب.")

@router.callback_query(F.data == "check_verify_links")
async def cb_check_verify(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ActionStates.waiting_for_check_link)
    await callback.message.answer("🔗 ابعت يوزرنيم الحساب (مثال: @username):")
    await callback.answer()

@router.message(ActionStates.waiting_for_check_link)
async def process_check_verify(message: Message, state: FSMContext):
    username = message.text.strip()
    await state.clear()
    sessions = await get_all_active_sessions()
    if not sessions:
        return await message.answer("❌ لا يوجد حسابات.")
        
    msg = await message.answer("⏳ جاري الفحص...")
    ok, result_text = await actions.check_verify_link(sessions[0], username)
    if ok:
        await msg.edit_text(result_text)
    else:
        await msg.edit_text(f"❌ خطأ: {result_text}")

# ==========================================
# 6. إيقاف العمليات
# ==========================================
@router.callback_query(F.data.in_({"stop_active_operations", "stop_transfer"}))
async def cb_stop(callback: CallbackQuery):
    global stop_flag
    stop_flag = True
    active = await get_active_transfer()
    if active:
        await update_transfer_status(active['id'], "stopped")
    await callback.message.answer("⛔ تم إرسال أمر إيقاف لجميع العمليات النشطة.")
    await callback.answer("تم الإيقاف")

# ==========================================
# 7. تسجيل الحسابات
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
