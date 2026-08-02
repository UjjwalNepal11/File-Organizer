from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.duplicates.duplicate_finder import (
    DuplicateFinder,
    group_recoverable_space,
)
from app.organizer.scanner import scan_directory

class DuplicateFinderTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)

    def tearDown(self) -> None:
        self._temp_dir.cleanup()

    def _make_file(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def _find_duplicates(self):
        files = scan_directory(self.root, recursive=True)
        finder = DuplicateFinder(algorithm="sha256")
        return finder.find_duplicates(files)

class TestDuplicateFinder(DuplicateFinderTestCase):

    def test_finds_identical_files(self) -> None:
        self._make_file("a.txt", "same content")
        self._make_file("b.txt", "same content")

        groups = self._find_duplicates()
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].files), 2)

    def test_does_not_mark_different_files_as_duplicates(self) -> None:
        self._make_file("a.txt", "content one")
        self._make_file("b.txt", "content two")

        groups = self._find_duplicates()
        self.assertEqual(groups, [])

    def test_groups_multiple_identical_files(self) -> None:
        self._make_file("a.txt", "same")
        self._make_file("b.txt", "same")
        self._make_file("c.txt", "same")

        groups = self._find_duplicates()
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].files), 3)

    def test_separates_distinct_groups(self) -> None:
        self._make_file("a.txt", "first group")
        self._make_file("b.txt", "first group")
        self._make_file("c.txt", "second group")
        self._make_file("d.txt", "second group")

        groups = self._find_duplicates()
        self.assertEqual(len(groups), 2)

    def test_single_file_is_not_duplicate(self) -> None:
        self._make_file("only.txt", "unique content")
        groups = self._find_duplicates()
        self.assertEqual(groups, [])

class TestRecoverableSpace(DuplicateFinderTestCase):

    def test_two_identical_files(self) -> None:
        self._make_file("a.txt", "data" * 100)
        self._make_file("b.txt", "data" * 100)

        groups = self._find_duplicates()
        self.assertEqual(len(groups), 1)
        group = groups[0]
        size = group.files[0].size

        self.assertEqual(group_recoverable_space(group), size)

    def test_three_identical_files(self) -> None:
        self._make_file("a.txt", "data" * 50)
        self._make_file("b.txt", "data" * 50)
        self._make_file("c.txt", "data" * 50)

        groups = self._find_duplicates()
        group = groups[0]
        size = group.files[0].size

        self.assertEqual(group_recoverable_space(group), 2 * size)
        self.assertNotEqual(group_recoverable_space(group), 3 * size)

    def test_empty_group_recoverable_space_is_zero(self) -> None:
        group = type("Group", (), {"files": []})()
        self.assertEqual(group_recoverable_space(group), 0)

if __name__ == "__main__":
    unittest.main()
