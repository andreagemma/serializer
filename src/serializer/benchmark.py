"""Reusable performance benchmarks for serializer compression codecs."""

from __future__ import annotations

import gc
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from statistics import median
from time import perf_counter
from typing import Any, Final, Literal

from ._api import dumps
from ._backends import COMPRESSION_IDS, normalize_compression, serializer_backend, validate_level
from .exceptions import MissingDependencyError

MISSING_CODEC: Final = "x"
BENCHMARK_ERROR: Final = "ERR"
COMPRESSION_CODECS: Final = tuple(COMPRESSION_IDS)

BenchmarkValue = float | Literal["x", "ERR"]
BenchmarkSize = int | Literal["x", "ERR"]
ProgressCallback = Callable[[int, int, str, int], None]


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Immutable codec-by-level benchmark matrix.

    ``values`` contains median elapsed seconds and ``sizes`` contains median
    serialized envelope sizes in bytes. ``x`` identifies an unavailable codec,
    while ``ERR`` identifies a codec that failed for another reason.
    """

    codecs: tuple[str, ...]
    levels: tuple[int, ...]
    values: tuple[tuple[BenchmarkValue, ...], ...]
    sizes: tuple[tuple[BenchmarkSize, ...], ...]
    repeats: int
    backend: str
    errors: tuple[str, ...] = ()

    def value(self, codec: str, level: int) -> BenchmarkValue:
        """Return one measured value by codec and compression level."""
        try:
            codec_index = self.codecs.index(codec)
            level_index = self.levels.index(level)
        except ValueError as exc:
            raise KeyError((codec, level)) from exc
        return self.values[codec_index][level_index]

    def size(self, codec: str, level: int) -> BenchmarkSize:
        """Return the serialized envelope size in bytes for one matrix cell."""
        try:
            codec_index = self.codecs.index(codec)
            level_index = self.levels.index(level)
        except ValueError as exc:
            raise KeyError((codec, level)) from exc
        return self.sizes[codec_index][level_index]

    def _table_to_markdown(
        self,
        label: str,
        matrix: Sequence[Sequence[BenchmarkValue | BenchmarkSize]],
        precision: int,
    ) -> str:
        headers = [label, *(str(level) for level in self.levels)]
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join(["---", *("---:" for _ in self.levels)]) + " |",
        ]
        for codec, row in zip(self.codecs, matrix, strict=True):
            formatted = [
                f"{value:.{precision}f}" if isinstance(value, float) else str(value)
                for value in row
            ]
            lines.append("| " + " | ".join([codec, *formatted]) + " |")
        return "\n".join(lines)

    def to_markdown(self, *, precision: int = 4) -> str:
        """Render timing and size matrices as Markdown pivot tables."""
        if isinstance(precision, bool) or not isinstance(precision, int):
            raise TypeError("precision must be an integer")
        if precision < 0:
            raise ValueError("precision must not be negative")

        timings = self._table_to_markdown(
            "codec / level (seconds)", self.values, precision
        )
        sizes = self._table_to_markdown("codec / level (bytes)", self.sizes, precision)
        return f"### Time\n\n{timings}\n\n### Serialized size\n\n{sizes}"

    def __str__(self) -> str:
        return self.to_markdown()


def _normalize_codecs(codecs: Iterable[str | None] | None) -> tuple[str, ...]:
    if codecs is None:
        return COMPRESSION_CODECS

    normalized: list[str] = []
    for value in codecs:
        codec = normalize_compression(value)
        if codec == "auto":
            raise ValueError("'auto' is a strategy, not a concrete benchmark codec")
        if codec not in normalized:
            normalized.append(codec)
    if not normalized:
        raise ValueError("at least one codec is required")
    return tuple(normalized)


def _normalize_levels(levels: Iterable[int]) -> tuple[int, ...]:
    normalized: list[int] = []
    for level in levels:
        validate_level(level)
        if level not in normalized:
            normalized.append(level)
    if not normalized:
        raise ValueError("at least one compression level is required")
    return tuple(normalized)


def benchmark(
    obj: Any,
    *,
    codecs: Iterable[str | None] | None = None,
    levels: Iterable[int] = range(10),
    repeats: int = 3,
    backend: str = "auto",
    protocol: int | None = None,
    progress: ProgressCallback | None = None,
) -> BenchmarkResult:
    """Benchmark serialization and compression of any supported Python object.

    Each cell contains the median end-to-end elapsed time in seconds. Optional
    codecs are tested strictly: when their dependency is unavailable, all cells
    for that codec contain ``x`` instead of timing an uncompressed fallback.
    Other codec failures are recorded as ``ERR`` and described in ``errors``.
    """
    if isinstance(repeats, bool) or not isinstance(repeats, int):
        raise TypeError("repeats must be an integer")
    if repeats < 1:
        raise ValueError("repeats must be greater than zero")

    selected_codecs = _normalize_codecs(codecs)
    selected_levels = _normalize_levels(levels)
    _, resolved_backend = serializer_backend(backend, fallback=True)

    # Validate object/backend compatibility before starting the timed matrix.
    dumps(
        obj,
        compression=None,
        protocol=protocol,
        backend=resolved_backend,
        fallback=False,
    )

    unavailable: set[str] = set()
    errors: list[str] = []
    time_matrix: list[tuple[BenchmarkValue, ...]] = []
    size_matrix: list[tuple[BenchmarkSize, ...]] = []
    current = 0
    total = len(selected_codecs) * len(selected_levels)

    for codec in selected_codecs:
        time_row: list[BenchmarkValue] = []
        size_row: list[BenchmarkSize] = []
        for level in selected_levels:
            current += 1
            if progress is not None:
                progress(current, total, codec, level)

            if codec in unavailable:
                time_row.append(MISSING_CODEC)
                size_row.append(MISSING_CODEC)
                continue

            time_samples: list[float] = []
            size_samples: list[int] = []
            try:
                for _ in range(repeats):
                    gc.collect()
                    started = perf_counter()
                    payload = dumps(
                        obj,
                        compression=codec,
                        level=level,
                        protocol=protocol,
                        backend=resolved_backend,
                        fallback=False,
                    )
                    time_samples.append(perf_counter() - started)
                    size_samples.append(len(payload))
                    del payload
            except MissingDependencyError:
                unavailable.add(codec)
                time_row.append(MISSING_CODEC)
                size_row.append(MISSING_CODEC)
            except Exception as exc:  # preserve the complete matrix for comparison
                time_row.append(BENCHMARK_ERROR)
                size_row.append(BENCHMARK_ERROR)
                errors.append(f"{codec} level {level}: {type(exc).__name__}: {exc}")
            else:
                time_row.append(median(time_samples))
                size_row.append(int(median(size_samples)))
        time_matrix.append(tuple(time_row))
        size_matrix.append(tuple(size_row))

    return BenchmarkResult(
        codecs=selected_codecs,
        levels=selected_levels,
        values=tuple(time_matrix),
        sizes=tuple(size_matrix),
        repeats=repeats,
        backend=resolved_backend,
        errors=tuple(errors),
    )
