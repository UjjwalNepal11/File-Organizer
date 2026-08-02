from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.database import Database
from app.organizer.operation_preview import OperationPlanner
from app.organizer.organizer import Organizer, create_category_folders
from app.organizer.scanner import scan_directory

class OrganizerTestCase(unittest.TestCase):

    def setUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self._temp_dir.name)
        self.root.mkdir(parents=True, exist_ok=True)

        self._db_dir = tempfile.TemporaryDirectory()
        self._db_file = Path(self._db_dir.name) / "test_history.db"
        self.database = Database(self._db_file)

    def tearDown(self) -> None:
        self.database.close()
        self._temp_dir.cleanup()
        self._db_dir.cleanup()

    def _make_file(self, path: Path, content: str = "data") -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _build_plan(self, include_subfolder: bool = False):
        files = scan_directory(self.root, recursive=True)
        planner = OperationPlanner(
            root=self.root, include_subfolder_files=include_subfolder
        )
        return planner.build_plan(files)

class TestOperationPlanner(OrganizerTestCase):

    def test_generates_correct_plan(self) -> None:
        self._make_file(self.root / "photo.jpg")
        self._make_file(self.root / "notes.pdf")

        plan = self._build_plan()
        self.assertEqual(len(plan.operations), 2)

        destinations = {op.destination.name for op in plan.operations}
        self.assertEqual(destinations, {"photo.jpg", "notes.pdf"})

        by_name = {op.source.name: op for op in plan.operations}
        self.assertEqual(
            by_name["photo.jpg"].destination.parent.name, "Images"
        )
        self.assertEqual(
            by_name["notes.pdf"].destination.parent.name, "Documents"
        )

    def test_does_not_plan_files_already_in_category_folder(self) -> None:
        self._make_file(self.root / "Images" / "photo.jpg")
        self._make_file(self.root / "loose.txt")

        plan = self._build_plan()
        self.assertEqual(len(plan.operations), 1)
        self.assertEqual(plan.operations[0].source.name, "loose.txt")

    def test_include_subfolder_files_flag(self) -> None:
        from app.organizer.scanner import FileInfo

        file_in_documents = FileInfo(
            path=(self.root / "Documents" / "photo.jpg").resolve(),
            name="photo.jpg",
            extension="jpg",
            size=10,
            modified=0.0,
        )

        default_planner = OperationPlanner(root=self.root)
        default = default_planner.build_plan([file_in_documents])
        self.assertEqual(len(default.operations), 0)

        include_planner = OperationPlanner(
            root=self.root, include_subfolder_files=True
        )
        include = include_planner.build_plan([file_in_documents])
        self.assertEqual(len(include.operations), 1)

        self.assertEqual(
            include.operations[0].destination,
            self.root / "Images" / "photo.jpg",
        )

    def test_empty_plan_for_empty_directory(self) -> None:
        plan = self._build_plan()
        self.assertFalse(plan)

    def test_does_not_plan_application_files(self) -> None:
        self._make_file(self.root / "data" / "file_organizer.db")
        self._make_file(self.root / "logs" / "file_organizer.log")

        plan = self._build_plan()
        self.assertFalse(plan)

class TestOrganizer(OrganizerTestCase):

    def test_creates_category_folders(self) -> None:
        create_category_folders(self.root)
        for category in ("Images", "Documents", "Videos", "Other"):
            self.assertTrue((self.root / category).is_dir())

    def test_moves_files_after_confirmation(self) -> None:
        self._make_file(self.root / "photo.jpg")
        self._make_file(self.root / "notes.txt")
        plan = self._build_plan()

        organizer = Organizer(database=self.database, confirm=lambda plan: True)
        performed = organizer.execute(plan)

        self.assertEqual(len(performed), 2)
        self.assertTrue((self.root / "Images" / "photo.jpg").exists())
        self.assertTrue((self.root / "Documents" / "notes.txt").exists())
        self.assertFalse((self.root / "photo.jpg").exists())

    def test_confirmation_declined_does_nothing(self) -> None:
        self._make_file(self.root / "photo.jpg")
        plan = self._build_plan()

        organizer = Organizer(database=self.database, confirm=lambda plan: False)
        performed = organizer.execute(plan)

        self.assertEqual(performed, [])
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertFalse((self.root / "Images" / "photo.jpg").exists())

    def test_does_not_overwrite_existing_files(self) -> None:
        self._make_file(self.root / "photo.jpg", content="original")
        (self.root / "Images").mkdir()
        self._make_file(self.root / "Images" / "photo.jpg", content="keep me")

        plan = self._build_plan()
        organizer = Organizer(database=self.database, confirm=lambda plan: True)
        performed = organizer.execute(plan)

        self.assertEqual(len(performed), 1)
        self.assertTrue((self.root / "Images" / "photo.jpg").exists())

        self.assertTrue((self.root / "Images" / "photo (1).jpg").exists())

    def test_generates_unique_destination_names(self) -> None:
        self._make_file(self.root / "photo.jpg")
        (self.root / "Images").mkdir()
        self._make_file(self.root / "Images" / "photo.jpg")
        self._make_file(self.root / "Images" / "photo (1).jpg")

        plan = self._build_plan()
        organizer = Organizer(database=self.database, confirm=lambda plan: True)
        performed = organizer.execute(plan)

        self.assertEqual(len(performed), 1)
        self.assertTrue((self.root / "Images" / "photo (2).jpg").exists())

    def test_dry_run_does_not_move_files(self) -> None:
        self._make_file(self.root / "photo.jpg")
        plan = self._build_plan()

        self.assertTrue(plan)
        self.assertTrue((self.root / "photo.jpg").exists())
        self.assertFalse((self.root / "Images" / "photo.jpg").exists())

    def test_organizer_records_history(self) -> None:
        self._make_file(self.root / "photo.jpg")
        plan = self._build_plan()
        organizer = Organizer(database=self.database, confirm=lambda plan: True)
        organizer.execute(plan)

        rows = self.database.get_all_operations()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["operation_type"], "ORGANIZE")
        self.assertEqual(rows[0]["status"], "SUCCESS")

if __name__ == "__main__":
    unittest.main()
