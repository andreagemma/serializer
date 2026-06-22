"""Serialize Python objects with lazy backends and optional compression.

Do not deserialize data from untrusted sources: dill and pickle payloads may
execute arbitrary code while loading.
"""

from ._api import Serializer, dump, dumps, load, loads, save
from ._version import __version__
from .benchmark import COMPRESSION_CODECS, BenchmarkResult, benchmark
from .exceptions import (
    DependencyWarning,
    FormatError,
    MissingDependencyError,
    SerializationError,
    SerializerError,
    SerializerWarning,
)

__all__ = [
    "BenchmarkResult",
    "COMPRESSION_CODECS",
    "DependencyWarning",
    "FormatError",
    "MissingDependencyError",
    "SerializationError",
    "Serializer",
    "SerializerError",
    "SerializerWarning",
    "__version__",
    "benchmark",
    "dump",
    "dumps",
    "load",
    "loads",
    "save",
]
