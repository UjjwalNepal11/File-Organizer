from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence

from app.config import APP_NAME, APP_VERSION, DEFAULT_HASH_ALGORITHM

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="file-organizer",
        description=(
            f"{APP_NAME} — safely scan, organize and deduplicate your files "
            "from the terminal. Nothing is ever deleted; files are only moved "
            "after preview and confirmation."
        ),
        epilog=(
            "Examples:\n"
            "  python -m app.main scan \"PATH\"\n"
            "  python -m app.main organize \"PATH\" --dry-run\n"
            "  python -m app.main organize \"PATH\"\n"
            "  python -m app.main duplicates \"PATH\" --recursive\n"
            "  python -m app.main review-duplicates \"PATH\"\n"
            "  python -m app.main undo\n"
            "  python -m app.main history\n"
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    scan_parser = subparsers.add_parser(
        "scan", help="Scan a directory and list its files."
    )
    scan_parser.add_argument("path", help="Directory to scan.")
    _add_common_options(scan_parser)

    organize_parser = subparsers.add_parser(
        "organize",
        help="Organize files into category folders after preview.",
    )
    organize_parser.add_argument("path", help="Directory to organize.")
    _add_common_options(organize_parser)
    organize_parser.add_argument(
        "--include-subfolder-files",
        action="store_true",
        help="Also organize files already inside a category folder.",
    )

    duplicates_parser = subparsers.add_parser(
        "duplicates",
        help="Find duplicate files using content hashes.",
    )
    duplicates_parser.add_argument("path", help="Directory to scan for duplicates.")
    _add_common_options(duplicates_parser)

    review_parser = subparsers.add_parser(
        "review-duplicates",
        help="Review duplicate groups and move unwanted copies to a safe folder.",
    )
    review_parser.add_argument("path", help="Directory to review for duplicates.")
    _add_common_options(review_parser)

    history_parser = subparsers.add_parser(
        "history", help="Show the most recent recorded operations."
    )
    history_parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the command report to a text file.",
    )

    undo_parser = subparsers.add_parser(
        "undo", help="Undo the latest successful organization batch."
    )
    undo_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt for the undo operation.",
    )

    return parser

