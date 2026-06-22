from __future__ import annotations

import warnings
from unittest.mock import patch

import serializer


def test_benchmark_returns_markdown_matrix() -> None:
    result = serializer.benchmark(
        {"items": list(range(100))},
        codecs=("none", "gzip"),
        levels=(0, 1),
        repeats=1,
        backend="pickle",
    )

    assert result.codecs == ("none", "gzip")
    assert result.levels == (0, 1)
    assert isinstance(result.value("gzip", 1), float)
    assert "| gzip |" in result.to_markdown()


def test_benchmark_marks_missing_codec_with_x() -> None:
    from serializer import _backends

    real_import = _backends.import_module

    def without_zstandard(name: str):
        if name == "zstandard":
            error = ModuleNotFoundError("No module named 'zstandard'")
            error.name = "zstandard"
            raise error
        return real_import(name)

    with patch(
        "serializer._backends.import_module", side_effect=without_zstandard
    ), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = serializer.benchmark(
            {"value": 1},
            codecs=("zstd",),
            levels=(0, 1),
            repeats=1,
            backend="pickle",
        )

    assert result.values == (("x", "x"),)
    assert "| zstd | x | x |" in result.to_markdown()
