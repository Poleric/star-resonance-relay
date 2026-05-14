import struct

from scapy.fields import IntField, ByteEnumField
from scapy.layers.inet import TCP, IP
from scapy.packet import Packet, Raw, conf

from star_resonance_relay.packet.packet import MsgType, Compression
from star_resonance_relay.sniffer.connection import Connection


class BPSRPacket(Packet):
    name = "BPSRPacket"
    fields_desc = [
        IntField("length", None),
        ByteEnumField("compression", 0, enum=Compression),
        ByteEnumField("type", 0, enum=MsgType)
    ]

    @classmethod
    def tcp_reassemble(cls, data, *_args, **_kwargs):
        if len(data) < 4:
            return None

        length = struct.unpack(">I", data[:4])[0]
        if len(data) >= length:
            return cls(data)

        return None

    def mysummary(self):
        return self.sprintf("BPSRPacket %BPSRPacket.length% %BPSRPacket.type%")


KNOWN_SERVERS: set[Connection] = set()


def add_bpsr_packet_dissect(func):
    def guess_payload_class(self: TCP, payload: bytes) -> type[Packet]:
        if Raw in self and isinstance(self.underlayer, IP):
            connection = Connection.from_tcp_ip(self, self.underlayer)  # noqa
            if connection in KNOWN_SERVERS:
                return BPSRPacket
        return func(self, payload)

    return guess_payload_class


TCP.guess_payload_class = add_bpsr_packet_dissect(TCP.guess_payload_class)
conf.layers.filter([BPSRPacket, TCP, IP])
