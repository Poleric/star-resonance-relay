import logging
from dataclasses import dataclass
from typing import Callable, Self

from scapy.arch import get_if_addr
from scapy.fields import BitField, BitEnumField, IntField, PacketLenField
from scapy.sendrecv import sniff
from scapy.sessions import TCPSession
from google.protobuf.message import Message
from scapy.layers.inet import TCP, IP
import struct
from scapy.packet import Packet, Raw
from scapy.config import conf

from star_resonance_relay.processor import BPSRPacketProcessor, FragmentType

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ServerPort:
    ip: str
    port: int


@dataclass(frozen=True, slots=True)
class Connection:
    source: ServerPort
    destination: ServerPort

    @classmethod
    def from_tcp_ip(cls, tcp: TCP, ip: IP) -> Self:
        return cls(
            ServerPort(ip.src, tcp.sport),
            ServerPort(ip.dst, tcp.dport)
        )

    @classmethod
    def from_packet(cls, packet: Packet) -> Self:
        return cls.from_tcp_ip(packet[TCP], packet[IP])

known_servers: set[Connection] = set()


class BPSRPacket(Packet):
    name = "BPSRPacket"
    fields_desc = [
        IntField("length", None),
        BitField("is_compressed", 0, size=1),
        BitEnumField("type", 0, enum=FragmentType, size=15)
    ]

    @classmethod
    def tcp_reassemble(cls, data, *args, **kwargs):
        if len(data) < 4:
            return None

        length = struct.unpack(">I", data[:4])[0]
        if len(data) >= length + 4:
            return cls(data)

        return None

    def mysummary(self):
        return self.sprintf("BPSRPacket %BPSRPacket.length% %BPSRPacket.type%")


def add_bpsr_packet_dissect(func):
    def guess_payload_class(self: TCP, payload: bytes) -> type[Packet]:
        if Raw in self and isinstance(self.underlayer, IP):
            connection = Connection.from_tcp_ip(self, self.underlayer)  # noqa
            if connection in known_servers:
                return BPSRPacket
        return func(self, payload)
    return guess_payload_class

TCP.guess_payload_class = add_bpsr_packet_dissect(TCP.guess_payload_class)
conf.layers.filter([BPSRPacket, TCP, IP])
LOCAL_IP = get_if_addr(conf.iface)
logger.info(f"Local IP discovered as {LOCAL_IP}")


class BPSRSniffer:
    ECHO_SIGNATURE = bytes.fromhex("00 00 00 06 00 04")

    def __init__(self, callback: Callable[[Message], None]):
        self._callback = callback
        self._processor = BPSRPacketProcessor()

    def _is_server(self, payload: bytes) -> bool:
        return payload.startswith(self.ECHO_SIGNATURE)

    def handle_packet(self, packet: Packet) -> None:
        if TCP not in packet or Raw not in packet:
            return

        connection = Connection.from_packet(packet)
        # Filter server responses only
        if connection.source.ip == LOCAL_IP:
            return

        if BPSRPacket not in packet:
            if connection not in known_servers:
                payload = bytes(packet[Raw])

                # Discover/lock server flow
                if self._is_server(payload):
                    logger.info(f"Adding to flow "
                                f"{connection.source.ip}:{connection.source.port} <-> "
                                f"{connection.destination.ip}:{connection.destination.port}")
                    known_servers.add(connection)

            return

        try:
            payload = bytes(packet[BPSRPacket])
            logger.info(f"{connection.source.ip} <-> {connection.destination.ip}: {packet} {len(payload)}")

            for notify_frame in self._processor.process_frame(payload):
                try:
                    message = self._processor.decode_payload(notify_frame)
                except NotImplementedError:
                    logger.info(f"Failed to decode payload. {notify_frame}")
                    continue
                self._callback(message)
        except Exception:
            logger.exception(packet)

    def sniff(self):
        sniff(filter="tcp", prn=self.handle_packet, store=False, session=TCPSession)
