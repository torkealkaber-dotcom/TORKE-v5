import asyncio
from telethon import events, Button
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    FloodWaitError,
    PhoneNumberInvalidError,
)
from bot.states import State, set_state, get_state, get_data, clear_state
from bot.keyboards import main_menu, back_menu
from userbot import auth
from database import (
    add_account, get_accounts, delete_account,
    count_accounts, create_transfer, update_transfer
)
from config import DEVELOPER_ID


def is_developer(event):
    return event.sender_id == DEVELOPER_ID


def register_handlers(bot):

    # ============ /start ============
    @bot.on(events.NewMessage(pattern="/start"))
    async def start(event):
        if not is_developer(event):
            await event.respond("⛔ البوت ده خاص بالمطور فقط.")
            return
        clear_state(event.chat_id)
        count = count_accounts()
        await event.respond(
            f"أهلاً 👋\nعدد الحسابات المسجلة: {count}\nاختار:",
            buttons=main_menu()
        )

    # ============ رجوع ============
    @bot.on(events.CallbackQuery(data=b"back_main"))
    async def back_main(event):
        clear_state(event.chat_id)
        count = count_accounts()
        await event.edit(
            f"القائمة الرئيسية\nعدد الحسابات: {count}",
            buttons=main_menu()
        )

    # ============ إضافة حساب ============
    @bot.on(events.CallbackQuery(data=b"add_account"))
    async def add_account_cb(event):
        set_state(event.chat_id, State.WAITING_PHONE)
        await event.edit(
            "ابعت رقم الهاتف بصيغة دولية\nمثال: +201234567890",
            buttons=back_menu()
        )

    # ============ عرض الحسابات ============
    @bot.on(events.CallbackQuery(data=b"list_accounts"))
    async def list_accounts_cb(event):
        accounts = get_accounts(include_banned=True)
        if not accounts:
            await event.edit("مفيش حسابات مسجلة.", buttons=back_menu())
            return
        text = f"📊 الحسابات ({len(accounts)}):\n\n"
        for i, (phone, _) in enumerate(accounts, 1):
            text += f"{i}. {phone}\n"
        buttons = [[Button.inline("🔙 رجوع", b"back_main")]]
        # أزرار حذف لكل حساب
        for phone, _ in accounts:
            buttons.append([Button.inline(f"🗑 حذف {phone}", f"del_{phone}".encode())])
        await event.edit(text, buttons=buttons)

    # ============ حذف حساب ============
    @bot.on(events.CallbackQuery(pattern=b"^del_"))
    async def delete_account_cb(event):
        phone = event.data.decode().replace("del_", "")
        delete_account(phone)
        await event.answer(f"تم حذف {phone}")
        accounts = get_accounts(include_banned=True)
        if not accounts:
            await event.edit("مفيش حسابات مسجلة.", buttons=back_menu())
            return
        text = f"📊 الحسابات ({len(accounts)}):\n\n"
        for i, (p, _) in enumerate(accounts, 1):
            text += f"{i}. {p}\n"
        buttons = [[Button.inline("🔙 رجوع", b"back_main")]]
        for p, _ in accounts:
            buttons.append([Button.inline(f"🗑 حذف {p}", f"del_{p}".encode())])
        await event.edit(text, buttons=buttons)

    # ============ نقل أعضاء ============
    @bot.on(events.CallbackQuery(data=b"transfer_members"))
    async def transfer_cb(event):
        accounts = get_accounts()
        if not accounts:
            await event.edit("لازم تضيف حساب واحد على الأقل الأول.", buttons=back_menu())
            return
        set_state(event.chat_id, State.WAITING_SOURCE)
        await event.edit(
            "ابعت رابط/معرف المجموعة المصدر\nمثال: @source_group أو https://t.me/...",
            buttons=back_menu()
        )

    # ============ استقبال الرسائل النصية ============
    @bot.on(events.NewMessage)
    async def handle_input(event):
        if not is_developer(event):
            return
        chat_id = event.chat_id
        state = get_state(chat_id)
        if not state or state == State.IDLE:
            return

        text = event.raw_text.strip()
        data = get_data(chat_id)

        # ---------- استلام الرقم ----------
        if state == State.WAITING_PHONE:
            phone = text
            if not phone.startswith("+"):
                await event.respond("❌ الرقم لازم يبدأ بـ + ويشمل كود الدولة.")
                return
            try:
                client, session_path = await auth.create_client(phone)
                if await auth.is_authorized(client):
                    await auth.safe_disconnect(client)
                    add_account(phone, session_path)
                    clear_state(chat_id)
                    await event.respond("✅ الحساب مسجل دخول بالفعل واتضاف.", buttons=main_menu())
                    return
                await auth.send_code(client, phone)
                set_state(chat_id, State.WAITING_CODE,
                          phone=phone, client=client, session_path=session_path)
                await event.respond("✅ تم إرسال الكود. ابعته هنا.")
            except PhoneNumberInvalidError:
                await event.respond("❌ رقم غير صحيح. ابعته تاني.")
                clear_state(chat_id)
            except Exception as e:
                await event.respond(f"❌ خطأ: {e}")
                clear_state(chat_id)

        # ---------- استلام الكود ----------
        elif state == State.WAITING_CODE:
            client = data.get("client")
            phone = data.get("phone")
            session_path = data.get("session_path")
            if not client:
                clear_state(chat_id)
                await event.respond("انتهت الجلسة، ابدأ من جديد.", buttons=main_menu())
                return
            try:
                await auth.sign_in_code(client, phone, text)
                await auth.safe_disconnect(client)
                add_account(phone, session_path)
                clear_state(chat_id)
                await event.respond("✅ تم تسجيل الدخول بنجاح.", buttons=main_menu())
            except SessionPasswordNeededError:
                set_state(chat_id, State.WAITING_PASSWORD)
                await event.respond("🔐 الحساب عليه تحقق بخطوتين. ابعته كلمة المرور.")
            except PhoneCodeInvalidError:
                await event.respond("❌ الكود غلط. ابعته تاني.")
            except PhoneCodeExpiredError:
                await auth.safe_disconnect(client)
                clear_state(chat_id)
                await event.respond("❌ الكود انتهت صلاحيته. ابدأ من جديد.", buttons=main_menu())
            except Exception as e:
                await auth.safe_disconnect(client)
                clear_state(chat_id)
                await event.respond(f"❌ خطأ: {e}", buttons=main_menu())

        # ---------- استلام كلمة مرور 2FA ----------
        elif state == State.WAITING_PASSWORD:
            client = data.get("client")
            phone = data.get("phone")
            session_path = data.get("session_path")
            if not client:
                clear_state(chat_id)
                await event.respond("انتهت الجلسة، ابدأ من جديد.", buttons=main_menu())
                return
            try:
                await auth.sign_in_password(client, text)
                await auth.safe_disconnect(client)
                add_account(phone, session_path)
                clear_state(chat_id)
                await event.respond("✅ تم تسجيل الدخول بنجاح.", buttons=main_menu())
            except Exception as e:
                await event.respond(f"❌ كلمة المرور غلط أو خطأ: {e}\nابعتها تاني.")

        # ---------- استلام رابط المصدر ----------
        elif state == State.WAITING_SOURCE:
            set_state(chat_id, State.WAITING_TARGET, source=text)
            await event.respond("✅ المصدر اتسجل.\nدلوقتي ابعت رابط/معرف المجموعة الهدف.")

        # ---------- استلام رابط الهدف ----------
        elif state == State.WAITING_TARGET:
            source = data.get("source")
            target = text
            clear_state(chat_id)
            await event.respond("⏳ جاري سحب الأعضاء وإضافتهم... ممكن ياخد وقت.")
            try:
                from userbot.invite import transfer_members
                result = await transfer_members(source, target)
                await event.respond(f"✅ انتهت العملية:\n{result}", buttons=main_menu())
            except Exception as e:
                await event.respond(f"❌ خطأ أثناء النقل: {e}", buttons=main_menu())
