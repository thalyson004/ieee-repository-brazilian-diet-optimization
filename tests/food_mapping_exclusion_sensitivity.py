"""Run a paired sensitivity excluding the 19 unresolved mapped food labels."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tests.result_writer import RESULTS_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline", "pending-mappings-excluded")


def latest_mapping_queue_run_id(results_dir: Path = RESULTS_DIR) -> str | None:
    """Return the newest successful active-map queue run, not a stale literal ID."""
    candidates = []
    for path in results_dir.glob("mapping-review-queue-current_*.json"):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if result.get("status") != "passed" or not result.get("run_id"):
            continue
        candidates.append((result.get("started_at_utc", ""), result["run_id"]))
    return max(candidates)[1] if candidates else None


def run(runs: int, seed: int, nutrition_protocol: str, output_dir: Path) -> dict[str, Any]:
    if runs < 1:
        raise ValueError("runs must be positive")
    output_dir.mkdir(parents=True, exist_ok=False)
    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "experiment": "food-mapping-exclusion-sensitivity",
        "status": "running",
        "paired_base_seed": seed,
        "runs_per_profile_and_granularity": runs,
        "nutrition_protocol": nutrition_protocol,
        "mapping_queue_run_id": latest_mapping_queue_run_id(),
        "variants": [],
        "interpretation": "Exclusion is a robustness scenario, not a food-mapping adjudication or final input policy.",
    }
    for variant in VARIANTS:
        workspace = output_dir / variant
        command = [
            sys.executable, "-m", "diet_optimization.experiments.runner",
            "--mode", "rerun", "--runs", str(runs), "--seed", str(seed),
            "--nutrition-protocol", nutrition_protocol, "--output-dir", str(workspace),
        ]
        if variant == "pending-mappings-excluded":
            command.append("--exclude-pending-food-mappings")
        print(f"Starting food-mapping exclusion variant: {variant}", flush=True)
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
        summary["variants"].append({
            "variant": variant,
            "exclude_pending_food_mappings": variant == "pending-mappings-excluded",
            "workspace": str(workspace.relative_to(PROJECT_ROOT)),
        })
    summary["status"] = "completed"
    (output_dir / "sensitivity-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--nutrition-protocol", choices=("historical", "revised"), default="revised")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.runs, args.seed, args.nutrition_protocol, args.output_dir)
    print(json.dumps({
        "status": report["status"],
        "paired_base_seed": report["paired_base_seed"],
        "runs_per_profile_and_granularity": report["runs_per_profile_and_granularity"],
        "variants": [row["variant"] for row in report["variants"]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
