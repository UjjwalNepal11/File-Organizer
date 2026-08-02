from __future__ import annotations

import hashlib
from pathlib import Path

from app.config import HASH_CHUNK_SIZE
from app.utils.logger import get_logger

logger = get_logger(__name__)


class HashCalculator:

    def __init__(
        self,
        algorithm: str = "sha256",
        chunk_size: int = HASH_CHUNK_SIZE,
    ) -> None:
        if algorithm not in hashlib.algorithms_available:
            raise ValueError(
                f"Invalid hash algorithm: {algorithm!r}. "
                f"Available algorithms: {sorted(hashlib.algorithms_available)}"
            )
        self._algorithm = algorithm
        self._chunk_size = chunk_size

    @property
    def algorithm(self) -> str:
        return self._algorithm

    def hash_file(self, path: Path) -> str:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"File does not exist: {source}")

        hasher = hashlib.new(self._algorithm)
        original_size = source.stat().st_size
        bytes_read = 0

        try:
            with source.open("rb") as file_handle:
                while True:
                    chunk = file_handle.read(self._chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)
                    bytes_read += len(chunk)
        except PermissionError:
            raise
        except OSError as exc:
            raise HashError(f"Could not read file {source}: {exc}") from exc

        if bytes_read != original_size:
            raise HashError(
                f"File changed while being hashed (size mismatch): {source}"
            )

        return hasher.hexdigest()


class HashError(Exception):
    pass
