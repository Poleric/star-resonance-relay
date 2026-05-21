from enum import Enum

__all__ = (
    "ChitChatNtf",
    "Social"
)


class ChitChatNtf(Enum):
    ServiceId = 0x9d4a768

    class Method(Enum):
        NotifyNewestChitChatMsgs = 0x1


class Social(Enum):
    ServiceId = 0x626ad66

    class Method(Enum):
        GetSocialData = 0x47065
