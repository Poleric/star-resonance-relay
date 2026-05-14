from abc import ABC, abstractmethod
from typing import override
from dataclasses import dataclass
import zstandard

from star_resonance_relay.utils import BinaryReader

MAX_ZSTD_BUFFER = 1_000_000  # 1 MB


class Msg(ABC):
    @classmethod
    @abstractmethod
    def from_raw(cls, data: bytes, *, zstd: bool = False):
        raise NotImplementedError


@dataclass(slots=True, frozen=True)
class CallMsg(Msg):
    service_uuid: int
    stub_id: int
    call_id: int
    method_id: int
    data: bytes

    @override
    @classmethod
    def from_raw(cls, data: bytes, *, zstd: bool = False):
        reader = BinaryReader(data)
        return cls(
            service_uuid=reader.read_u64(),
            stub_id=reader.read_u32(),
            call_id=reader.read_u32(),
            method_id=reader.read_u32(),
            data=zstandard.decompress(reader.read_remaining(), MAX_ZSTD_BUFFER) if zstd else reader.read_remaining()
        )


@dataclass(slots=True, frozen=True)
class NotifyMsg(Msg):
    service_uuid: int
    stub_id: int
    method_id: int
    data: bytes

    @override
    @classmethod
    def from_raw(cls, data: bytes, *, zstd: bool = False):
        reader = BinaryReader(data)
        return cls(
            service_uuid=reader.read_u64(),
            stub_id=reader.read_u32(),
            method_id=reader.read_u32(),
            data=zstandard.decompress(reader.read_remaining(), MAX_ZSTD_BUFFER) if zstd else reader.read_remaining()
        )


@dataclass(slots=True, frozen=True)
class ReturnMsg(Msg):
    stub_id: int
    call_id: int
    error_id: int
    data: bytes

    @override
    @classmethod
    def from_raw(cls, data: bytes, *, zstd: bool = False):
        reader = BinaryReader(data)
        return cls(
            stub_id=reader.read_u32(),
            call_id=reader.read_u32(),
            error_id=reader.read_u32(),
            data=zstandard.decompress(reader.read_remaining(), MAX_ZSTD_BUFFER) if zstd else reader.read_remaining()
        )


@dataclass(slots=True, frozen=True)
class FrameUpMsg(Msg):
    client_sequence: int
    nested_msg: bytes

    @override
    @classmethod
    def from_raw(cls, data: bytes, *, zstd: bool = False):
        reader = BinaryReader(data)
        return cls(
            client_sequence=reader.read_u32(),
            nested_msg=zstandard.decompress(reader.read_remaining(), MAX_ZSTD_BUFFER) if zstd else reader.read_remaining()
        )


@dataclass(slots=True, frozen=True)
class FrameDownMsg(Msg):
    server_sequence: int
    nested_msg: bytes

    @override
    @classmethod
    def from_raw(cls, data: bytes, *, zstd: bool = False):
        reader = BinaryReader(data)
        return cls(
            server_sequence=reader.read_u32(),
            nested_msg=zstandard.decompress(reader.read_remaining(), MAX_ZSTD_BUFFER) if zstd else reader.read_remaining()
        )
