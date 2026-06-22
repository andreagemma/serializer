"""Benchmark every serializer compression codec and level.

The final pivot table is printed to stdout as Markdown. Progress and diagnostic
messages are written to stderr so stdout can be redirected to a report file.
"""

from __future__ import annotations

import argparse
import gc
import sys
from collections.abc import Sequence
from numbers import Real
from statistics import median
from time import perf_counter
from typing import Any

import serializer
from serializer._backends import COMPRESSION_IDS, normalize_compression

DEFAULT_CODECS = tuple(COMPRESSION_IDS)
DEFAULT_LEVELS = tuple(range(10))


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_codecs(value: str) -> tuple[str, ...]:
    if value.strip().lower() == "all":
        return DEFAULT_CODECS

    codecs: list[str] = []
    for item in value.split(","):
        try:
            codec = normalize_compression(item)
        except (TypeError, ValueError) as exc:
            raise argparse.ArgumentTypeError(str(exc)) from exc
        if codec == "auto":
            raise argparse.ArgumentTypeError(
                "'auto' is a strategy, not a concrete codec; use 'all' instead"
            )
        if codec not in codecs:
            codecs.append(codec)
    if not codecs:
        raise argparse.ArgumentTypeError("at least one codec is required")
    return tuple(codecs)


def parse_levels(value: str) -> tuple[int, ...]:
    if value.strip().lower() == "all":
        return DEFAULT_LEVELS

    levels: list[int] = []
    for item in value.split(","):
        try:
            level = int(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"invalid compression level: {item!r}") from exc
        if not 0 <= level <= 9:
            raise argparse.ArgumentTypeError("compression levels must be between 0 and 9")
        if level not in levels:
            levels.append(level)
    if not levels:
        raise argparse.ArgumentTypeError("at least one compression level is required")
    return tuple(levels)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark serializer codecs and print a codec-by-level Markdown pivot table."
        )
    )
    parser.add_argument("--rows", type=positive_integer, default=1_000_000)
    parser.add_argument("--columns", type=positive_integer, default=10)
    parser.add_argument("--repeats", type=positive_integer, default=3)
    parser.add_argument(
        "--backend",
        choices=("auto", "dill", "pickle"),
        default="pickle",
        help="serialization backend used for every measurement (default: pickle)",
    )
    parser.add_argument(
        "--codecs",
        type=parse_codecs,
        default=DEFAULT_CODECS,
        metavar="LIST",
        help="comma-separated codecs or 'all' (default: all)",
    )
    parser.add_argument(
        "--levels",
        type=parse_levels,
        default=DEFAULT_LEVELS,
        metavar="LIST",
        help="comma-separated levels from 0 to 9 or 'all' (default: all)",
    )
    return parser


def create_dataframe(pandas: Any, rows: int, columns: int) -> Any:
    data = {
        f"column_{column + 1}": range(column, rows + column)
        for column in range(columns)
    }
    return pandas.DataFrame(data)


def format_cell(value: Any) -> str:
    if isinstance(value, Real):
        numeric = float(value)
        if numeric != numeric:  # NaN
            return "N/A"
        return f"{numeric:.4f}"
    return str(value)


def pivot_to_markdown(pivot: Any, levels: Sequence[int]) -> str:
    headers = ["codec / level (seconds)", *(str(level) for level in levels)]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---", *("---:" for _ in levels)]) + " |",
    ]
    for codec, row in pivot.iterrows():
        values = [str(codec), *(format_cell(row[level]) for level in levels)]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def run_benchmark(
    pandas: Any,
    dataframe: Any,
    codecs: Sequence[str],
    levels: Sequence[int],
    repeats: int,
    backend: str,
) -> tuple[Any, bool]:
    records: list[dict[str, str | int | float]] = []
    unavailable: set[str] = set()
    had_errors = False
    total = len(codecs) * len(levels)
    current = 0

    for codec in codecs:
        for level in levels:
            current += 1
            print(f"[{current:>3}/{total}] {codec:<11} level {level}", file=sys.stderr)

            if codec in unavailable:
                result: str | float = "N/A"
            else:
                samples: list[float] = []
                try:
                    for _ in range(repeats):
                        gc.collect()
                        started = perf_counter()
                        payload = serializer.dumps(
                            dataframe,
                            compression=codec,
                            level=level,
                            backend=backend,
                            fallback=False,
                        )
                        samples.append(perf_counter() - started)
                        del payload
                    result = median(samples)
                except serializer.MissingDependencyError as exc:
                    unavailable.add(codec)
                    result = "N/A"
                    print(f"      unavailable: {exc}", file=sys.stderr)
                except Exception as exc:  # keep the complete matrix on codec errors
                    had_errors = True
                    result = "ERR"
                    print(f"      error: {type(exc).__name__}: {exc}", file=sys.stderr)

            records.append({"codec": codec, "level": level, "seconds": result})

    results = pandas.DataFrame.from_records(records)
    pivot = results.pivot(index="codec", columns="level", values="seconds")
    pivot = pivot.reindex(index=codecs, columns=levels)
    return pivot, had_errors


def main() -> int:
    args = build_parser().parse_args()
    try:
        import pandas
    except ModuleNotFoundError:
        print(
            'pandas is required; install it with: pip install "ga-serializer[benchmark]"',
            file=sys.stderr,
        )
        return 2

    print(
        f"Building DataFrame: {args.rows:,} rows x {args.columns} columns",
        file=sys.stderr,
    )
    dataframe = create_dataframe(pandas, args.rows, args.columns)
    pivot, had_errors = run_benchmark(
        pandas,
        dataframe,
        args.codecs,
        args.levels,
        args.repeats,
        args.backend,
    )
    print(pivot_to_markdown(pivot, args.levels))
    return int(had_errors)


if __name__ == "__main__":
    raise SystemExit(main())
