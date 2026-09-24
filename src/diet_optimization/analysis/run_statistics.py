"""Describe per-run outcomes without treating pooled source diets as replicates.

Usage: python -m diet_optimization.analysis.run_statistics --workspace PATH
The output is diagnostic until the reviewed food map and revised nutrition
protocol are active. No cross-method significance test is performed here.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path


PROFILES = ("regular", "vegetariana", "vegana")
METHODS = {"ag-alimentos": "GA-Food", "ag-refeicoes": "GA-Meal",
           "pl-alimentos": "LP-Food", "pl-refeicoes": "LP-Meal"}
METRICS = ("carbon_gco2eq_per_day", "energy_kcal_per_day", "unique_foods_per_plan",
           "daily_nutrient_violation_count")


def _quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summarize_values(values: list[float], seed: int, bootstrap_draws: int = 2000) -> dict:
    if not values:
        raise ValueError("At least one observation is required")
    result = {
        "n": len(values), "mean": statistics.mean(values),
        "median": statistics.median(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        "q1": _quantile(values, 0.25), "q3": _quantile(values, 0.75),
        "mean_bootstrap_percentile_95_ci": None,
    }
    if len(values) > 1:
        rng = random.Random(seed)
        means = [statistics.mean(rng.choices(values, k=len(values)))
                 for _ in range(bootstrap_draws)]
        result["mean_bootstrap_percentile_95_ci"] = [
            _quantile(means, 0.025), _quantile(means, 0.975)
        ]
    return result


def _metrics(plan: dict, diagnostics: dict) -> dict[str, float]:
    unique = {item["alimento"] for meals in plan.values() for foods in meals.values() for item in foods}
    return {
        "carbon_gco2eq_per_day": float(diagnostics["mean_daily_footprints"]["carbon_footprint"]),
        "energy_kcal_per_day": float(diagnostics["mean_daily_nutrients"].get("Energia", 0.0)),
        "unique_foods_per_plan": float(len(unique)),
        "daily_nutrient_violation_count": float(diagnostics["violation_count"]),
    }


def collect(workspace: Path) -> list[dict]:
    rows: list[dict] = []
    root = workspace / "data" / "outputs" / "optimization_runs"
    for profile in PROFILES:
        for resolution, method in METHODS.items():
            if resolution.startswith("ag-"):
                paths = sorted((root / resolution / "runs" / f"dietas-{profile}").glob("execution-*.json"))
            else:
                paths = [root / resolution / f"execution-{profile}.json"]
            if not paths or any(not path.is_file() for path in paths):
                raise FileNotFoundError(f"Missing per-run artifact for {profile}/{method}: {paths}")
            for path in paths:
                payload = json.loads(path.read_text(encoding="utf-8"))
                plan = payload["final_solution"]
                if isinstance(plan, list):
                    plan = plan[0]
                diagnostics = payload["metrics_and_violations"]
                if not plan or not diagnostics:
                    raise ValueError(f"Missing final plan or diagnostics: {path}")
                for metric, value in _metrics(plan, diagnostics).items():
                    rows.append({
                        "profile": profile, "method": method, "metric": metric,
                        "value": value, "observation_unit": "independent_ga_run" if resolution.startswith("ag-") else "deterministic_lp_configuration",
                        "execution_id": payload.get("execution_id", 1),
                        "source_artifact": str(path.relative_to(workspace)).replace("\\", "/"),
                    })
    return rows


def write_reports(workspace: Path, output_dir: Path) -> dict:
    rows = collect(workspace)
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "run-metrics-long.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(row["profile"], row["method"], row["metric"])].append(row["value"])
    summary = []
    for key, values in sorted(grouped.items()):
        material = "|".join(key).encode("utf-8")
        seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
        summary.append({"profile": key[0], "method": key[1], "metric": key[2],
                        **summarize_values(values, seed)})
    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_until_mapping_and_revised_nutrition_are_frozen",
        "units": {"GA": "independent seeded execution conditional on fixed input pool",
                  "LP": "one deterministic configuration, no sampling CI"},
        "interval_method": "2000 fixed-seed percentile bootstrap resamples of independent GA runs; absent for n=1",
        "statistical_tests": "none: archived formulations are not equivalent; no pseudo-replication",
        "summary": summary,
    }
    (output_dir / "run-statistics.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    report = write_reports(workspace, workspace / "article_outputs" / "run_statistics")
    print(f"Wrote {len(report['summary'])} profile-method-metric summaries")


if __name__ == "__main__":
    main()
