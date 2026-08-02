from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from app.duplicates.hash_calculator import HashCalculator, HashError

class TestHashCalculator(unittest.TestCase):

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def _make_file(self, content: bytes | str) -> Path:
        path = self.root / "sample.bin"
        if isinstance(content, str):
            content = content.encode("utf-8")
        path.write_bytes(content)
        return path

    def test_produces_correct_sha256_hash(self) -> None:
        content = b"hello world"
        path = self._make_file(content)

        calculator = HashCalculator(algorithm="sha256")
        expected = hashlib.sha256(content).hexdigest()

        self.assertEqual(calculator.hash_file(path), expected)

    def test_algorithm_property(self) -> None:
        calculator = HashCalculator(algorithm="md5")
        self.assertEqual(calculator.algorithm, "md5")

    def test_reads_large_files_in_chunks(self) -> None:

        chunk = b"x" * (1024 * 1024)
        content = chunk * 3
        path = self._make_file(content)

        calculator = HashCalculator(algorithm="sha256", chunk_size=1024 * 1024)
        expected = hashlib.sha256(content).hexdigest()

        self.assertEqual(calculator.hash_file(path), expected)

    def test_empty_file_hash(self) -> None:
        path = self._make_file(b"")
        calculator = HashCalculator(algorithm="sha256")
        self.assertEqual(
            calculator.hash_file(path),
            hashlib.sha256(b"").hexdigest(),
        )

    def test_missing_file_raises(self) -> None:
        calculator = HashCalculator(algorithm="sha256")
        missing = self.root / "missing.bin"
        with self.assertRaises(FileNotFoundError):
            calculator.hash_file(missing)

    def test_invalid_algorithm_raises(self) -> None:
        with self.assertRaises(ValueError):
            HashCalculator(algorithm="not-a-real-algorithm")

    def test_file_changed_while_hashing_raises_hash_error(self) -> None:
        from unittest import mock

        path = self._make_file(b"0123456789")

        calculator = HashCalculator(algorithm="sha256")

        with mock.patch.object(
            type(path), "stat", return_value=mock.Mock(st_size=10)
        ), mock.patch.object(
            type(path), "open"
        ) as mock_open:
            context = mock_open.return_value.__enter__.return_value
            context.read.side_effect = [b"012", b""]
            with self.assertRaises(HashError):
                calculator.hash_file(path)

if __name__ == "__main__":
    unittest.main()
