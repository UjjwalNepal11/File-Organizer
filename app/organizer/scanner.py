from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.config import IGNORED_FOLDER_NAMES
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class FileInfo:

    path: Path
    name: str
    extension: str
    size: int
    modified: float


class Scanner:

    def __init__(
        self,
        include_hidden: bool = False,
        ignore_folders: Iterable[str] | None = None,
    ) -> None:
        self._include_hidden = include_hidden
        self._ignore_folders = IGNORED_FOLDER_NAMES.union(
            set(ignore_folders or ())
        )

    def scan(self, directory: Path) -> list[FileInfo]:
        root = Path(directory)
        if not root.exists():
            raise FileNotFoundError(f"Directory does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {root}")
        if not os.access(root, os.R_OK | os.X_OK):
            raise PermissionError(f"Permission denied for directory: {root}")

        files: list[FileInfo] = []
        self._walk(root, files)
        logger.info("Scanned %s — found %d file(s)", root, len(files))
        return files

    def _walk(self, directory: Path, files: list[FileInfo]) -> None:
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name)
        except PermissionError as exc:
            self._warn_unreadable(directory, "Permission denied", exc)
            return
        except OSError as exc:
            self._warn_unreadable(directory, "Cannot list directory", exc)
            return

        for entry in entries:
            if self._should_skip(entry):
                continue

            try:
                if entry.is_symlink():
                    if entry.is_dir():
                        continue
                    self._collect_file(entry, files)
                elif entry.is_dir():
                    self._walk(entry, files)
                elif entry.is_file():
                    self._collect_file(entry, files)
            except PermissionError as exc:
                self._warn_unreadable(entry, "Permission denied", exc)
            except OSError as exc:
                self._warn_unreadable(entry, "Cannot access entry", exc)

    def _should_skip(self, entry: Path) -> bool:
        if entry.name in self._ignore_folders:
            return True
        if not self._include_hidden and entry.name.startswith("."):
            return True
        return False

    def _collect_file(self, entry: Path, files: list[FileInfo]) -> None:
        try:
            stat_result = entry.stat()
        except FileNotFoundError:
            logger.warning("File disappeared during scan: %s", entry)
            return
        except PermissionError as exc:
            self._warn_unreadable(entry, "Permission denied", exc)
            return
        except OSError as exc:
            self._warn_unreadable(entry, "Cannot stat file", exc)
            return

        if not stat.S_ISREG(stat_result.st_mode):
            return

        files.append(
            FileInfo(
                path=entry.resolve(),
                name=entry.name,
                extension=entry.suffix.lstrip(".").lower(),
                size=stat_result.st_size,
                modified=stat_result.st_mtime,
            )
        )

    @staticmethod
    def _warn_unreadable(entry: Path, reason: str, exc: Exception) -> None:
        logger.warning(
            "Could not access:\n%s\nReason: %s (%s)\n"
            "The application will continue with the remaining files.",
            entry,
            reason,
            exc,
        )


def scan_directory(
    directory: Path,
    recursive: bool = True,
    include_hidden: bool = False,
) -> list[FileInfo]:
    scanner = Scanner(include_hidden=include_hidden)
    all_files = scanner.scan(directory)
    if recursive:
        return all_files

    root = Path(directory).resolve()
    return [info for info in all_files if info.path.parent == root]
