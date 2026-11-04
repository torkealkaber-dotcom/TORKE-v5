import logging
import sys
import os
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from telethon.errors import SessionPasswordNeededError, PhoneNumberInvalidError, PhoneCodeInvalidError, PhoneCodeExpiredError

# عشان يقرأ من الفولدر الأساسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from public_bot.bot.keyboards import get_public_main_keyboard, get_cancel_keyboard
from public_bot.bot.states import AddAccountStates
from public_bot.userbot import auth
from public_bot.database import add_client_user, add_client_account, get_client_accounts

logger = logging.getLogger(__name__)
router = Router()

temp_clients = {}

# ==========================================
# أوامر البدء
# ==========================================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    
    # تسجيل بيانات المستخدم في قاعدة البيانات
    await add_client_user(message.from_user.id, message.from_user.username, message.from_user.first_name)
    
    text = (
        f"أهلاً بك يا {message.from_user.first_name} 👋\n\n"
        "هذا البوت مخصص لإدارة حسابات تيليجرام الخاصة بك بشكل آمن.\n"
        "يمكنك من خلاله ربط حسابك للاستفادة من خدمات النقل والتفاعل.\n\n"
        "🔒 جميع بياناتك وجلساتك محفوظة بأمان تام.\n"
        "اضغط على الزر بالأسفل للبدء:"
    )
    
    await message.answer(text, reply_markup=get_public_main_keyboard())

# ==========================================
# إضافة حساب جديد
# ==========================================
@router.callback_query(F.data == "pub_add_account")
async def cb_add_account(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddAccountStates.waiting_for_phone)
    await callback.message.edit_text(
        "📱 يرجى إرسال رقم هاتفك بصيغة دولية:\n"
        "مثال: +201234567890\n\n"
        "ملاحظة: سيتم إرسال كود تحقق إلى حسابك على تيليجرام.",
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "pub_cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "تم إلغاء العملية. يمكنك البدء من جديد:",
        reply_markup=get_public_main_keyboard()
    )
    await callback.answer()

@router.message(AddAccountStates.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    if not phone.startswith("+"):
        return await message.answer("❌ الرقم لازم يبدأ بـ + ويشمل كود الدولة. جرب تاني:")
    
    try:
        client, session_path = await auth.create_client(phone)
        if await auth.is_authorized(client):
            await auth.safe_disconnect(client)
            await add_client_account(phone, session_path, message.from_user.id)
            await state.clear()
            return await message.answer(
                f"✅ الحساب {phone} مسجل بالفعل وتم إضافته لحساباتك.",
                reply_markup=get_public_main_keyboard()
            )

        await auth.send_code(client, phone)
        temp_clients[message.from_user.id] = client
        await state.update_data(phone=phone, session_path=session_path)
        await state.set_state(AddAccountStates.waiting_for_code)
        
        await message.answer(
            "✅ تم إرسال كود التحقق إلى حسابك.\n"
            "يرجى إرسال الكود هنا (مثال: 12345):"
        )
    except PhoneNumberInvalidError:
        await message.answer("❌ رقم الهاتف غير صحيح. تأكد من الرقم وحاول مرة أخرى:")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ حدث خطأ: {e}")
        await state.clear()

@router.message(AddAccountStates.waiting_for_code)
async def process_code(message: Message, state: FSMContext):
    code = message.text.strip()
    data = await state.get_data()
    phone, session_path = data.get("phone"), data.get("session_path")
    client = temp_clients.get(message.from_user.id)

    if not client:
        await state.clear()
        return await message.answer("انتهت الجلسة، ابدأ من جديد.", reply_markup=get_public_main_keyboard())

    try:
        await auth.sign_in_code(client, phone, code)
        await auth.safe_disconnect(client)
        await add_client_account(phone, session_path, message.from_user.id)
        temp_clients.pop(message.from_user.id, None)
        await state.clear()
        
        await message.answer(
            "🎉 تم تسجيل الدخول وإضافة الحساب بنجاح!\n"
            "شكراً لثقتك بنا.",
            reply_markup=get_public_main_keyboard()
        )
    except SessionPasswordNeededError:
        await state.set_state(AddAccountStates.waiting_for_2fa)
        await message.answer("🔐 الحساب محمي بالتحقق بخطوتين.\nيرجى إرسال كلمة المرور الخاصة بك:")
    except PhoneCodeInvalidError:
        await message.answer("❌ الكود غير صحيح. يرجى المحاولة مرة أخرى:")
    except PhoneCodeExpiredError:
        await auth.safe_disconnect(client)
        await state.clear()
        await message.answer("❌ انتهت صلاحية الكود. يرجى البدء من جديد.", reply_markup=get_public_main_keyboard())
    except Exception as e:
        await message.answer(f"❌ حدث خطأ: {e}\nحاول مرة أخرى.")

@router.message(AddAccountStates.waiting_for_2fa)
async def process_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    data = await state.get_data()
    phone, session_path = data.get("phone"), data.get("session_path")
    client = temp_clients.get(message.from_user.id)

    try:
        await auth.sign_in_password(client, password)
        await auth.safe_disconnect(client)
        await add_client_account(phone, session_path, message.from_user.id)
        temp_clients.pop(message.from_user.id, None)
        await state.clear()
        
        await message.answer(
            "🎉 تم تسجيل الدخول وإضافة الحساب بنجاح!\n"
            "شكراً لثقتك بنا.",
            reply_markup=get_public_main_keyboard()
        )
    except Exception as e:
        await message.answer(f"❌ كلمة المرور غير صحيحة: {e}\nحاول مرة أخرى.")

# ==========================================
# عرض حسابات المستخدم
# ==========================================
@router.callback_query(F.data == "pub_my_accounts")
async def cb_my_accounts(callback: CallbackQuery):
    accounts = await get_client_accounts(callback.from_user.id)
    
    if not accounts:
        await callback.answer("لا توجد حسابات مسجلة حتى الآن.", show_alert=True)
        return
    
    text = f"📊 حساباتك المسجلة ({len(accounts)}):\n\n"
    for i, acc in enumerate(accounts, 1):
        text += f"{i}. {acc['phone']}\n"
    
    await callback.message.answer(text)
    await callback.answer()

# ==========================================
# عن البوت
# ==========================================
@router.callback_query(F.data == "pub_about")
async def cb_about(callback: CallbackQuery):
    text = (
        "🤖 **بوت إدارة الحسابات**\n\n"
        "هذا البوت يسمح لك بربط حساباتك على تيليجرام للاستفادة من خدمات:\n"
        "• نقل الأعضاء بين المجموعات\n"
        "• التفاعل والرشق\n"
        "• إدارة القنوات والمجموعات\n\n"
        "🔒 **الأمان:**\n"
        "جميع الجلسات مشفرة ومحفوظة بشكل آمن ولا يتم مشاركتها مع أي طرف ثالث."
    )
    await callback.message.answer(text)
    await callback.answer()
