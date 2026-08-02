from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.config import (
    CATEGORY_FOLDERS,
    DATA_DIR,
    DUPLICATE_REVIEW_FOLDER,
    LOGS_DIR,
    MAX_PREVIEW_ITEMS,
)
from app.organizer.file_classifier import get_category
from app.organizer.scanner import FileInfo
from app.utils.file_utils import same_file
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class FileOperation:

    source: Path
    destination: Path
    category: str


@dataclass(frozen=True)
class OperationPlan:

    root: Path
    operations: list[FileOperation]

    def __bool__(self) -> bool:
        return bool(self.operations)


class OperationPlanner:

    def __init__(self, root: Path, include_subfolder_files: bool = False) -> None:
        self._root = Path(root).resolve()
        self._include_subfolder_files = include_subfolder_files

    def build_plan(self, files: list[FileInfo]) -> OperationPlan:
        operations: list[FileOperation] = []
        for info in files:
            operation = self._plan_for_file(info)
            if operation is not None:
                operations.append(operation)

        logger.info(
            "Planner produced %d operation(s) for %s",
            len(operations),
            self._root,
        )
        return OperationPlan(root=self._root, operations=operations)

    def _plan_for_file(self, info: FileInfo) -> FileOperation | None:
        source = info.path

        if self._is_application_file(source):
            return None

        if not self._include_subfolder_files and self._is_already_organized(
            source
        ):
            return None

        if self._is_inside_duplicate_review(source):
            return None

        category = get_category(source.name)
        destination = self._destination_for(source, category)

        if same_file(source, destination):
            return None

        return FileOperation(
            source=source,
            destination=destination,
            category=category,
        )

    def _destination_for(self, source: Path, category: str) -> Path:
        return self._root / category / source.name

    def _is_application_file(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except OSError:
            return False
        resolved_str = str(resolved).lower()
        if str(DATA_DIR.resolve()).lower() in resolved_str:
            return True
        if str(LOGS_DIR.resolve()).lower() in resolved_str:
            return True
        return False

    def _is_already_organized(self, path: Path) -> bool:
        parts = path.parts
        return any(part in CATEGORY_FOLDERS for part in parts)

    def _is_inside_duplicate_review(self, path: Path) -> bool:
        return DUPLICATE_REVIEW_FOLDER in path.parts


def format_plan(plan: OperationPlan) -> str:
    lines: list[str] = ["Planned operations:", ""]
    operations = plan.operations
    shown = operations[:MAX_PREVIEW_ITEMS]

    for index, operation in enumerate(shown, start=1):
        lines.append(f"{index}. {operation.source.name}")
        lines.append(f"   From: {operation.source}")
        lines.append(f"   To:   {operation.destination}")
        lines.append("")

    if len(operations) > len(shown):
        lines.append(f"... and {len(operations) - len(shown)} more.")
        lines.append("")

    lines.append(f"Total files to move: {len(operations)}")
    return "\n".join(lines)
