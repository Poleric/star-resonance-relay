from enum import Enum

# all method id are u32
class ChitChatNtf(Enum):
    NotifyNewestChitChatMsgs = 0x1


class Social(Enum):
    GetSocialData = 0x47065
