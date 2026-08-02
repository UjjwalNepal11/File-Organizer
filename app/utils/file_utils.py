from __future__ import annotations

from pathlib import Path


def human_readable_size(size_bytes: int) -> str:
    size = float(max(size_bytes, 0))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size_bytes} B"


def generate_unique_path(destination: Path) -> Path:
    if not destination.exists():
        return destination

    parent = destination.parent
    stem = destination.stem
    suffix = destination.suffix

    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def same_file(file_a: Path, file_b: Path) -> bool:
    try:
        return file_a.resolve() == file_b.resolve()
    except OSError:

        return str(file_a) == str(file_b)
