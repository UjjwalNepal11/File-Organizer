from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.organizer.scanner import FileInfo, Scanner, scan_directory

class TestScanner(unittest.TestCase):

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.root.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def _make_file(self, path: Path, content: str = "data") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_scans_files_correctly(self) -> None:
        self._make_file(self.root / "a.txt")
        self._make_file(self.root / "b.jpg")

        files = scan_directory(self.root, recursive=True)
        self.assertEqual(len(files), 2)
        names = {info.name for info in files}
        self.assertEqual(names, {"a.txt", "b.jpg"})

    def test_ignores_directories(self) -> None:
        self._make_file(self.root / "a.txt")
        (self.root / "subdir").mkdir()

        files = scan_directory(self.root, recursive=True)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "a.txt")

    def test_recursive_scan(self) -> None:
        self._make_file(self.root / "a.txt")
        self._make_file(self.root / "sub" / "b.txt")
        self._make_file(self.root / "sub" / "deep" / "c.txt")

        recursive = scan_directory(self.root, recursive=True)
        self.assertEqual(len(recursive), 3)

        non_recursive = scan_directory(self.root, recursive=False)
        self.assertEqual(len(non_recursive), 1)

    def test_handles_empty_directory(self) -> None:
        files = scan_directory(self.root, recursive=True)
        self.assertEqual(files, [])

    def test_handles_invalid_path(self) -> None:
        missing = self.root / "does" / "not" / "exist"
        with self.assertRaises(FileNotFoundError):
            scan_directory(missing, recursive=True)

    def test_file_info_metadata(self) -> None:
        path = self._make_file(self.root / "photo.JPG", content="hello")
        files = scan_directory(self.root, recursive=True)
        self.assertEqual(len(files), 1)
        info = files[0]
        self.assertIsInstance(info, FileInfo)
        self.assertEqual(info.name, "photo.JPG")
        self.assertEqual(info.extension, "jpg")
        self.assertEqual(info.size, len("hello"))
        self.assertGreater(info.modified, 0)
        self.assertTrue(info.path.exists())

    def test_ignores_hidden_files_by_default(self) -> None:
        self._make_file(self.root / ".secret")
        self._make_file(self.root / "visible.txt")

        default = scan_directory(self.root, recursive=True)
        self.assertEqual(len(default), 1)
        self.assertEqual(default[0].name, "visible.txt")

        with_hidden = scan_directory(
            self.root, recursive=True, include_hidden=True
        )
        self.assertEqual(len(with_hidden), 2)

    def test_ignores_application_folders(self) -> None:
        self._make_file(self.root / "Documents" / "inside.pdf")
        self._make_file(self.root / "__pycache__" / "cache.pyc")
        self._make_file(self.root / "visible.txt")

        files = scan_directory(self.root, recursive=True)
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "visible.txt")

    def test_scanner_class_interface(self) -> None:
        self._make_file(self.root / "a.txt")
        scanner = Scanner()
        files = scanner.scan(self.root)
        self.assertEqual(len(files), 1)

if __name__ == "__main__":
    unittest.main()
