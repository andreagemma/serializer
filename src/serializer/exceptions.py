"""Public exceptions and warnings raised by :mod:`serializer`."""


class SerializerError(Exception):
    """Base class for serializer-specific errors."""


class SerializationError(SerializerError):
    """An object could not be serialized or deserialized."""


class FormatError(SerializationError):
    """Serialized data is malformed, truncated, or unsupported."""


class MissingDependencyError(SerializerError, ImportError):
    """A dependency required to decode data is unavailable."""


class SerializerWarning(UserWarning):
    """Base class for warnings emitted by serializer."""


class DependencyWarning(SerializerWarning):
    """An optional dependency is unavailable and a fallback may be used."""
