"""Persist an experiment summary without overwriting prior executions."""

from __future__ import annotations

import json
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
RESULTS_DIR = TEST_ROOT / "results"


def save_result(experiment: str, run_id: str, payload: dict) -> Path:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{experiment}_{run_id}.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return path
