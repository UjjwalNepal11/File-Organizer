from __future__ import annotations

from pathlib import Path

APP_NAME = "File Organizer and Duplicate Finder"
APP_VERSION = "1.0.0"

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = _PROJECT_ROOT / "data"
LOGS_DIR = _PROJECT_ROOT / "logs"
DATABASE_PATH = DATA_DIR / "file_organizer.db"
LOG_FILE_PATH = LOGS_DIR / "file_organizer.log"

DEFAULT_HASH_ALGORITHM = "sha256"
HASH_CHUNK_SIZE = 1024 * 1024

EXTENSION_MAPPING: dict[str, tuple[str, ...]] = {
    "Images": (
        "jpg", "jpeg", "png", "gif", "webp", "svg", "bmp",
        "tiff", "tif", "ico", "heic", "raw", "psd",
    ),
    "Documents": (
        "pdf", "doc", "docx", "txt", "rtf", "odt", "md",
        "epub", "tex", "pages",
    ),
    "Videos": (
        "mp4", "mkv", "avi", "mov", "webm", "flv", "wmv",
        "m4v", "mpg", "mpeg", "3gp",
    ),
    "Audio": (
        "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a",
        "opus", "aiff",
    ),
    "Archives": (
        "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "tgz",
        "tbz2", "iso",
    ),
    "Programs": (
        "exe", "msi", "app", "deb", "rpm", "bat", "cmd",
        "sh", "apk", "dmg",
    ),
    "Code": (
        "py", "js", "ts", "jsx", "tsx", "html", "css", "java",
        "cpp", "c", "h", "hpp", "cs", "go", "rs", "rb", "php",
        "swift", "kt", "sql", "json", "yaml", "yml", "xml",
        "toml", "ini", "vue", "sass", "scss", "lua", "pl", "r",
    ),
    "Spreadsheets": (
        "xls", "xlsx", "ods", "csv", "tsv",
    ),
    "Presentations": (
        "ppt", "pptx", "odp", "key",
    ),
    "Other": (),
}

CATEGORY_ORDER: tuple[str, ...] = tuple(EXTENSION_MAPPING.keys())

CATEGORY_FOLDERS: tuple[str, ...] = tuple(EXTENSION_MAPPING.keys())

DUPLICATE_REVIEW_FOLDER = "Duplicate_Review"

IGNORED_FOLDER_NAMES: frozenset[str] = frozenset(
    {
        *CATEGORY_FOLDERS,
        DUPLICATE_REVIEW_FOLDER,
        "data",
        "logs",
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
    }
)

MAX_PREVIEW_ITEMS = 50
