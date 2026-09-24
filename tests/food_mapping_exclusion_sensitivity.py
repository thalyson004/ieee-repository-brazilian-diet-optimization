"""Run a paired sensitivity excluding the 19 unresolved mapped food labels."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline", "pending-mappings-excluded")


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
        "mapping_queue_run_id": "mapping-review-queue-current_20260924T201700618482Z_77923935",
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
