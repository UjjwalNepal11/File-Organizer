# File Organizer and Duplicate Finder

A safe, beginner-friendly **command-line application** that scans, organizes and
deduplicates your files — completely built on the **Python standard library**.
No web front end, no third-party packages, no hidden cloud calls.

The golden rule of this project: **your files are never deleted.** Every
operation is first _previewed_, then _confirmed_, supports `--dry-run`, avoids
overwriting anything, and records itself in a local SQLite history database so
it can be **undone** later.

## 1. Features

| Feature                 | Description                                                                                                                      |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 📁 Directory scanning   | Walks a folder (optionally recursive), collects file metadata without loading file contents                                      |
| 🗂️ Smart classification | Groups files into _Images, Documents, Videos, Audio, Archives, Programs, Code, Spreadsheets, Presentations, Other_               |
| 🎯 Safe organization    | Moves files into category folders only after a preview + confirmation                                                            |
| 👯 Duplicate detection  | Uses **size-first grouping** + **chunked SHA-256 hashing** so only same-sized files are ever hashed                              |
| 🗃️ Duplicate review     | Moves unwanted copies to a safe `Duplicate_Review/` folder instead of deleting them                                              |
| 🧾 Operation preview    | Shows every `From → To` move before anything changes                                                                             |
| 🧪 Dry-run mode         | Builds the complete plan, prints it, and changes absolutely nothing                                                              |
| 💾 SQLite history       | Every move is recorded (type, source, destination, timestamp, status, error)                                                     |
| ↩️ Undo                 | Restores the latest operation batch — organizers and duplicate reviews alike                                                     |
| 🧯 Error resilience     | Permission errors, locked files, broken links and vanished files are logged and skipped; the app never crashes from one bad file |
| 📝 Rotating logs        | `logs/file_organizer.log` keeps a full diagnostic trail with no console tracebacks                                               |

## 2. Technology Used

Built with **Python 3.11+** and the **standard-library** modules only:
No Django, Flask, FastAPI or any other web framework. No third-party packages.

## 17. License

MIT — see [LICENSE](LICENSE).

