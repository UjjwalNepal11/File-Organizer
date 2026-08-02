from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.duplicates.hash_calculator import HashCalculator, HashError
from app.organizer.scanner import FileInfo
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class DuplicateGroup:

    hash_value: str
    files: list[FileInfo]

    def __bool__(self) -> bool:
        return len(self.files) >= 2


class DuplicateFinder:

    def __init__(self, algorithm: str = "sha256") -> None:
        self._calculator = HashCalculator(algorithm=algorithm)

    def find_duplicates(self, files: list[FileInfo]) -> list[DuplicateGroup]:

        by_size: dict[int, list[FileInfo]] = {}
        for info in files:
            by_size.setdefault(info.size, []).append(info)

        candidates = [
            group for group in by_size.values() if len(group) >= 2
        ]

        by_hash: dict[str, list[FileInfo]] = {}
        for candidate_group in candidates:
            for info in candidate_group:
                try:
                    digest = self._calculator.hash_file(info.path)
                except FileNotFoundError:
                    logger.warning(
                        "File disappeared before hashing: %s", info.path
                    )
                    continue
                except PermissionError:
                    logger.warning("Permission denied while hashing: %s", info.path)
                    continue
                except HashError as exc:
                    logger.warning("Hashing failed for %s: %s", info.path, exc)
                    continue
                by_hash.setdefault(digest, []).append(info)

        groups = [
            DuplicateGroup(hash_value=digest, files=members)
            for digest, members in by_hash.items()
            if len(members) >= 2
        ]
        groups.sort(key=lambda group: group.files[0].size, reverse=True)

        logger.info("Found %d duplicate group(s).", len(groups))
        return groups


def group_recoverable_space(group: DuplicateGroup) -> int:
    if not group.files:
        return 0
    return (len(group.files) - 1) * group.files[0].size
