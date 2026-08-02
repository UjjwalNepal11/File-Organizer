from __future__ import annotations

import sys

from app.cli import run
from app.utils.logger import get_logger

logger = get_logger(__name__)

def main() -> int:
    logger.info("Application startup.")
    exit_code = run(sys.argv[1:])
    logger.info("Application finished with exit code %d.", exit_code)
    return exit_code

if __name__ == "__main__":
    raise SystemExit(main())
