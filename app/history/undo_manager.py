from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from app.database import Database, new_batch_id
from app.utils.file_utils import generate_unique_path
from app.utils.logger import get_logger

logger = get_logger(__name__)

ConfirmCallback = Callable[[str], bool]


@dataclass(frozen=True)
class ReverseOperation:

    current: Path
    original: Path


class UndoManager:

    def __init__(
        self,
        database: Database,
        confirm: ConfirmCallback | None = None,
    ) -> None:
        self._database = database
        self._confirm = confirm or self._default_confirm

    def build_reverse_operations(self, batch_id: str) -> list[ReverseOperation]:
        rows = self._database.get_batch_operations(batch_id)
        reverse: list[ReverseOperation] = []

        for row in rows:
            if row["status"] != "SUCCESS":
                continue
            if row["operation_type"] not in ("ORGANIZE", "DUPLICATE_REVIEW"):
                continue
            current = Path(row["destination_path"])
            original = Path(row["source_path"])
            if current == original:
                continue
            reverse.append(ReverseOperation(current=current, original=original))

        reverse.reverse()
        return reverse

    def preview(self, operations: Sequence[ReverseOperation]) -> str:
        lines = ["Undo preview:", ""]
        for index, operation in enumerate(operations, start=1):
            lines.append(f"{index}. Move:")
            lines.append(f"   {operation.current}")
            lines.append("")
            lines.append("   Back to:")
            lines.append(f"   {operation.original}")
            lines.append("")
        lines.append(f"Total files to restore: {len(operations)}")
        return "\n".join(lines)

    def run_interactive(self, force_yes: bool = False) -> int:
        batch_id = self._database.get_latest_successful_batch()
        if batch_id is None:
            print("Nothing to undo — no successful operation found.")
            return 0

        operations = self.build_reverse_operations(batch_id)
        if not operations:
            print("The latest operation batch has nothing reversible.")
            return 0

        print(self.preview(operations))

        if not force_yes:
            print("\nContinue with undo? [y/N]: ", end="", flush=True)
            try:
                response = input().strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\nUndo cancelled.")
                return 0
            if response not in ("y", "yes"):
                print("Undo cancelled.")
                return 0

        return self.execute(operations)

    def execute(
        self,
        operations: Sequence[ReverseOperation],
        batch_id: str | None = None,
    ) -> int:
        restored = 0
        failed = 0
        undo_batch_id = batch_id or new_batch_id()

        for operation in operations:
            if self._try_restore(operation, undo_batch_id):
                restored += 1
            else:
                failed += 1

        print(
            f"\nUndo complete: {restored} file(s) restored, "
            f"{failed} failed."
        )
        return 1 if failed and restored == 0 else 0

    def _try_restore(
        self,
        operation: ReverseOperation,
        batch_id: str,
    ) -> bool:
        current = operation.current
        original = operation.original

        if not current.exists():
            self._warn_missing(current, "destination file is missing")
            self._record_undo(
                operation,
                success=False,
                error="File missing",
                batch_id=batch_id,
            )
            return False

        if original.exists():
            final_original = generate_unique_path(original)
            logger.info(
                "Original location occupied; restoring to %s", final_original
            )
        else:
            final_original = original

        try:
            final_original.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(final_original))
        except PermissionError as exc:
            self._warn_missing(current, f"permission denied: {exc}")
            self._record_undo(
                operation,
                success=False,
                error=str(exc),
                batch_id=batch_id,
            )
            return False
        except OSError as exc:
            self._warn_missing(current, f"move failed: {exc}")
            self._record_undo(
                operation,
                success=False,
                error=str(exc),
                batch_id=batch_id,
            )
            return False

        logger.info("Restored %s -> %s", current, final_original)
        self._record_undo(
            operation,
            success=True,
            destination=final_original,
            batch_id=batch_id,
        )
        return True

    def _record_undo(
        self,
        operation: ReverseOperation,
        success: bool,
        error: str | None = None,
        destination: Path | None = None,
        batch_id: str | None = None,
    ) -> None:
        try:
            self._database.record_operation(
                operation_type="UNDO",
                source_path=operation.current,
                destination_path=destination or operation.original,
                status="SUCCESS" if success else "FAILED",
                error_message=error,
                batch_id=batch_id,
            )
        except Exception as exc:
            logger.error("Could not record undo operation: %s", exc)

    @staticmethod
    def _warn_missing(path: Path, reason: str) -> None:
        logger.warning(
            "Could not undo:\n%s\nReason: %s\n"
            "The application will continue with the remaining operations.",
            path,
            reason,
        )
        print(f"Warning: Could not undo {path}\nReason: {reason}")

    @staticmethod
    def _default_confirm(prompt: str) -> bool:
        try:
            response = input(prompt).strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return False
        return response in ("y", "yes")