def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan subdirectories recursively.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview operations without changing anything.",
    )
    parser.add_argument(
        "--output",
        metavar="FILE",
        help="Write the command report to a text file.",
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="Include hidden files and folders in the scan.",
    )
    parser.add_argument(
        "--hash-algorithm",
        default=DEFAULT_HASH_ALGORITHM,
        metavar="ALGO",
        help=(
            "Hashing algorithm for duplicate detection "
            f"(default: {DEFAULT_HASH_ALGORITHM})."
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed diagnostic information to the console.",
    )

class CommandError(Exception):
    pass

def run(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    from app.utils.logger import configure_console, get_logger

    configure_console(verbose=getattr(args, "verbose", False))
    logger = get_logger("app.cli")
    logger.info("Command '%s' started with args: %s", args.command, vars(args))

    handlers: dict[str, Callable[[argparse.Namespace], int]] = {
        "scan": _cmd_scan,
        "organize": _cmd_organize,
        "duplicates": _cmd_duplicates,
        "review-duplicates": _cmd_review_duplicates,
        "history": _cmd_history,
        "undo": _cmd_undo,
    }

    handler = handlers[args.command]
    try:
        return handler(args)
    except CommandError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by the user.", file=sys.stderr)
        return 130
    except Exception as exc:
        logger.exception("Unhandled error during command '%s'", args.command)
        print(
            "An unexpected error occurred. "
            "Details have been written to the application log.",
            file=sys.stderr,
        )
        return 1

def _cmd_scan(args: argparse.Namespace) -> int:
    from app.organizer.scanner import scan_directory
    from app.utils.validators import validate_directory

    root = validate_directory(args.path)
    files = scan_directory(
        root,
        recursive=args.recursive,
        include_hidden=args.include_hidden,
    )
    report = build_scan_report(root, files)

    if args.output:
        write_output(args.output, report)
    print(report)
    return 0

def _cmd_organize(args: argparse.Namespace) -> int:
    from app.database import Database
    from app.organizer.operation_preview import OperationPlanner, format_plan
    from app.organizer.organizer import Organizer, create_category_folders
    from app.organizer.scanner import scan_directory
    from app.utils.validators import validate_directory

    root = validate_directory(args.path)
    files = scan_directory(
        root,
        recursive=args.recursive,
        include_hidden=args.include_hidden,
    )

    planner = OperationPlanner(
        root=root,
        include_subfolder_files=args.include_subfolder_files,
    )
    plan = planner.build_plan(files)

    if not plan:
        print("No files need to be organized.")
        return 0

    if args.dry_run:
        print(format_plan(plan))
        print("\nDRY RUN MODE: No files were changed.")
        return 0

    print(format_plan(plan))

    def confirm(_plan_text: str) -> bool:
        return ask_yes_no("Continue? [y/N]: ", default=False)

    database = Database()
    try:
        create_category_folders(root)
        organizer = Organizer(database=database, confirm=confirm)
        performed = organizer.execute(plan)
    finally:
        database.close()

    print(f"\nMoved {len(performed)} file(s).")
    return 0

def _cmd_duplicates(args: argparse.Namespace) -> int:
    from app.duplicates.duplicate_finder import DuplicateFinder
    from app.organizer.scanner import scan_directory
    from app.utils.validators import validate_directory, validate_hash_algorithm

    root = validate_directory(args.path)
    algorithm = validate_hash_algorithm(args.hash_algorithm)
    files = scan_directory(
        root,
        recursive=args.recursive,
        include_hidden=args.include_hidden,
    )

    finder = DuplicateFinder(algorithm=algorithm)
    groups = finder.find_duplicates(files)
    report = build_duplicates_report(groups, root)

    if args.output:
        write_output(args.output, report)
    print(report)

    if not groups and not args.output:
        print("No duplicate files found.")
    return 0

def _cmd_review_duplicates(args: argparse.Namespace) -> int:
    from app.database import Database
    from app.duplicates.duplicate_finder import DuplicateFinder
    from app.duplicates.duplicate_manager import DuplicateReviewer
    from app.organizer.scanner import scan_directory
    from app.utils.validators import validate_directory, validate_hash_algorithm

    root = validate_directory(args.path)
    algorithm = validate_hash_algorithm(args.hash_algorithm)
    files = scan_directory(
        root,
        recursive=args.recursive,
        include_hidden=args.include_hidden,
    )

    finder = DuplicateFinder(algorithm=algorithm)
    groups = finder.find_duplicates(files)

    if not groups:
        print("No duplicate files found. Nothing to review.")
        return 0

    database = Database()
    try:
        reviewer = DuplicateReviewer(
            database=database,
            dry_run=args.dry_run,
            confirm_callback=ask_yes_no,
        )
        summary = reviewer.review_groups(groups, root)
    finally:
        database.close()

    print(f"\nDuplicate review complete: {summary}")
    if args.dry_run:
        print("DRY RUN MODE: No files were changed.")
    return 0

def _cmd_history(args: argparse.Namespace) -> int:
    from app.database import Database

    database = Database()
    try:
        rows = database.get_all_operations(limit=100)
    finally:
        database.close()

    report = build_history_report(rows)
    if args.output:
        write_output(args.output, report)
    print(report)
    return 0

def _cmd_undo(args: argparse.Namespace) -> int:
    from app.database import Database
    from app.history.undo_manager import UndoManager

    database = Database()
    try:
        manager = UndoManager(database=database)
        return manager.run_interactive(force_yes=args.yes)
    finally:
        database.close()

def build_scan_report(root: Path, files: list) -> str:
    lines = [f"Scanned directory: {root}", f"Found {len(files)} file(s).", ""]
    for info in files[:MAX_REPORT_LINES]:
        lines.append(f"  {info.path}")
    if len(files) > MAX_REPORT_LINES:
        lines.append(f"  ... and {len(files) - MAX_REPORT_LINES} more.")
    return "\n".join(lines)

def build_duplicates_report(groups: list, root: Path) -> str:
    from app.duplicates.duplicate_finder import group_recoverable_space
    from app.utils.file_utils import human_readable_size

    if not groups:
        return f"Scanned: {root}\nNo duplicate files found."

    lines = [f"Scanned: {root}", f"Found {len(groups)} duplicate group(s).", ""]
    for index, group in enumerate(groups, start=1):
        recoverable = group_recoverable_space(group)
        lines.append(f"Duplicate group {index}")
        lines.append("")
        lines.append(f"Hash: {group.hash_value}")
        lines.append("")
        lines.append("Files:")
        for number, info in enumerate(group.files, start=1):
            lines.append(f"{number}. {info.path}")
            lines.append(f"   Size: {human_readable_size(info.size)}")
        lines.append("")
        lines.append(
            "Potential space that can be recovered: "
            f"{human_readable_size(recoverable)}"
        )
        lines.append("")
    return "\n".join(lines)

def build_history_report(rows: list) -> str:
    if not rows:
        return "No operations recorded yet."
    lines = ["Recent operations:", ""]
    for row in rows:
        status = row["status"]
        marker = "+" if status == "SUCCESS" else "!"
        lines.append(
            f"[{marker}] {row['operation_type']:16s} "
            f"{row['timestamp']}  {row['source_path']} -> {row['destination_path']}"
        )
    return "\n".join(lines)

def ask_yes_no(prompt: str, default: bool = False) -> bool:
    import sys

    try:
        response = input(prompt).strip().lower()
    except EOFError:
        return default
    except KeyboardInterrupt:
        print(file=sys.stderr)
        return default
    if not response:
        return default
    return response in ("y", "yes")

def write_output(path: str, content: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content + "\n", encoding="utf-8")

MAX_REPORT_LINES = 200
