import asyncio
import random
from telethon import TelegramClient, functions, types
from telethon.errors import (
    FloodWaitError,
    PeerFloodError,
    UserPrivacyRestrictedError,
    UserAlreadyParticipantError,
    UserNotMutualContactError,
    ChatAdminRequiredError
)
from config import API_ID, API_HASH, DELAY_MIN, DELAY_MAX

# ==========================================
# 1. وظائف النقل (سحب وإضافة الأعضاء)
# ==========================================
async def transfer_members(session_path, source_link, target_link, limit, delay, mode="hidden"):
    """
    وظيفة نقل الأعضاء.
    mode: "hidden" (إضافة قسرية) أو "visible" (دعوة)
    limit: أقصى عدد أعضاء (0 = الكل)
    delay: وقت الانتظار بين كل إضافة
    """
    added = 0
    failed = 0
    skipped = 0
    
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            source = await client.get_entity(source_link)
            target = await client.get_entity(target_link)
        except Exception as e:
            return {"error": f"تأكد من الروابط أو أن الحساب موجود في المجموعتين. ({e})"}

        # سحب قائمة الأعضاء
        members = []
        async for user in client.iter_participants(source):
            if user.bot or user.deleted:
                continue
            members.append(user.id)
            if limit > 0 and len(members) >= limit:
                break
                
        if not members:
            return {"error": "لم يتم العثور على أعضاء في المجموعة المصدر."}

        # بدء الإضافة
        for member_id in members:
            try:
                if mode == "visible":
                    # دعوة مباشرة (تظهر إشعار للمستخدم)
                    await client(functions.channels.InviteToChannelRequest(target, [member_id]))
                else:
                    # إضافة قسرية (قد لا تظهر كإشعار اعتماداً على إعدادات الخصوصية)
                    await client(functions.channels.InviteToChannelRequest(target, [member_id]))
                    # ملاحظة: تيليجرام لا يدعم "الإضافة الصامتة" تماماً، الفارق يكمن في نوع الحساب وإعداداته.
                
                added += 1
            except FloodWaitError as e:
                # انتظار إجباري من تيليجرام
                await asyncio.sleep(e.seconds + 5)
                skipped += 1
            except (UserPrivacyRestrictedError, UserNotMutualContactError, UserAlreadyParticipantError):
                # المستخدم مقفل الخصوصية أو موجود بالفعل
                skipped += 1
            except Exception:
                failed += 1
            
            # الانتظار المحدد من المستخدم أو العشوائي
            wait_time = delay if delay > 0 else random.randint(DELAY_MIN, DELAY_MAX)
            await asyncio.sleep(wait_time)

    return {"added": added, "failed": failed, "skipped": skipped, "total": len(members)}

# ==========================================
# 2. وظائف الانضمام والخروج
# ==========================================
async def join_channel(session_path, link):
    """انضمام حساب إلى قناة أو مجموعة"""
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            await client(functions.channels.JoinChannelRequest(link))
            return True, "تم الانضمام بنجاح"
        except Exception as e:
            return False, str(e)

async def leave_channel(session_path, link):
    """خروج حساب من قناة أو مجموعة"""
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            entity = await client.get_entity(link)
            await client(functions.channels.LeaveChannelRequest(entity))
            return True, "تم الخروج بنجاح"
        except Exception as e:
            return False, str(e)

# ==========================================
# 3. وظائف الرشق (تفاعل، مشاهدات، تصويت)
# ==========================================
async def spam_views(session_path, post_link, views_count=100):
    """زيادة مشاهدات بوست معين"""
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            # استخراج معرف القناة والرسالة من الرابط
            parts = post_link.split("/")
            channel = parts[-2]
            msg_id = int(parts[-1])
            
            entity = await client.get_entity(channel)
            for _ in range(views_count):
                await client(functions.messages.GetMessagesViewsRequest(
                    peer=entity,
                    id=[msg_id],
                    increment=True
                ))
                await asyncio.sleep(0.5) # تأخير بسيط لتجنب الحظر
            return True, f"تم إرسال {views_count} مشاهدة."
        except Exception as e:
            return False, str(e)

async def spam_reactions(session_path, post_link, reaction="👍", count=10):
    """إضافة تفاعلات (ريأكشن) لبوست"""
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            parts = post_link.split("/")
            entity = await client.get_entity(parts[-2])
            msg_id = int(parts[-1])
            
            for _ in range(count):
                await client(functions.messages.SendReactionRequest(
                    peer=entity,
                    msg_id=msg_id,
                    reaction=[types.ReactionEmoji(emoticon=reaction)]
                ))
                await asyncio.sleep(1)
            return True, f"تم إرسال {count} تفاعل."
        except Exception as e:
            return False, str(e)

# ==========================================
# 4. وظائف الإدارة والتحقق
# ==========================================
async def end_all_sessions(session_path):
    """إنهاء جميع الجلسات النشطة للحساب (تسجيل خروج من الأجهزة الأخرى)"""
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            await client(functions.auth.ResetAuthorizationsRequest())
            return True, "تم إنهاء جميع الجلسات الأخرى."
        except Exception as e:
            return False, str(e)

async def leave_all_chats(session_path):
    """الخروج من كل المجموعات والقنوات"""
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        left_count = 0
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                try:
                    await client.delete_dialog(dialog.entity)
                    left_count += 1
                    await asyncio.sleep(1)
                except:
                    pass
        return True, f"تم الخروج من {left_count} محادثة."
