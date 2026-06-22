"""Serialize Python objects with lazy backends and optional compression.

Do not deserialize data from untrusted sources: dill and pickle payloads may
execute arbitrary code while loading.
"""

from ._api import Serializer, dump, dumps, load, loads, save
from .exceptions import (
    DependencyWarning,
    FormatError,
    MissingDependencyError,
    SerializationError,
    SerializerError,
    SerializerWarning,
)

__version__ = "0.1.0"

__all__ = [
    "DependencyWarning",
    "FormatError",
    "MissingDependencyError",
    "SerializationError",
    "Serializer",
    "SerializerError",
    "SerializerWarning",
    "__version__",
    "dump",
    "dumps",
    "load",
    "loads",
    "save",
]
