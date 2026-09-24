"""Run paired-seed GA sensitivity variants and preserve each full workspace."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VARIANTS = {
    "baseline": None,
    "reduced-population": "configs/ga-sensitivity/reduced-population.json",
    "higher-mutation": "configs/ga-sensitivity/higher-mutation.json",
    "shorter-stagnation": "configs/ga-sensitivity/shorter-stagnation.json",
    "repair-disabled": "configs/ga-sensitivity/repair-disabled.json",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--nutrition-protocol", choices=("historical", "revised"), default="revised")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.runs < 1:
        raise SystemExit("--runs must be positive")
    summary = {
        "schema_version": "1.0",
        "experiment": "ga-hyperparameter-sensitivity",
        "status": "running",
        "paired_base_seed": args.seed,
        "runs_per_profile_and_granularity": args.runs,
        "nutrition_protocol": args.nutrition_protocol,
        "variants": [],
    }
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for variant, override_path in VARIANTS.items():
        output = args.output_dir / variant
        command = [
            sys.executable,
            "-m",
            "diet_optimization.experiments.runner",
            "--mode",
            "rerun",
            "--runs",
            str(args.runs),
            "--seed",
            str(args.seed),
            "--nutrition-protocol",
            args.nutrition_protocol,
            "--output-dir",
            str(output),
        ]
        if override_path is not None:
            command.extend(["--ga-overrides", str(PROJECT_ROOT / override_path)])
        print(f"Starting GA sensitivity variant: {variant}", flush=True)
        subprocess.run(command, cwd=PROJECT_ROOT, check=True)
        summary["variants"].append(
            {
                "variant": variant,
                "overrides_file": override_path,
                "workspace": str(output.relative_to(PROJECT_ROOT)),
            }
        )
    summary["status"] = "completed"
    (args.output_dir / "sensitivity-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
