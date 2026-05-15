import logging
from collections import defaultdict
from typing import Callable

from google.protobuf.message import Message
from scapy.config import conf
from scapy.layers.inet import TCP, IP
from scapy.packet import Packet, Raw
from scapy.sendrecv import sniff
from scapy.sessions import TCPSession

from star_resonance_relay.packet.msg import CallMsg, NotifyMsg, ReturnMsg
from star_resonance_relay.packet.processor import BPSRPacketProcessor
from star_resonance_relay.sniffer.connection import Connection
from star_resonance_relay.utils import TCPReassembler

logger = logging.getLogger(__name__)
conf.layers.filter([TCP, IP])


class BPSRSniffer:
    ECHO_SIGNATURE = bytes.fromhex("00 00 00 06 00 04")

    def __init__[T: Message, K: Message](self):
        self._processor = BPSRPacketProcessor()
        self._reassemblers: dict[Connection, TCPReassembler] = defaultdict(TCPReassembler)
        self._known_servers: set[Connection] = set()
        self._handlers: dict[type[T], list[Callable[[T], None]]] = defaultdict(list)

        self._service_types: dict[tuple[int, int], type[T]] = {}
        self._return_types: dict[type[T], type[K]] = {}
        self._calls: dict[int, type[T]] = {}

    def set_service_type[T: Message](self, service_id: int, method_id: int, msg_type: type[T]) -> None:
        self._service_types[(service_id, method_id)] = msg_type

    def set_return_type[T: Message, K: Message](self, call_type: type[T], return_type: type[K]) -> None:
        self._return_types[call_type] = return_type

    def subscribe[T: Message](self, msg_type: type[T], callback: Callable[[T], None]) -> None:
        self._handlers[msg_type].append(callback)

    def _is_server(self, payload: bytes) -> bool:
        return payload.startswith(self.ECHO_SIGNATURE)

    def handle_packet(self, packet: Packet) -> None:
        if TCP not in packet or Raw not in packet:
            return

        connection = Connection.from_packet(packet)
        if connection not in self._known_servers:
            payload = bytes(packet[Raw])
            # Discover/lock server flow
            if self._is_server(payload):
                logger.info(f"Adding to flow "
                            f"{connection.source.ip}:{connection.source.port} <-> "
                            f"{connection.destination.ip}:{connection.destination.port}")
                self._known_servers.add(connection)

            return

        try:
            payload = bytes(packet[Raw])

            self._reassemblers[connection].push(packet[TCP].seq, payload)
            logger.info(self._reassemblers[connection].cache)
            for frame in self._reassemblers[connection].pop_frames():
                for msg in self._processor.process_bytes(frame):
                    match msg:
                        case CallMsg() | NotifyMsg():
                            msg_type = self._service_types.get((msg.service_uuid, msg.method_id))
                            if msg_type is None:
                                continue

                            if isinstance(msg, CallMsg):
                                self._calls[msg.call_id] = msg_type

                            handlers = self._handlers.get(msg_type, [])
                            for handler in handlers:
                                handler(msg_type.FromString(msg.data))

                        case ReturnMsg():
                            msg_type = self._calls.get(msg.call_id)
                            if msg_type is None:
                                continue

                            del self._calls[msg.call_id]

                            return_type = self._return_types.get(msg_type)
                            if return_type is None:
                                continue

                            handlers = self._handlers.get(return_type, [])
                            for handler in handlers:
                                handler(return_type.FromString(msg.data))

                        case _:
                            continue

        except Exception:
            logger.exception(packet)

    def sniff(self):
        sniff(filter="tcp and ip", prn=self.handle_packet, store=False, session=TCPSession)
