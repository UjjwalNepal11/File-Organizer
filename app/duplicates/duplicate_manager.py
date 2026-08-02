from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from app.config import DUPLICATE_REVIEW_FOLDER
from app.database import Database, new_batch_id
from app.duplicates.duplicate_finder import DuplicateGroup
from app.utils.file_utils import generate_unique_path
from app.utils.logger import get_logger
from app.utils.validators import validate_choice

logger = get_logger(__name__)

ConfirmCallback = Callable[[str], bool]


class DuplicateReviewer:

    def __init__(
        self,
        database: Database,
        dry_run: bool = False,
        confirm_callback: ConfirmCallback | None = None,
    ) -> None:
        self._database = database
        self._dry_run = dry_run
        self._confirm = confirm_callback or self._default_confirm

    def review_groups(
        self, groups: list[DuplicateGroup], root: Path
    ) -> dict[str, int]:
        root = Path(root)
        summary = {"moved": 0, "skipped": 0}
        batch_id = new_batch_id()

        for group_index, group in enumerate(groups, start=1):
            print(f"\nDuplicate Group {group_index}")
            self._display_group(group)

            if self._dry_run:
                print(
                    "[DRY RUN] Would ask you to choose a file to keep here."
                )
                summary["skipped"] += 1
                continue

            choice = self._ask_choice(len(group.files))
            if choice == "s":
                print(f"Skipped group {group_index}.")
                summary["skipped"] += 1
                continue

            keeper = group.files[choice - 1]
            print(f"Keeping: {keeper.path}")

            review_dir = root / DUPLICATE_REVIEW_FOLDER
            moved = self._move_others(group, keeper, review_dir, batch_id)
            summary["moved"] += moved

        return summary

    @staticmethod
    def _display_group(group: DuplicateGroup) -> None:
        for index, info in enumerate(group.files, start=1):
            print(f"[{index}] {info.path}")

    @staticmethod
    def _default_confirm(prompt: str) -> bool:
        try:
            response = input(prompt).strip().lower()
        except EOFError:
            return False
        except KeyboardInterrupt:
            print()
            return False
        return response in ("y", "yes")

    def _ask_choice(self, count: int) -> str | int:
        prompt = (
            "\nChoose the file to keep:\n"
            f"Enter 1, 2, ... {count}, or S to skip: "
        )
        while True:
            try:
                raw = input(prompt)
            except EOFError:
                print("\nNo input available — skipping group.")
                return "s"
            except KeyboardInterrupt:
                print("\nSkipping group.")
                return "s"
            try:
                return validate_choice(raw, count)
            except ValueError as exc:
                print(f"  {exc}")

    def _move_others(
        self,
        group: DuplicateGroup,
        keeper: object,
        review_dir: Path,
        batch_id: str,
    ) -> int:
        moved = 0
        for info in group.files:
            if info is keeper:
                continue

            source = info.path
            destination = review_dir / source.name
            try:
                destination.parent.mkdir(parents=True, exist_ok=True)
                final_destination = generate_unique_path(destination)
                shutil.move(str(source), str(final_destination))
            except FileNotFoundError:
                logger.warning(
                    "File disappeared during review: %s", source
                )
                continue
            except PermissionError as exc:
                logger.warning(
                    "Permission denied moving %s: %s", source, exc
                )
                continue
            except OSError as exc:
                logger.warning("Could not move %s: %s", source, exc)
                continue

            self._record_move(source, final_destination, batch_id)
            print(f"  Moved duplicate to: {final_destination}")
            moved += 1
        return moved

    def _record_move(
        self, source: Path, destination: Path, batch_id: str
    ) -> None:
        try:
            self._database.record_operation(
                operation_type="DUPLICATE_REVIEW",
                source_path=source,
                destination_path=destination,
                batch_id=batch_id,
            )
        except Exception as exc:
            logger.error("Could not record duplicate review move: %s", exc)
