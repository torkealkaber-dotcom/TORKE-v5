import asyncio
import random
import logging
import sys
import os
from telethon import TelegramClient, functions, types
from telethon.errors import (
    FloodWaitError, PeerFloodError,
    UserPrivacyRestrictedError, UserAlreadyParticipantError,
    UserNotMutualContactError, ChatAdminRequiredError
)

# عشان يقرأ من الكونفيج الأساسي
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import API_ID, API_HASH, DELAY_MIN, DELAY_MAX

logger = logging.getLogger(__name__)

async def transfer_members(session_paths, source_link, target_link, total_limit, account_limit, delay, mode="hidden", filter_online=False, filter_premium=False):
    added = 0
    failed = 0
    skipped = 0
    
    members = []
    members_set = set()
    
    try:
        async with TelegramClient(session_paths[0], API_ID, API_HASH) as client:
            source = await client.get_entity(source_link)
            me = await client.get_me()
            
            if mode == "hidden":
                logger.info("Starting Hidden extraction (from messages)")
                msg_limit = total_limit * 3 if total_limit > 0 else 5000
                
                async for message in client.iter_messages(source, limit=msg_limit):
                    if isinstance(message.sender, types.User):
                        user = message.sender
                        if user.bot or user.deleted or user.id == me.id:
                            continue
                        if user.id in members_set:
                            continue
                            
                        if filter_online and not isinstance(user.status, types.UserStatusOnline):
                            continue
                        
                        if filter_premium and not getattr(user, 'premium', False):
                            continue
                        
                        members_set.add(user.id)
                        members.append(user.id)
                        
                        if total_limit > 0 and len(members) >= total_limit:
                            break
            else:
                logger.info("Starting Visible extraction (from participant list)")
                async for user in client.iter_participants(source):
                    if user.bot or user.deleted or user.id == me.id:
                        continue
                    
                    if filter_online and not isinstance(user.status, types.UserStatusOnline):
                        continue
                    
                    if filter_premium and not getattr(user, 'premium', False):
                        continue
                    
                    members.append(user.id)
                    if total_limit > 0 and len(members) >= total_limit:
                        break
                        
    except Exception as e:
        logger.error(f"Error fetching members: {e}")
        return {"error": f"فشل سحب الأعضاء: {e}"}

    if not members:
        return {"error": "لم يتم العثور على أعضاء يطابقون الشروط."}

    current_member_index = 0
    total_members = len(members)

    for session_path in session_paths:
        if current_member_index >= total_members:
            break
            
        account_added = 0
        try:
            async with TelegramClient(session_path, API_ID, API_HASH) as client:
                try:
                    target = await client.get_entity(target_link)
                except Exception:
                    continue
                
                while account_added < account_limit and current_member_index < total_members:
                    member_id = members[current_member_index]
                    try:
                        await client(functions.channels.InviteToChannelRequest(target, [member_id]))
                        added += 1
                        account_added += 1
                    except FloodWaitError as e:
                        await asyncio.sleep(e.seconds + 5)
                        skipped += 1
                    except (UserPrivacyRestrictedError, UserNotMutualContactError, UserAlreadyParticipantError):
                        skipped += 1
                    except ChatAdminRequiredError:
                        break
                    except PeerFloodError:
                        failed += 1
                        break
                    except Exception:
                        failed += 1

                    current_member_index += 1
                    wait_time = delay if delay > 0 else random.randint(DELAY_MIN, DELAY_MAX)
                    await asyncio.sleep(wait_time)
        except Exception:
            continue

    return {"added": added, "failed": failed, "skipped": skipped, "total": total_members}

async def join_channel(session_path, link):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            await client(functions.channels.JoinChannelRequest(link))
            return True, "تم الانضمام بنجاح."
        except UserAlreadyParticipantError:
            return True, "الحساب منضم بالفعل."
        except Exception as e:
            return False, str(e)

async def leave_channel(session_path, link):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            entity = await client.get_entity(link)
            await client(functions.channels.LeaveChannelRequest(entity))
            return True, "تم الخروج بنجاح."
        except Exception as e:
            return False, str(e)

async def spam_views(session_path, post_link, views_count=100):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            parts = post_link.split("/")
            channel = parts[-2]
            msg_id = int(parts[-1])
            entity = await client.get_entity(channel)
            
            for _ in range(views_count):
                await client(functions.messages.GetMessagesViewsRequest(
                    peer=entity, id=[msg_id], increment=True
                ))
                await asyncio.sleep(0.3)
            return True, f"تم إرسال {views_count} مشاهدة."
        except Exception as e:
            return False, str(e)

async def spam_reactions(session_path, post_link, reaction="👍", count=10):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            parts = post_link.split("/")
            entity = await client.get_entity(parts[-2])
            msg_id = int(parts[-1])
            
            for _ in range(count):
                await client(functions.messages.SendReactionRequest(
                    peer=entity, msg_id=msg_id,
                    reaction=[types.ReactionEmoji(emoticon=reaction)]
                ))
                await asyncio.sleep(1)
            return True, f"تم إرسال {count} تفاعل."
        except Exception as e:
            return False, str(e)

async def spam_poll_vote(session_path, post_link, option_index=0, count=10):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            parts = post_link.split("/")
            entity = await client.get_entity(parts[-2])
            msg_id = int(parts[-1])
            
            messages = await client.get_messages(entity, ids=msg_id)
            if not messages or not messages[0]:
                return False, "لم يتم العثور على الرسالة."
            
            msg = messages[0]
            if msg.poll:
                for _ in range(count):
                    await client(functions.messages.SendVoteRequest(
                        peer=entity, msg_id=msg_id,
                        options=[msg.poll.poll.answers[option_index].option]
                    ))
                    await asyncio.sleep(1)
                return True, f"تم التصويت {count} مرة."
            else:
                return False, "هذه الرسالة لا تحتوي على استفتاء."
        except Exception as e:
            return False, str(e)

async def end_all_sessions(session_path):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            await client(functions.auth.ResetAuthorizationsRequest())
            return True, "تم إنهاء جميع الجلسات الأخرى."
        except Exception as e:
            return False, str(e)

async def leave_all_chats(session_path):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        left_count = 0
        async for dialog in client.iter_dialogs():
            if dialog.is_group or dialog.is_channel:
                try:
                    await client.delete_dialog(dialog.entity)
                    left_count += 1
                    await asyncio.sleep(0.5)
                except:
                    pass
        return True, f"تم الخروج من {left_count} محادثة."

async def change_2fa_password(session_path, old_password, new_password):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            if old_password:
                try:
                    await client.sign_in(password=old_password)
                except Exception:
                    return False, "كلمة المرور القديمة خاطئة."
            await client.edit_2fa(new_password=new_password)
            return True, "تم تغيير كلمة مرور التحقق بنجاح."
        except Exception as e:
            return False, str(e)

async def check_verify_link(session_path, username):
    async with TelegramClient(session_path, API_ID, API_HASH) as client:
        try:
            user = await client.get_entity(username)
            is_verified = getattr(user, 'verified', False)
            status = "موثق ✅" if is_verified else "غير موثق ❌"
            return True, f"الحساب @{username}:\n{status}"
        except Exception as e:
            return False, str(e)
