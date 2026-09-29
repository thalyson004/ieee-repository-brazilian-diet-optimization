"""One immutable log file for every experiment execution."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


TEST_ROOT = Path(__file__).resolve().parent
LOGS_DIR = TEST_ROOT / "logs"


def build_run_id() -> str:
    """Return a sortable UTC execution identifier safe for file names."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}_{uuid4().hex[:8]}"


def append_log(path: Path, message: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(message.rstrip() + "\n")
