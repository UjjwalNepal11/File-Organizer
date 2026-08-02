from __future__ import annotations

from pathlib import Path

from app.config import EXTENSION_MAPPING


_EXTENSION_LOOKUP: dict[str, str] = {
    ext: category
    for category, extensions in EXTENSION_MAPPING.items()
    for ext in extensions
}


_OTHER = "Other"


def get_category(filename: str) -> str:
    suffix = Path(filename).suffix
    if not suffix:
        return _OTHER
    return _EXTENSION_LOOKUP.get(suffix.lstrip(".").lower(), _OTHER)
