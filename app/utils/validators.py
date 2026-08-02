from __future__ import annotations

import hashlib
from pathlib import Path


def validate_directory(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.exists():
        raise ValueError(f"Directory does not exist: {candidate}")
    if not candidate.is_dir():
        raise ValueError(f"Path is not a directory: {candidate}")
    return candidate.resolve()


def validate_hash_algorithm(algorithm: str | None) -> str:
    if algorithm is None:
        return "sha256"
    normalized = algorithm.lower()
    if normalized not in hashlib.algorithms_available:
        available = ", ".join(sorted(hashlib.algorithms_available))
        raise ValueError(
            f"Invalid hash algorithm: {algorithm!r}. "
            f"Available algorithms: {available}"
        )
    return normalized


def validate_choice(value: str, count: int) -> str | int:
    normalized = value.strip().lower()
    if normalized == "s":
        return "s"
    try:
        index = int(normalized)
    except ValueError as exc:
        raise ValueError(
            f"Invalid selection {value!r}. "
            f"Enter a number between 1 and {count}, or 'S' to skip."
        ) from exc
    if not 1 <= index <= count:
        raise ValueError(
            f"Invalid selection {value!r}. "
            f"Enter a number between 1 and {count}, or 'S' to skip."
        )
    return index
