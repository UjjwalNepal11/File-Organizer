from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database import Database
from app.history.undo_manager import UndoManager, ReverseOperation
from app.organizer.operation_preview import OperationPlanner
from app.organizer.organizer import Organizer, create_category_folders
from app.organizer.scanner import scan_directory

class UndoManagerTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.root.mkdir(parents=True, exist_ok=True)

        self._db_dir = tempfile.TemporaryDirectory()
        self._db_file = Path(self._db_dir.name) / "undo_history.db"
        self.database = Database(self._db_file)

    def tearDown(self) -> None:
        self.database.close()
        self._temp_dir.cleanup()
        self._db_dir.cleanup()

    def _make_file(self, path: Path, content: str = "data") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _organize(self) -> None:
        create_category_folders(self.root)
        files = scan_directory(self.root, recursive=True)
        planner = OperationPlanner(root=self.root)
        plan = planner.build_plan(files)
        organizer = Organizer(database=self.database, confirm=lambda plan: True)
        organizer.execute(plan)

    def _build_reverse(self) -> list[ReverseOperation]:
        manager = UndoManager(database=self.database)
        batch_id = self.database.get_latest_successful_batch()
        assert batch_id is not None
        return manager.build_reverse_operations(batch_id)

class TestUndoManager(UndoManagerTestCase):

    def test_restores_files_to_original_locations(self) -> None:
        self._make_file(self.root / "photo.jpg")
        self._make_file(self.root / "notes.txt")

        self._organize()
        self.assertTrue((self.root / "Images" / "photo.jpg").exists())
        self.assertTrue((self.root / "Documents" / "notes.txt").exists())

        manager = UndoManager(database=self.database)
        reverse = self._build_reverse()
        self.assertEqual(len(reverse), 2)

        exit_code = manager.execute(reverse)
        self.assertEqual(exit_code, 0)
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertTrue((self.root / "notes.txt").exists())
        self.assertFalse((self.root / "Images" / "photo.jpg").exists())

    def test_handles_filename_conflicts(self) -> None:
        self._make_file(self.root / "photo.jpg", content="original")
        self._organize()
        self.assertTrue((self.root / "Images" / "photo.jpg").exists())

        self._make_file(self.root / "photo.jpg", content="new occupant")

        manager = UndoManager(database=self.database)
        reverse = self._build_reverse()
        exit_code = manager.execute(reverse)

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertTrue((self.root / "photo (1).jpg").exists())

    def test_does_not_undo_unrelated_files(self) -> None:

        self.database.record_operation(
            operation_type="ORGANIZE",
            source_path=self.root / "unrelated.txt",
            destination_path=self.root / "Other" / "unrelated.txt",
        )

        self._make_file(self.root / "a.txt")
        self._organize()

        reverse = self._build_reverse()
        sources = {op.current for op in reverse}
        self.assertNotIn(self.root / "Other" / "unrelated.txt", sources)

    def test_missing_file_is_reported_and_continues(self) -> None:
        self._make_file(self.root / "a.txt")
        self._make_file(self.root / "b.txt")
        self._organize()

        organized = self.root / "Documents" / "b.txt"
        self.assertTrue(organized.exists())
        organized.unlink()

        manager = UndoManager(database=self.database)
        reverse = self._build_reverse()
        exit_code = manager.execute(reverse)

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.root / "a.txt").exists())

        self.assertFalse((self.root / "b.txt").exists())

    def test_preview_shows_reverse_operations(self) -> None:
        self._make_file(self.root / "photo.jpg")
        self._organize()

        manager = UndoManager(database=self.database)
        reverse = self._build_reverse()
        preview = manager.preview(reverse)

        self.assertIn("Undo preview:", preview)
        self.assertIn("photo.jpg", preview)
        self.assertIn("Total files to restore: 1", preview)

    def test_nothing_to_undo(self) -> None:
        manager = UndoManager(database=self.database)
        exit_code = manager.run_interactive(force_yes=True)
        self.assertEqual(exit_code, 0)

if __name__ == "__main__":
    unittest.main()
