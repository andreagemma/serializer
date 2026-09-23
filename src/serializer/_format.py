"""Versioned, self-describing on-disk format."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from typing import Final

from ._backends import (
    BACKEND_IDS,
    BACKENDS_BY_ID,
    COMPRESSION_IDS,
    COMPRESSIONS_BY_ID,
)
from .exceptions import FormatError

MAGIC: Final = b"SRLZ"
VERSION: Final = 1
_HEADER: Final = struct.Struct(">4sBBBBQI")


@dataclass(frozen=True, slots=True)
class Envelope:
    payload: bytes
    backend: str
    compression: str


def pack(payload: bytes, backend: str, compression: str) -> bytes:
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    header = _HEADER.pack(
        MAGIC,
        VERSION,
        BACKEND_IDS[backend],
        COMPRESSION_IDS[compression],
        0,
        len(payload),
        checksum,
    )
    return header + payload


def unpack(data: bytes) -> Envelope | None:
    """Read an envelope, or return ``None`` for a legacy raw payload."""
    if not data.startswith(MAGIC):
        return None
    if len(data) < _HEADER.size:
        raise FormatError("truncated serializer header")

    magic, version, backend_id, compression_id, flags, length, checksum = _HEADER.unpack_from(data)
    if magic != MAGIC:  # pragma: no cover - guarded by startswith
        return None
    if version != VERSION:
        raise FormatError(f"unsupported serializer format version: {version}")
    if flags != 0:
        raise FormatError(f"unsupported serializer format flags: {flags}")
    try:
        backend = BACKENDS_BY_ID[backend_id]
    except KeyError as exc:
        raise FormatError(f"unknown serializer backend id: {backend_id}") from exc
    try:
        compression = COMPRESSIONS_BY_ID[compression_id]
    except KeyError as exc:
        raise FormatError(f"unknown compression id: {compression_id}") from exc

    payload = data[_HEADER.size :]
    if len(payload) != length:
        raise FormatError(f"payload length mismatch: expected {length}, found {len(payload)}")
    if zlib.crc32(payload) & 0xFFFFFFFF != checksum:
        raise FormatError("payload checksum mismatch")
    return Envelope(payload, backend, compression)
