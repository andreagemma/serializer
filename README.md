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

codec = Serializer().using("gzip").at_level(9).with_backend("auto").atomic()

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
Python object. The result contains median end-to-end times and final serialized sizes
in bytes, and renders both matrices directly as Markdown pivot tables:

```python
import serializer

result = serializer.benchmark(
    my_object,
    repeats=3,
    codecs=("gzip", "zstd", "lz4"),  # None benchmarks every codec
    levels=range(10),
)

print(result.to_markdown())

gzip_time = result.value("gzip", 5)
gzip_size = result.size("gzip", 5)
```

`result.values` contains timing data and `result.sizes` contains total serialized
envelope sizes. Unavailable codecs are displayed as `x`; unexpected failures are
displayed as `ERR` and listed in `result.errors`.

The included script applies this API to a DataFrame containing 10 integer columns and
100,000 rows by default:

```bash
python -m pip install -e ".[benchmark,compression]"
python benchmarks/benchmark_codecs.py
```

Progress is written to stderr and the final pivot table to stdout as Markdown. This
makes it possible to save a clean report with:

```bash
python benchmarks/benchmark_codecs.py > benchmark-results.md
```

To run the benchmark and replace the results section below automatically:

```bash
python benchmarks/benchmark_codecs.py --update-readme
```

Use `--help` to change the dataset size, repetitions, backend, codecs, levels, or
README path. Missing dependencies are never replaced by uncompressed fallback data.

### Latest DataFrame benchmark

<!-- ga-serializer-benchmark:start -->

**Dataset:** `100,000 rows x 10 columns` | **Backend:** `pickle` | **Repetitions:** `3`

### Time

| codec / level (seconds) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| none | 0.0039 | 0.0040 | 0.0041 | 0.0041 | 0.0042 | 0.0039 | 0.0041 | 0.0043 | 0.0044 | 0.0046 |
| gzip | 0.0120 | 0.0337 | 0.0368 | 0.0638 | 0.0570 | 0.1013 | 0.3260 | 0.5520 | 1.5434 | 5.4007 |
| bz2 | 0.1992 | 0.2003 | 0.2013 | 0.2092 | 0.2212 | 0.2240 | 0.2322 | 0.2417 | 0.2412 | 0.2555 |
| lzma | 0.1019 | 0.0389 | 0.0454 | 0.0651 | 0.4757 | 0.6380 | 0.9451 | 0.9383 | 0.9787 | 0.9374 |
| zlib | 0.0096 | 0.0336 | 0.0362 | 0.0611 | 0.0571 | 0.1040 | 0.3232 | 0.5606 | 1.5711 | 5.5304 |
| zip | 0.0126 | 0.0363 | 0.0369 | 0.0626 | 0.0581 | 0.1059 | 0.3289 | 0.5636 | 1.5626 | 5.4964 |
| zstd | 0.0166 | 0.0165 | 0.0165 | 0.0053 | 0.0060 | 0.0072 | 0.0099 | 0.0130 | 0.0160 | 0.0177 |
| lz4 | 0.0112 | 0.0114 | 0.0113 | 0.0330 | 0.0368 | 0.0498 | 0.0713 | 0.1143 | 0.1785 | 0.2665 |
| snappy | 0.0108 | 0.0108 | 0.0106 | 0.0108 | 0.0106 | 0.0109 | 0.0166 | 0.0107 | 0.0108 | 0.0114 |
| blosclz | 0.0051 | 0.0064 | 0.0044 | 0.0043 | 0.0045 | 0.0044 | 0.0045 | 0.0046 | 0.0048 | 0.0050 |
| lz4hc | 0.0050 | 0.0058 | 0.0058 | 0.0082 | 0.0105 | 0.0136 | 0.0148 | 0.0223 | 0.0342 | 0.0432 |
| blosc-zlib | 0.0054 | 0.0072 | 0.0084 | 0.0118 | 0.0104 | 0.0186 | 0.0503 | 0.0792 | 0.2136 | 0.7219 |
| blosc-zstd | 0.0053 | 0.0045 | 0.0057 | 0.0078 | 0.0184 | 0.0323 | 0.0557 | 0.0409 | 0.0771 | 1.3535 |

### Serialized size

| codec / level (bytes) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| none | 8000977 | 8000977 | 8000977 | 8000977 | 8000977 | 8000977 | 8000977 | 8000977 | 8000977 | 8000977 |
| gzip | 8001610 | 1509620 | 1509994 | 1509985 | 1514837 | 1514665 | 1514659 | 1512915 | 1512788 | 1509239 |
| bz2 | 368429 | 368429 | 335724 | 358067 | 380663 | 404650 | 407180 | 413568 | 436529 | 461902 |
| lzma | 258168 | 28868 | 28868 | 28868 | 28896 | 28464 | 28464 | 28464 | 28464 | 28464 |
| zlib | 8001598 | 1509608 | 1509982 | 1509973 | 1514825 | 1514653 | 1514647 | 1512903 | 1512776 | 1509227 |
| zip | 8001709 | 1509714 | 1510088 | 1510079 | 1514931 | 1514759 | 1514753 | 1513009 | 1512882 | 1509333 |
| zstd | 1018755 | 1018755 | 1019109 | 143755 | 152306 | 176426 | 104291 | 104301 | 103118 | 103118 |
| lz4 | 4004283 | 4004283 | 4004283 | 4005016 | 4004902 | 4004592 | 4003985 | 4003984 | 4003984 | 4002601 |
| snappy | 4007189 | 4007189 | 4007189 | 4007189 | 4007189 | 4007189 | 4007189 | 4007189 | 4007189 | 4007189 |
| blosclz | 8000993 | 8000993 | 4003766 | 4000248 | 3999013 | 3999013 | 3998399 | 3998399 | 3998399 | 3999259 |
| lz4hc | 8000993 | 4003057 | 4003057 | 4004990 | 4004227 | 4003927 | 4003362 | 4003362 | 4003362 | 4002031 |
| blosc-zlib | 8000993 | 1513768 | 1514031 | 1512021 | 1515866 | 1515689 | 1515685 | 1513995 | 1513882 | 1510239 |
| blosc-zstd | 8000993 | 1032273 | 1085234 | 1137459 | 1024959 | 1022071 | 1022614 | 1022197 | 1022213 | 415175 |

<!-- ga-serializer-benchmark:end -->

## Development

```bash
python -m pip install -e ".[dev]"
ruff check .
mypy
pytest
python -m build
twine check dist/*
```

## Releasing

Update `__version__` in `src/serializer/_version.py`, then run the **Create release**
workflow from GitHub Actions. By default, it creates the tag `v<version>`, generates
the GitHub Release notes, and starts the build and PyPI publication workflow.

The workflow accepts an optional `tag` input when a different tag is required. Package
metadata reads the same `_version.py` value, so code and distribution versions cannot
drift.

Released under the [MIT License](LICENSE).
