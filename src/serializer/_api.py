"""Public functional and fluent APIs."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, replace
from os import PathLike
from pathlib import Path
from typing import Any, BinaryIO, ClassVar

from ._backends import (
    compress,
    decompress,
    normalize_compression,
    serializer_backend,
    validate_level,
)
from ._format import pack, unpack
from .exceptions import FormatError, SerializationError, SerializerError

Pathish = str | PathLike[str]
Readable = Pathish | BinaryIO
Writable = Pathish | BinaryIO


def dumps(
    obj: Any,
    *,
    compression: str | None = None,
    level: int = 5,
    protocol: int | None = None,
    backend: str = "auto",
    fallback: bool = True,
) -> bytes:
    """Serialize *obj* into self-describing bytes.

    ``dill`` is loaded lazily and preferred. If it is unavailable, a warning is
    emitted and stdlib ``pickle`` is used. Missing optional compressors likewise
    fall back to an uncompressed envelope unless ``fallback=False``.
    """
    validate_level(level)
    module, actual_backend = serializer_backend(backend, fallback=fallback)
    if protocol is not None and (isinstance(protocol, bool) or not isinstance(protocol, int)):
        raise TypeError("protocol must be an integer or None")
    try:
        if protocol is None:
            serialized = module.dumps(obj, protocol=getattr(module, "HIGHEST_PROTOCOL", 5))
        else:
            serialized = module.dumps(obj, protocol=protocol)
    except Exception as exc:
        raise SerializationError(
            f"could not serialize {type(obj).__module__}.{type(obj).__qualname__} "
            f"with {actual_backend}"
        ) from exc
    payload, actual_compression = compress(serialized, compression, level, fallback=fallback)
    return pack(payload, actual_backend, actual_compression)


def loads(
    data: bytes | bytearray | memoryview,
    *,
    compression: str | None = None,
    backend: str = "auto",
) -> Any:
    """Deserialize bytes created by :func:`dumps` or a legacy raw pickle.

    New envelopes contain their backend and compression metadata. ``compression``
    and ``backend`` are only needed when reading legacy, headerless payloads.

    Warning: as with pickle and dill, never load untrusted data.
    """
    if not isinstance(data, bytes | bytearray | memoryview):
        raise TypeError("data must be bytes-like")
    raw = bytes(data)
    if not raw:
        raise FormatError("cannot deserialize an empty payload")

    envelope = unpack(raw)
    if envelope is None:
        codec = normalize_compression(compression)
        if codec == "auto":
            raise ValueError("legacy payloads require an explicit compression codec")
        payload = raw
        requested_backend = backend
    else:
        codec = envelope.compression
        payload = envelope.payload
        requested_backend = envelope.backend

    try:
        serialized = decompress(payload, codec)
        module, _actual_backend = serializer_backend(requested_backend, fallback=True)
        return module.loads(serialized)
    except SerializerError:
        raise
    except Exception as exc:
        raise SerializationError(
            f"could not deserialize payload with {requested_backend}/{codec}"
        ) from exc


def _write_path(path: Path, data: bytes, atomic: bool) -> None:
    # Internal helper: write path.
    """Internal helper: write path."""
    if not atomic:
        path.write_bytes(data)
        return
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as stream:
            temporary = stream.name
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def dump(
    obj: Any,
    file: Writable,
    *,
    compression: str | None = None,
    level: int = 5,
    protocol: int | None = None,
    backend: str = "auto",
    fallback: bool = True,
    atomic: bool = True,
) -> None:
    """Serialize *obj* to a path or an open binary stream.

    Paths are replaced atomically by default. Supplied streams are never closed.
    """
    data = dumps(
        obj,
        compression=compression,
        level=level,
        protocol=protocol,
        backend=backend,
        fallback=fallback,
    )
    if isinstance(file, str | os.PathLike):
        _write_path(Path(file), data, atomic)
        return
    if not hasattr(file, "write"):
        raise TypeError("file must be a path or a writable binary stream")
    try:
        written = file.write(data)
    except TypeError as exc:
        raise TypeError("file must be opened in binary mode") from exc
    if written is not None and written != len(data):
        raise OSError(f"short write: expected {len(data)} bytes, wrote {written}")


def load(
    file: Readable,
    *,
    compression: str | None = None,
    backend: str = "auto",
) -> Any:
    """Deserialize one object from a path or an open binary stream."""
    if isinstance(file, str | os.PathLike):
        data = Path(file).read_bytes()
    else:
        if not hasattr(file, "read"):
            raise TypeError("file must be a path or a readable binary stream")
        data = file.read()
    if not isinstance(data, bytes | bytearray | memoryview):
        raise TypeError("file must be opened in binary mode")
    return loads(data, compression=compression, backend=backend)


save = dump


@dataclass(frozen=True, slots=True)
class Serializer:
    """Immutable, reusable serializer configuration with a fluent API.

    Configuration calls return a new instance, so a base configuration can be
    safely shared between threads. ``dump`` returns the configured instance to
    make repeated writes chainable.
    """

    compression: str | None = None
    level: int = 5
    protocol: int | None = None
    backend: str = "auto"
    fallback: bool = True
    atomic_writes: bool = True

    CNAME_BLOSCLZ: ClassVar[str] = "blosclz"
    CNAME_LZ4: ClassVar[str] = "lz4"
    CNAME_LZ4HC: ClassVar[str] = "lz4hc"
    CNAME_ZLIB: ClassVar[str] = "zlib"
    CNAME_ZSTD: ClassVar[str] = "zstd"
    CNAME_GZIP: ClassVar[str] = "gzip"
    CNAME_BZ2: ClassVar[str] = "bz2"
    CNAME_ZIP: ClassVar[str] = "zip"
    CNAME_LZMA: ClassVar[str] = "lzma"
    CNAME_SNAPPY: ClassVar[str] = "snappy"
    CNAME_DEFAULT: ClassVar[None] = None
    CLEVEL_DEFAULT: ClassVar[int] = 5

    def __post_init__(self) -> None:
        """Implement `__post_init__`.

        Returns:
            TODO describe return value.

        """
        normalize_compression(self.compression)
        validate_level(self.level)
        if self.backend not in {"auto", "dill", "pickle"}:
            raise ValueError("backend must be 'auto', 'dill', or 'pickle'")
        if self.protocol is not None and (
            isinstance(self.protocol, bool) or not isinstance(self.protocol, int)
        ):
            raise TypeError("protocol must be an integer or None")

    def using(self, compression: str | None) -> Serializer:
        """Return a copy configured with a compression codec."""
        normalize_compression(compression)
        return replace(self, compression=compression)

    def at_level(self, level: int) -> Serializer:
        """Return a copy configured with compression level 0..9."""
        validate_level(level)
        return replace(self, level=level)

    def with_backend(self, backend: str) -> Serializer:
        """Select ``auto`` (dill first), ``dill``, or ``pickle``."""
        return replace(self, backend=backend)

    def with_protocol(self, protocol: int | None) -> Serializer:
        """With protocol.

        Args:
            protocol: TODO describe protocol.

        Returns:
            TODO describe return value.

        """
        return replace(self, protocol=protocol)

    def strict(self, enabled: bool = True) -> Serializer:
        """Disable dependency fallbacks when *enabled* is true."""
        return replace(self, fallback=not enabled)

    def atomic(self, enabled: bool = True) -> Serializer:
        """Atomic.

        Args:
            enabled: TODO describe enabled.

        Returns:
            TODO describe return value.

        """
        return replace(self, atomic_writes=enabled)

    def dumps(self, obj: Any) -> bytes:
        """Dumps.

        Args:
            obj: TODO describe obj.

        Returns:
            TODO describe return value.

        """
        return dumps(
            obj,
            compression=self.compression,
            level=self.level,
            protocol=self.protocol,
            backend=self.backend,
            fallback=self.fallback,
        )

    def loads(self, data: bytes | bytearray | memoryview) -> Any:
        """Loads.

        Args:
            data: TODO describe data.

        Returns:
            TODO describe return value.

        """
        return loads(data, compression=self.compression, backend=self.backend)

    def dump(self, obj: Any, file: Writable) -> Serializer:
        """Dump.

        Args:
            obj: TODO describe obj.
            file: TODO describe file.

        Returns:
            TODO describe return value.

        """
        dump(
            obj,
            file,
            compression=self.compression,
            level=self.level,
            protocol=self.protocol,
            backend=self.backend,
            fallback=self.fallback,
            atomic=self.atomic_writes,
        )
        return self

    save = dump

    def load(self, file: Readable) -> Any:
        """Load.

        Args:
            file: TODO describe file.

        Returns:
            TODO describe return value.

        """
        return load(file, compression=self.compression, backend=self.backend)
