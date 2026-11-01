from enum import Enum, auto


class State(Enum):
    IDLE = auto()
    WAITING_PHONE = auto()
    WAITING_CODE = auto()
    WAITING_PASSWORD = auto()
    WAITING_SOURCE = auto()
    WAITING_TARGET = auto()
    WAITING_LIMIT = auto()


# حالة كل مستخدم: {chat_id: {"state": State, ...بيانات إضافية}}
USER_STATES = {}


def set_state(chat_id, state, **kwargs):
    """تعيين حالة المستخدم مع بيانات إضافية"""
    if chat_id not in USER_STATES:
        USER_STATES[chat_id] = {}
    USER_STATES[chat_id]["state"] = state
    USER_STATES[chat_id].update(kwargs)


def get_state(chat_id):
    """جلب حالة المستخدم"""
    return USER_STATES.get(chat_id, {}).get("state")


def get_data(chat_id):
    """جلب بيانات المستخدم"""
    return USER_STATES.get(chat_id, {})


def clear_state(chat_id):
    """مسح حالة المستخدم"""
    USER_STATES.pop(chat_id, None)
