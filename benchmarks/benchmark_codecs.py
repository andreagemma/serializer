"""Benchmark every serializer compression codec and level on a DataFrame."""

from __future__ import annotations

import argparse
import sys
from typing import Any

import serializer

DEFAULT_LEVELS = tuple(range(10))


def positive_integer(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return parsed


def parse_codecs(value: str) -> tuple[str, ...]:
    if value.strip().lower() == "all":
        return serializer.COMPRESSION_CODECS
    codecs = tuple(dict.fromkeys(item.strip().lower() for item in value.split(",") if item))
    unknown = set(codecs).difference(serializer.COMPRESSION_CODECS)
    if unknown:
        raise argparse.ArgumentTypeError(f"unknown codecs: {', '.join(sorted(unknown))}")
    if not codecs:
        raise argparse.ArgumentTypeError("at least one codec is required")
    return codecs


def parse_levels(value: str) -> tuple[int, ...]:
    if value.strip().lower() == "all":
        return DEFAULT_LEVELS
    try:
        levels = tuple(dict.fromkeys(int(item) for item in value.split(",")))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("levels must be comma-separated integers") from exc
    if not levels or any(not 0 <= level <= 9 for level in levels):
        raise argparse.ArgumentTypeError("levels must be between 0 and 9")
    return levels


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
        "--backend", choices=("auto", "dill", "pickle"), default="pickle"
    )
    parser.add_argument(
        "--codecs", type=parse_codecs, default=serializer.COMPRESSION_CODECS, metavar="LIST"
    )
    parser.add_argument("--levels", type=parse_levels, default=DEFAULT_LEVELS, metavar="LIST")
    return parser


def create_dataframe(pandas: Any, rows: int, columns: int) -> Any:
    data = {
        f"column_{column + 1}": range(column, rows + column)
        for column in range(columns)
    }
    return pandas.DataFrame(data)


def show_progress(current: int, total: int, codec: str, level: int) -> None:
    print(f"[{current:>3}/{total}] {codec:<11} level {level}", file=sys.stderr)


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
    result = serializer.benchmark(
        dataframe,
        codecs=args.codecs,
        levels=args.levels,
        repeats=args.repeats,
        backend=args.backend,
        progress=show_progress,
    )
    for error in result.errors:
        print(f"error: {error}", file=sys.stderr)
    print(result.to_markdown())
    return int(bool(result.errors))


if __name__ == "__main__":
    raise SystemExit(main())
