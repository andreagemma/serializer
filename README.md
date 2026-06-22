# ga-serializer

[![CI](https://github.com/andreagemma/serializer/actions/workflows/ci.yml/badge.svg)](https://github.com/andreagemma/serializer/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/ga-serializer.svg)](https://pypi.org/project/ga-serializer/)
[![Python](https://img.shields.io/pypi/pyversions/ga-serializer.svg)](https://pypi.org/project/ga-serializer/)

Robust Python object serialization with lazy backends, optional compression, and a
self-describing binary format.

`ga-serializer` uses `dill` by default to support a broad range of Python objects.
If `dill` is unavailable, it emits a warning and falls back to the standard-library
`pickle` module.

## Installation

```bash
pip install ga-serializer
```

Install all optional compression backends with:

```bash
pip install "ga-serializer[compression]"
```

The distribution is named `ga-serializer`; the Python package is imported as
`serializer`.

## Quick start

```python
import serializer

data = {"items": [1, 2, 3], "enabled": True}

payload = serializer.dumps(data, compression="gzip", level=7)
restored = serializer.loads(payload)

serializer.dump(data, "state.srl", compression="lzma")
restored_from_file = serializer.load("state.srl")
```

Serialized envelopes record the backend and compression codec, so `loads()` and
`load()` do not require those parameters when reading data created by this library.

## Binary streams

`dump()` and `load()` accept filesystem paths or open binary streams. User-provided
streams are never closed.

```python
from io import BytesIO

import serializer

stream = BytesIO()
serializer.dump([1, 2, 3], stream, compression="zlib")

stream.seek(0)
assert serializer.load(stream) == [1, 2, 3]
```

## Fluent configuration

`Serializer` is an immutable, reusable configuration object. Configuration methods
return a new instance, while `dump()` returns the current instance to support chained
writes.

```python
from serializer import Serializer

codec = (
    Serializer()
    .using("gzip")
    .at_level(9)
    .with_backend("auto")
    .atomic()
)

codec.dump({"id": 1}, "one.srl").dump({"id": 2}, "two.srl")
assert codec.load("one.srl") == {"id": 1}
```

Call `.strict()` to disable dependency fallbacks. The functional API provides the
equivalent `fallback=False` argument.

## Compression

The following codecs are always available:

- `gzip`, `bz2`, `lzma`, `zlib`, and `zip`
- `None` or `"none"` for no compression
- `"auto"` to prefer Zstandard and otherwise use gzip

Optional codecs are imported only when requested:

| Codec | Dependency |
| --- | --- |
| `zstd` | `zstandard` |
| `lz4` | `lz4` |
| `snappy` | `python-snappy` |
| `blosclz`, `lz4hc`, `blosc-zlib`, `blosc-zstd` | `blosc` |

When an explicitly requested optional compressor is unavailable during serialization,
the default behavior emits `DependencyWarning` and writes an uncompressed envelope.
Deserialization never pretends that compressed data is uncompressed: a missing decoder
raises `MissingDependencyError`.

## Legacy payloads

Headerless pickle or dill payloads remain supported when their original settings are
provided explicitly:

```python
value = serializer.loads(
    legacy_payload,
    compression="gzip",
    backend="pickle",
)
```

## Security

> [!WARNING]
> `pickle` and `dill` may execute arbitrary code during deserialization. Never load
> data from an untrusted or unauthenticated source. CRC32 detects accidental corruption;
> it does not provide cryptographic authenticity.

## Benchmarking

Use the public API to benchmark every codec and compression level on any serializable
Python object. The result contains median end-to-end times and renders directly as a
Markdown pivot table:

```python
import serializer

result = serializer.benchmark(
    my_object,
    repeats=3,
    codecs=("gzip", "zstd", "lz4"),  # None benchmarks every codec
    levels=range(10),
)

print(result.to_markdown())
```

Unavailable codecs are displayed as `x`; unexpected codec failures are displayed as
`ERR` and listed in `result.errors`.

The included script applies this API to a DataFrame containing 10 integer columns and
1,000,000 rows:

```bash
python -m pip install -e ".[benchmark,compression]"
python benchmarks/benchmark_codecs.py
```

Progress is written to stderr and the final pivot table to stdout as Markdown. This
makes it possible to save a clean report with:

```bash
python benchmarks/benchmark_codecs.py > benchmark-results.md
```

Use `--help` to change the dataset size, repetitions, backend, codecs, or levels.
Missing optional dependencies are never replaced by uncompressed fallback timings.

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest
python -m build
twine check dist/*
```

Released under the [MIT License](LICENSE).
