import asyncio
import random
from telethon import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.errors import (
    FloodWaitError,
    PeerFloodError,
    UserPrivacyRestrictedError,
    UserAlreadyParticipantError,
    UserNotMutualContactError,
)
from config import API_ID, API_HASH, DAILY_LIMIT, DELAY_MIN, DELAY_MAX
from database import (
    get_accounts, increment_daily, get_daily_count,
    ban_account, create_transfer, update_transfer
)


async def transfer_members(source, target, max_members=None):
    """
    نقل الأعضاء من المصدر للهدف.
    - source: رابط/معرف المجموعة المصدر
    - target: رابط/معرف المجموعة الهدف
    - max_members: حد أقصى للأعضاء (None = الكل)
    """
    accounts = get_accounts()
    if not accounts:
        return "❌ مفيش حسابات مسجلة."

    transfer_id = create_transfer(source, target)
    added = failed = skipped = 0

    # ===== 1) سحب الأعضاء من المصدر بأول حساب =====
    first_phone, first_session = accounts[0]
    members = []
    try:
        async with TelegramClient(first_session, API_ID, API_HASH) as main_client:
            source_entity = await main_client.get_entity(source)
            target_entity = await main_client.get_entity(target)

            # التأكد إن كل الحسابات في الهدف
            for phone, sess in accounts:
                try:
                    async with TelegramClient(sess, API_ID, API_HASH) as c:
                        me = await c.get_me()
                        await c(InviteToChannelRequest(target_entity, [me]))
                except UserAlreadyParticipantError:
                    pass
                except Exception:
                    pass

            # سحب الأعضاء
            async for user in main_client.iter_participants(source_entity):
                if user.bot or user.deleted:
                    continue
                members.append(user.id)
                if max_members and len(members) >= max_members:
                    break
    except Exception as e:
        update_transfer(transfer_id, 0, 0, 0)
        return f"❌ فشل قراءة المجموعات: {e}"

    if not members:
        update_transfer(transfer_id, 0, 0, 0)
        return "❌ مفيش أعضاء اتسحبوا من المصدر."

    # ===== 2) فتح جلسة لكل حساب متاح =====
    clients = []
    for phone, sess in accounts:
        if get_daily_count(phone) >= DAILY_LIMIT:
            continue
        try:
            client = TelegramClient(sess, API_ID, API_HASH)
            client.flood_sleep_threshold = 3600  # ينتظر FloodWait لحد ساعة
            await client.connect()
            if await client.is_user_authorized():
                clients.append((phone, client))
        except Exception:
            try:
                await client.disconnect()
            except Exception:
                pass

    if not clients:
        update_transfer(transfer_id, 0, 0, 0)
        return "❌ مفيش حسابات متاحة (كلها محظورة أو وصلت الحد اليومي)."

    # ===== 3) توزيع الإضافة على الحسابات =====
    try:
        idx = 0
        for member_id in members:
            # اختيار الحساب التالي المتاح
            attempts = 0
            while attempts < len(clients):
                phone, client = clients[idx % len(clients)]
                idx += 1

                # تحقق من الحد اليومي
                if get_daily_count(phone) >= DAILY_LIMIT:
                    attempts += 1
                    continue

                try:
                    await client(InviteToChannelRequest(target, [member_id]))
                    increment_daily(phone)
                    added += 1
                    break
                except FloodWaitError as e:
                    skipped += 1
                    await asyncio.sleep(min(e.seconds, 60))
                    attempts += 1
                except PeerFloodError:
                    ban_account(phone, hours=24)
                    failed += 1
                    attempts += 1
                except (UserPrivacyRestrictedError,
                        UserNotMutualContactError):
                    skipped += 1
                    break
                except UserAlreadyParticipantError:
                    skipped += 1
                    break
                except Exception:
                    failed += 1
                    attempts += 1

            # تأخير عشوائي بين كل إضافة
            await asyncio.sleep(random.randint(DELAY_MIN, DELAY_MAX))

    finally:
        for _, client in clients:
            try:
                await client.disconnect()
            except Exception:
                pass

    update_transfer(transfer_id, added, failed, skipped)
    return (
        f"✅ تمت الإضافة: {added}\n"
        f"❌ فشل: {failed}\n"
        f"⏭ تخطي: {skipped}\n"
        f"📊 إجمالي الأعضاء: {len(members)}"
    )
