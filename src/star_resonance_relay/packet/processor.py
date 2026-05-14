import logging
from typing import Iterator

from google.protobuf.message import Message

from star_resonance_relay.packet.msg import Msg, CallMsg, NotifyMsg, ReturnMsg, FrameUpMsg, FrameDownMsg
from star_resonance_relay.packet.packet import Packet, MsgType, Compression
from star_resonance_relay.utils import BinaryReader

logger = logging.getLogger(__name__)

MAX_ZSTD_BUFFER = 10 * 1024 * 1024  # 10 mb


class BPSRPacketProcessor:
    """
    Process assembled BPSR frames into method opcodes and payloads.
    """

    def process_packet(self, packet: Packet) -> Iterator[Msg]:
        match packet.type:
            case MsgType.CALL:
                yield CallMsg.from_raw(packet.data, zstd=packet.compression == Compression.ZSTD)

            case MsgType.NOTIFY:
                yield NotifyMsg.from_raw(packet.data, zstd=packet.compression == Compression.ZSTD)

            case MsgType.RETURN:
                yield ReturnMsg.from_raw(packet.data, zstd=packet.compression == Compression.ZSTD)

            case MsgType.FRAME_UP | MsgType.FRAME_DOWN:
                msg: FrameUpMsg | FrameDownMsg
                if packet.type == MsgType.FRAME_UP:
                    msg = FrameUpMsg.from_raw(packet.data, zstd=packet.compression == Compression.ZSTD)
                else:
                    msg = FrameDownMsg.from_raw(packet.data, zstd=packet.compression == Compression.ZSTD)

                reader = BinaryReader(msg.nested_msg)
                while reader.remaining():
                    length = reader.peek_u32()
                    yield from self.process_bytes(reader.read(length))

            case _:
                pass

    def process_bytes(self, data: bytes) -> Iterator[Msg]:
        yield from self.process_packet(Packet.from_raw(data))
