"""Lazy serializer and compression backend loading."""

from __future__ import annotations

import io
import warnings
from importlib import import_module
from typing import Any, Final

from .exceptions import DependencyWarning, MissingDependencyError

BACKEND_IDS: Final = {"pickle": 1, "dill": 2}
BACKENDS_BY_ID: Final = {value: key for key, value in BACKEND_IDS.items()}

COMPRESSION_IDS: Final = {
    "none": 0,
    "gzip": 1,
    "bz2": 2,
    "lzma": 3,
    "zlib": 4,
    "zip": 5,
    "zstd": 6,
    "lz4": 7,
    "snappy": 8,
    "blosclz": 9,
    "lz4hc": 10,
    "blosc-zlib": 11,
    "blosc-zstd": 12,
}
COMPRESSIONS_BY_ID: Final = {value: key for key, value in COMPRESSION_IDS.items()}

_ALIASES: Final = {
    "": "none",
    "none": "none",
    "raw": "none",
    "gz": "gzip",
    "gzip": "gzip",
    "bz2": "bz2",
    "bzip2": "bz2",
    "lzma": "lzma",
    "xz": "lzma",
    "zlib": "zlib",
    "deflate": "zlib",
    "zip": "zip",
    "zstd": "zstd",
    "zstandard": "zstd",
    "lz4": "lz4",
    "snappy": "snappy",
    "blosc": "blosclz",
    "blosclz": "blosclz",
    "lz4hc": "lz4hc",
    "blosc-zlib": "blosc-zlib",
    "blosc-zstd": "blosc-zstd",
    "auto": "auto",
}


def normalize_compression(name: str | None) -> str:
    """Return the canonical compression name and validate it."""
    if name is None:
        return "none"
    if not isinstance(name, str):
        raise TypeError("compression must be a string or None")
    try:
        return _ALIASES[name.strip().lower()]
    except KeyError as exc:
        choices = ", ".join(sorted(COMPRESSION_IDS))
        raise ValueError(
            f"unsupported compression {name!r}; choose one of: {choices}, auto"
        ) from exc


def validate_level(level: int) -> None:
    """Validate level.

    Args:
        level: TODO describe level.

    Returns:
        TODO describe return value.

    """
    if isinstance(level, bool) or not isinstance(level, int):
        raise TypeError("level must be an integer")
    if not 0 <= level <= 9:
        raise ValueError("level must be between 0 and 9")


def _as_bytes(value: Any, feature: str) -> bytes:
    """Validate the bytes-like contract of a dynamically loaded backend."""
    # Internal helper: as bytes.
    if not isinstance(value, bytes | bytearray | memoryview):
        raise TypeError(f"{feature} returned {type(value).__name__}, expected bytes-like data")
    return bytes(value)


def _missing_dependency(feature: str, package: str, fallback: bool) -> None:
    # Internal helper: missing dependency.
    """Internal helper: missing dependency."""
    action = "using the safe default fallback" if fallback else "no fallback is permitted"
    warnings.warn(
        f"{package!r} is not installed; {feature} is unavailable, {action}.",
        DependencyWarning,
        stacklevel=3,
    )
    if not fallback:
        raise MissingDependencyError(
            f"Install ga-serializer[compression] (or {package}) to use {feature}."
        )


def _optional_module(module_name: str, feature: str, fallback: bool) -> Any | None:
    # Internal helper: optional module.
    """Internal helper: optional module."""
    try:
        return import_module(module_name)
    except ModuleNotFoundError as exc:
        # Do not hide a broken installation whose own transitive import failed.
        if exc.name != module_name and not module_name.startswith(f"{exc.name}."):
            raise
        _missing_dependency(feature, module_name.split(".", 1)[0], fallback)
        return None


def serializer_backend(requested: str = "auto", *, fallback: bool = True) -> tuple[Any, str]:
    """Resolve dill/pickle only when serialization is actually requested."""
    if not isinstance(requested, str):
        raise TypeError("backend must be 'auto', 'dill', or 'pickle'")
    requested = requested.strip().lower()
    if requested not in {"auto", "dill", "pickle"}:
        raise ValueError("backend must be 'auto', 'dill', or 'pickle'")

    if requested in {"auto", "dill"}:
        module = _optional_module("dill", "dill serialization", fallback)
        if module is not None:
            return module, "dill"
        if requested == "dill" and not fallback:  # pragma: no cover - raised above
            raise MissingDependencyError("dill is required")

    return import_module("pickle"), "pickle"


