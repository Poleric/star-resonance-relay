from dataclasses import dataclass
from typing import Self

from scapy.layers.inet import TCP, IP
from scapy.packet import Packet


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
