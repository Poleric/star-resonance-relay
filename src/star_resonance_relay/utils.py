import struct
from io import BytesIO

from cachetools import TTLCache


class BinaryReader:
    """Helper to read big‑endian data from a bytes object.

    Instances maintain a cursor into an internal buffer.  Note that all
    multibyte values in the BPSR protocol are big‑endian.
    """

    def __init__(self, data: bytes):
        self._buffer = memoryview(data)
        self._pos = 0

    def remaining(self) -> int:
        return len(self._buffer) - self._pos

    def read(self, length: int) -> bytes:
        if self._pos + length > len(self._buffer):
            raise EOFError("unexpected end of buffer")
        b = self._buffer[self._pos: self._pos + length].tobytes()
        self._pos += length
        return b

    def peek_u32(self) -> int:
        if self.remaining() < 4:
            raise EOFError
        return struct.unpack_from(">I", self._buffer, self._pos)[0]

    def read_u8(self) -> int:
        return struct.unpack(">B", self.read(1))[0]

    def read_u16(self) -> int:
        return struct.unpack(">H", self.read(2))[0]

    def read_u32(self) -> int:
        return struct.unpack(">I", self.read(4))[0]

    def read_u64(self) -> int:
        return struct.unpack(">Q", self.read(8))[0]

    def read_remaining(self) -> bytes:
        return self.read(self.remaining())


class TCPStream:
    buf: BytesIO
    length: int

    def __init__(self, length: int, data: bytes | None = None):
        self.length = length
        self.buf = BytesIO()
        if data:
            self.buf.write(data)

    @property
    def current_length(self) -> int:
        return self.buf.tell()

    @property
    def is_complete(self) -> bool:
        return self.current_length >= self.length

    def write(self, data: bytes) -> int:
        return self.buf.write(data)

    def read(self) -> bytes:
        return self.buf.getvalue()


class TCPReassembler:
    """
    TCP Reassembler with misordered and packet loss handling. Scapy drops packets at high loads.
    """

    def __init__(self) -> None:
        self.streams: TTLCache[int, TCPStream] = TTLCache(maxsize=32, ttl=60)  # seq_num -> payload
        self.next_seq: TTLCache[int, int] = TTLCache(maxsize=32, ttl=60)

    def push(self, seq: int, payload: bytes) -> bytes | None:
        if not payload:
            return None

        payload_length = len(payload)
        if seq not in self.next_seq:
            start_seq = seq
            length = struct.unpack(">I", payload[:4])[0]
            if payload_length >= length:
                # complete payload
                return payload

            # else fragmented
            self.streams[seq] = TCPStream(length, payload)
        else:
            start_seq = self.next_seq[seq]
            stream = self.streams[start_seq]
            stream.write(payload)
            if stream.is_complete:
                del self.streams[start_seq]
                return stream.read()

        self.next_seq[seq + payload_length] = start_seq
        return None

