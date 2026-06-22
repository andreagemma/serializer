from __future__ import annotations

import importlib.util
import io
import pickle
import tempfile
import unittest
import warnings
from pathlib import Path
from unittest.mock import patch

import serializer


class SerializerTests(unittest.TestCase):
    def test_round_trip_builtin_compressions(self) -> None:
        value = {"items": list(range(100)), "nested": (None, True, b"bytes")}
        for codec in (None, "gzip", "bz2", "lzma", "zlib", "zip"):
            with self.subTest(codec=codec):
                payload = serializer.dumps(value, compression=codec, backend="pickle")
                self.assertEqual(serializer.loads(payload), value)

    def test_none_is_a_valid_object(self) -> None:
        self.assertIsNone(serializer.loads(serializer.dumps(None, backend="pickle")))

    def test_paths_and_streams(self) -> None:
        value = ["stream", 42]
        stream = io.BytesIO()
        serializer.dump(value, stream, compression="gzip", backend="pickle")
        self.assertFalse(stream.closed)
        stream.seek(0)
        self.assertEqual(serializer.load(stream), value)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "value.srl")
            serializer.dump(value, path, backend="pickle")
            self.assertEqual(serializer.load(path), value)

    def test_fluent_configuration_is_immutable_and_dump_chains(self) -> None:
        base = serializer.Serializer(backend="pickle")
        codec = base.using("gzip").at_level(7).atomic()
        self.assertIsNone(base.compression)
        self.assertEqual(codec.compression, "gzip")

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory, "first.srl")
            second = Path(directory, "second.srl")
            returned = codec.dump({"n": 1}, first).dump({"n": 2}, second)
            self.assertIs(returned, codec)
            self.assertEqual(codec.load(first), {"n": 1})
            self.assertEqual(codec.load(second), {"n": 2})

    def test_corruption_and_truncation_are_detected(self) -> None:
        payload = serializer.dumps({"safe": True}, backend="pickle")
        with self.assertRaises(serializer.FormatError):
            serializer.loads(payload[:-1])
        corrupted = payload[:-1] + bytes([payload[-1] ^ 0xFF])
        with self.assertRaises(serializer.FormatError):
            serializer.loads(corrupted)

    def test_legacy_raw_pickle(self) -> None:
        old_payload = pickle.dumps({"legacy": True})
        self.assertEqual(
            serializer.loads(old_payload, compression=None, backend="pickle"),
            {"legacy": True},
        )

    def test_missing_dill_warns_and_falls_back_to_pickle(self) -> None:
        from serializer import _backends

        real_import = _backends.import_module

        def without_dill(name: str):
            if name == "dill":
                error = ModuleNotFoundError("No module named 'dill'")
                error.name = "dill"
                raise error
            return real_import(name)

        with patch(
            "serializer._backends.import_module", side_effect=without_dill
        ), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            payload = serializer.dumps({"fallback": True})
        self.assertTrue(
            any(issubclass(item.category, serializer.DependencyWarning) for item in caught)
        )
        self.assertEqual(serializer.loads(payload), {"fallback": True})

    def test_missing_optional_compressor_falls_back_or_is_strict(self) -> None:
        from serializer import _backends

        real_import = _backends.import_module

        def without_zstd(name: str):
            if name == "zstandard":
                error = ModuleNotFoundError("No module named 'zstandard'")
                error.name = "zstandard"
                raise error
            return real_import(name)

        with patch("serializer._backends.import_module", side_effect=without_zstd):
            with self.assertWarns(serializer.DependencyWarning):
                payload = serializer.dumps(
                    "fallback", compression="zstd", backend="pickle"
                )
            self.assertEqual(serializer.loads(payload), "fallback")
            with self.assertWarns(serializer.DependencyWarning), self.assertRaises(
                serializer.MissingDependencyError
            ):
                serializer.dumps(
                    "strict", compression="zstd", backend="pickle", fallback=False
                )

            from serializer._format import pack

            impossible_to_decode = pack(b"compressed", "pickle", "zstd")
            with self.assertWarns(serializer.DependencyWarning), self.assertRaises(
                serializer.MissingDependencyError
            ):
                serializer.loads(impossible_to_decode)

    @unittest.skipUnless(importlib.util.find_spec("dill"), "dill is not installed")
    def test_dill_serializes_a_closure(self) -> None:
        offset = 40

        def add(value: int) -> int:
            return offset + value

        restored = serializer.loads(serializer.dumps(add))
        self.assertEqual(restored(2), 42)

    def test_rejects_bad_arguments_and_text_streams(self) -> None:
        with self.assertRaises(ValueError):
            serializer.dumps(1, level=10, backend="pickle")
        with self.assertRaises(ValueError):
            serializer.dumps(1, compression="imaginary", backend="pickle")
        with self.assertRaises(TypeError):
            serializer.loads("not bytes")  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            serializer.dump(1, io.StringIO(), backend="pickle")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