def compress(data: bytes, name: str | None, level: int, *, fallback: bool) -> tuple[bytes, str]:
    """Compress bytes and return both data and the codec actually used."""
    validate_level(level)
    codec = normalize_compression(name)

    if codec == "auto":
        try:
            zstandard = import_module("zstandard")
        except ModuleNotFoundError as exc:
            if exc.name != "zstandard":
                raise
        else:
            compressed = zstandard.ZstdCompressor(level=max(1, level)).compress(data)
            return _as_bytes(compressed, "zstd compression"), "zstd"
        codec = "gzip"

    if codec == "none":
        return data, codec
    if codec == "gzip":
        compressed = import_module("gzip").compress(data, compresslevel=level)
        return _as_bytes(compressed, "gzip compression"), codec
    if codec == "bz2":
        compressed = import_module("bz2").compress(data, compresslevel=max(1, level))
        return _as_bytes(compressed, "bz2 compression"), codec
    if codec == "lzma":
        compressed = import_module("lzma").compress(data, preset=level)
        return _as_bytes(compressed, "lzma compression"), codec
    if codec == "zlib":
        compressed = import_module("zlib").compress(data, level=level)
        return _as_bytes(compressed, "zlib compression"), codec
    if codec == "zip":
        zipfile = import_module("zipfile")
        buffer = io.BytesIO()
        with zipfile.ZipFile(
            buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=level
        ) as archive:
            archive.writestr("payload", data)
        return buffer.getvalue(), codec

    module_name = {
        "zstd": "zstandard",
        "lz4": "lz4.frame",
        "snappy": "snappy",
        "blosclz": "blosc",
        "lz4hc": "blosc",
        "blosc-zlib": "blosc",
        "blosc-zstd": "blosc",
    }[codec]
    module = _optional_module(module_name, f"{codec} compression", fallback)
    if module is None:
        return data, "none"

    if codec == "zstd":
        compressed = module.ZstdCompressor(level=max(1, level)).compress(data)
        return _as_bytes(compressed, "zstd compression"), codec
    if codec == "lz4":
        compressed = module.compress(data, compression_level=level)
        return _as_bytes(compressed, "lz4 compression"), codec
    if codec == "snappy":
        compressed = module.compress(data)
        return _as_bytes(compressed, "snappy compression"), codec

    cname = {
        "blosclz": "blosclz",
        "lz4hc": "lz4hc",
        "blosc-zlib": "zlib",
        "blosc-zstd": "zstd",
    }[codec]
    compressed = module.compress(data, typesize=1, cname=cname, clevel=level)
    return _as_bytes(compressed, f"{codec} compression"), codec


def decompress(data: bytes, codec: str) -> bytes:
    """Decompress bytes. Missing decode dependencies never silently corrupt data."""
    codec = normalize_compression(codec)
    if codec == "auto":
        raise ValueError("'auto' cannot be used to decode a legacy payload")
    if codec == "none":
        return data
    if codec == "gzip":
        return _as_bytes(import_module("gzip").decompress(data), "gzip decompression")
    if codec == "bz2":
        return _as_bytes(import_module("bz2").decompress(data), "bz2 decompression")
    if codec == "lzma":
        return _as_bytes(import_module("lzma").decompress(data), "lzma decompression")
    if codec == "zlib":
        return _as_bytes(import_module("zlib").decompress(data), "zlib decompression")
    if codec == "zip":
        zipfile = import_module("zipfile")
        with zipfile.ZipFile(io.BytesIO(data), "r") as archive:
            names = archive.namelist()
            if names != ["payload"]:
                raise ValueError("invalid serializer zip payload")
            return _as_bytes(archive.read("payload"), "zip decompression")

    module_name = {
        "zstd": "zstandard",
        "lz4": "lz4.frame",
        "snappy": "snappy",
        "blosclz": "blosc",
        "lz4hc": "blosc",
        "blosc-zlib": "blosc",
        "blosc-zstd": "blosc",
    }[codec]
    module = _optional_module(module_name, f"{codec} decompression", False)
    assert module is not None  # _optional_module raises when fallback=False
    if codec == "zstd":
        decompressed = module.ZstdDecompressor().decompress(data)
        return _as_bytes(decompressed, "zstd decompression")
    if codec in {"lz4", "snappy"}:
        return _as_bytes(module.decompress(data), f"{codec} decompression")
    return _as_bytes(module.decompress(data), f"{codec} decompression")
