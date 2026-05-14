from abc import ABC
from dataclasses import dataclass
from enum import Enum

from star_resonance_relay.utils import BinaryReader


class MsgType(Enum):
    """Enumeration of message types used within the BPSR protocol."""

    NONE = 0
    CALL = 1
    NOTIFY = 2
    RETURN = 3
    ECHO = 4
    FRAME_UP = 5
    FRAME_DOWN = 6
    ACK_FRAME_UP = 7
    ACK_FRAME_DOWN = 8
    REWIND_FRAME = 9
    CALL_INNER = 10
    NOTIFY_INNER = 11
    BROADCAST = 12
    BROADCAST_BY_SES = 13
    TERMINATE = 14


class Compression(Enum):
    NONE = 0
    ZSTD = 0x80


@dataclass(slots=True, frozen=True)
class Packet(ABC):
    length: int
    compression: Compression
    type: MsgType
    data: bytes

    @classmethod
    def from_raw(cls, data: bytes):
        reader = BinaryReader(data)
        return cls(
            length=reader.read_u32(),
            compression=Compression(reader.read_u8()),
            type=MsgType(reader.read_u8()),
            data=reader.read_remaining()
        )
