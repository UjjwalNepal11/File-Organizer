from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable

from app.config import CATEGORY_ORDER
from app.database import Database, new_batch_id
from app.organizer.operation_preview import FileOperation, OperationPlan
from app.utils.file_utils import generate_unique_path
from app.utils.logger import get_logger

logger = get_logger(__name__)

ConfirmCallback = Callable[[str], bool]

class Organizer:

    def __init__(
        self,
        database: Database,
        confirm: ConfirmCallback | None = None,
    ) -> None:
        self._database = database
        self._confirm = confirm

    def execute(self, plan: OperationPlan) -> list[FileOperation]:
        if not plan:
            logger.info("Nothing to organize — plan is empty.")
            return []

        if self._confirm is not None and not self._confirm(plan):
            logger.info("Organization cancelled by the user.")
            return []

        performed: list[FileOperation] = []
        batch_id = new_batch_id()
        for operation in plan.operations:
            result = self._execute_one(operation, batch_id=batch_id)
            if result is not None:
                performed.append(result)
        return performed

    def _execute_one(
        self,
        operation: FileOperation,
        batch_id: str,
    ) -> FileOperation | None:
        source = operation.source
        destination = operation.destination

        if not source.exists():
            self._record_failure(
                operation,
                error="Source file does not exist (deleted meanwhile).",
                batch_id=batch_id,
            )
            return None

        try:

            destination.parent.mkdir(parents=True, exist_ok=True)
            final_destination = generate_unique_path(destination)
            shutil.move(str(source), str(final_destination))
        except PermissionError as exc:
            self._record_failure(
                operation,
                error=f"Permission denied: {exc}",
                batch_id=batch_id,
            )
            return None
        except OSError as exc:
            self._record_failure(
                operation,
                error=f"Move failed: {exc}",
                batch_id=batch_id,
            )
            return None

        actual = FileOperation(
            source=source,
            destination=final_destination,
            category=operation.category,
        )
        try:
            self._database.record_operation(
                operation_type="ORGANIZE",
                source_path=source,
                destination_path=final_destination,
                batch_id=batch_id,
            )
        except Exception as exc:
            logger.error("Move succeeded but history record failed: %s", exc)

        logger.info("Moved %s -> %s", source, final_destination)
        return actual

    def _record_failure(
        self,
        operation: FileOperation,
        error: str,
        batch_id: str,
    ) -> None:
        logger.warning("Could not move %s: %s", operation.source, error)
        try:
            self._database.record_operation(
                operation_type="ORGANIZE",
                source_path=operation.source,
                destination_path=operation.destination,
                status="FAILED",
                error_message=error,
                batch_id=batch_id,
            )
        except Exception as exc:
            logger.error("Could not record failure in history: %s", exc)

def create_category_folders(root: Path) -> None:
    for category in CATEGORY_ORDER:
        folder = root / category
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.warning("Permission denied creating folder: %s", folder)
