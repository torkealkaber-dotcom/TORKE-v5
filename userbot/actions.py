import asyncio
import random
import logging
from telethon import TelegramClient, functions
from telethon.errors import (
    FloodWaitError, PeerFloodError,
    UserPrivacyRestrictedError, UserAlreadyParticipantError,
    UserNotMutualContactError
)
from config import API_ID, API_HASH, DELAY_MIN, DELAY_MAX

logger = logging.getLogger(__name__)

async def transfer_members(session_paths, source_link, target_link, total_limit, account_limit, delay, mode="hidden"):
    """
    نقل الأعضاء باستخدام عدة حسابات (Round-Robin)
    - total_limit: إجمالي الأعضاء المطلوب نقلهم (0 = الكل)
    - account_limit: عدد الأعضاء لكل حساب قبل التبديل
    """
    added = 0
    failed = 0
    skipped = 0
    
    # 1. سحب الأعضاء باستخدام أول حساب متاح
    members = []
    try:
        async with TelegramClient(session_paths[0], API_ID, API_HASH) as client:
            source = await client.get_entity(source_link)
            async for user in client.iter_participants(source):
                if user.bot or user.deleted:
                    continue
                members.append(user.id)
                if total_limit > 0 and len(members) >= total_limit:
                    break
    except Exception as e:
        logger.error(f"Error fetching members: {e}")
        return {"error": f"فشل سحب الأعضاء: {e}"}

    if not members:
        return {"error": "لم يتم العثور على أعضاء في المصدر."}

    # 2. توزيع الإضافة على الحسابات
    current_member_index = 0
    total_members = len(members)

    for session_path in session_paths:
        # لو وصلنا للحد الكلي المطلوب، نوقف
        if current_member_index >= total_members:
            break
            
        account_added = 0
        logger.info(f"Starting with account: {session_path}")
        
        try:
            async with TelegramClient(session_path, API_ID, API_HASH) as client:
                target = await client.get_entity(target_link)
                
                # الحساب يفضل يضيف لحد ما يوصل للحد بتاعه أو نخلص الأعضاء
                while account_added < account_limit and current_member_index < total_members:
                    member_id = members[current_member_index]
                    
                    try:
                        # إضافة العضو
                        await client(functions.channels.InviteToChannelRequest(target, [member_id]))
                        added += 1
                        account_added += 1
                    except FloodWaitError as e:
                        logger.warning(f"FloodWait: {e.seconds}s")
                        await asyncio.sleep(e.seconds + 5)
                        skipped += 1
                    except (UserPrivacyRestrictedError, UserNotMutualContactError, UserAlreadyParticipantError):
                        skipped += 1
                    except PeerFloodError:
                        logger.error(f"Account {session_path} is PeerFlooded!")
                        failed += 1
                        break # هذا الحساب انتهى أمره، ننتقل للحساب التالي
                    except Exception as e:
                        logger.error(f"Error adding member: {e}")
                        failed += 1

                    # الانتقال للعضو اللي بعده
                    current_member_index += 1
                    
                    # وقت الانتظار
                    wait_time = delay if delay > 0 else random.randint(DELAY_MIN, DELAY_MAX)
                    await asyncio.sleep(wait_time)

        except Exception as e:
            logger.error(f"Failed to use session {session_path}: {e}")
            # لو الحساب فيه مشكلة (زي انتهاء الجلسة)، البوت هيتخطاه ويكمل باللي بعده
            continue

    return {
        "added": added,
        "failed": failed,
        "skipped": skipped,
        "total": total_members
              }
