import struct


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
