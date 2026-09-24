"""Validate and summarize one completed paired GA sensitivity run."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

from tests.logging_utils import LOGS_DIR, append_log, build_run_id
from tests.result_writer import RESULTS_DIR, save_result
from tests.validate_candidate_scope import audit_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VARIANTS = (
    "baseline", "reduced-population", "higher-mutation", "shorter-stagnation",
    "repair-disabled",
)
BOOTSTRAP_REPLICATES = 2000


def paired_summary(differences: list[float], seed: int) -> dict:
    if not differences:
        raise ValueError("Cannot summarize an empty paired difference sample")
    generator = random.Random(seed)
    means = sorted(
        statistics.mean(generator.choices(differences, k=len(differences)))
        for _ in range(BOOTSTRAP_REPLICATES)
    )
    n = len(differences)
    return {
        "n_pairs": n,
        "mean_difference": statistics.mean(differences),
        "median_difference": statistics.median(differences),
        "sample_sd": statistics.stdev(differences) if n > 1 else None,
        "bootstrap_percentile_95_ci": [
            means[int(0.025 * BOOTSTRAP_REPLICATES)],
            means[min(int(0.975 * BOOTSTRAP_REPLICATES), BOOTSTRAP_REPLICATES - 1)],
        ] if n > 1 else None,
        "bootstrap_replicates": BOOTSTRAP_REPLICATES if n > 1 else 0,
    }


def read_ga_metrics(variant_workspace: Path) -> dict[tuple, float]:
    path = variant_workspace / "article_outputs" / "run_statistics" / "run-metrics-long.csv"
    values = {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row["observation_unit"] != "independent_ga_run":
                continue
            key = (row["profile"], row["method"], row["metric"], int(row["execution_id"]))
            value = float(row["value"])
            if not math.isfinite(value) or key in values:
                raise ValueError(f"Invalid or duplicate GA metric row: {key}")
            values[key] = value
    if not values:
        raise ValueError(f"No independent GA-run metrics in {path}")
    return values


def analyze_workspace(source_workspace: Path, review_workspace: Path) -> dict:
    summary = json.loads((source_workspace / "sensitivity-summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "completed" or summary.get("runs_per_profile_and_granularity") != 10:
        raise ValueError("Source run is not the complete ten-run sensitivity matrix")
    listed_variants = {entry["variant"]: entry for entry in summary["variants"]}
    if set(listed_variants) != set(VARIANTS):
        raise ValueError("Sensitivity run does not contain the registered five variants")

    provenance = {}
    metrics = {}
    scope = {}
    for variant in VARIANTS:
        variant_workspace = source_workspace / variant
        manifest = json.loads((variant_workspace / "run-manifest.json").read_text(encoding="utf-8"))
        if manifest["replication_base_seed"] != summary["paired_base_seed"]:
            raise ValueError(f"Seed mismatch in variant {variant}")
        if manifest["ga_runs_per_profile_and_granularity"] != 10:
            raise ValueError(f"Run count mismatch in variant {variant}")
        provenance[variant] = manifest["source_provenance"]
        metrics[variant] = read_ga_metrics(variant_workspace)
        scope_report = audit_workspace(variant_workspace)
        scope[variant] = {
            "status": scope_report["status"],
            "checked_outputs": scope_report["checked_outputs"],
            "violations": scope_report["violations"],
        }
        if scope_report["status"] != "passed" or scope_report["checked_outputs"] != 66:
            raise ValueError(f"Profile scope validation failed for variant {variant}")

    commits = {item["git_commit"] for item in provenance.values()}
    if len(commits) != 1 or any(item["git_worktree_dirty"] for item in provenance.values()):
        raise ValueError("Sensitivity variants do not share one clean source revision")
    baseline = metrics["baseline"]
    comparison_rows = []
    for variant_index, variant in enumerate(VARIANTS[1:], start=1):
        if set(metrics[variant]) != set(baseline):
            raise ValueError(f"GA metric keys do not match baseline for {variant}")
        grouped: dict[tuple, list[tuple[int, float]]] = {}
        for key, value in metrics[variant].items():
            profile, method, metric, execution_id = key
            group = (profile, method, metric)
            grouped.setdefault(group, []).append((execution_id, value - baseline[key]))
        for group, pairs in sorted(grouped.items()):
            pairs.sort()
            if [execution_id for execution_id, _ in pairs] != list(range(1, 11)):
                raise ValueError(f"Expected ten paired execution IDs for {variant}/{group}")
            stats = paired_summary(
                [difference for _, difference in pairs],
                seed=summary["paired_base_seed"] + variant_index,
            )
            comparison_rows.append(
                {
                    "variant": variant,
                    "profile": group[0],
                    "method": group[1],
                    "metric": group[2],
                    **stats,
                }
            )

    report = {
        "schema_version": "1.0",
        "source_sensitivity_run_id": source_workspace.name.removeprefix("ga-hyperparameter-sensitivity_"),
        "source_workspace": str(source_workspace.relative_to(PROJECT_ROOT)),
        "source_git_commit": next(iter(commits)),
        "paired_base_seed": summary["paired_base_seed"],
        "runs_per_profile_and_granularity": 10,
        "variants": list(VARIANTS),
        "profile_scope_validation": scope,
        "paired_ga_differences_vs_baseline": comparison_rows,
        "interpretation": "Diagnostic paired sensitivity only. No cross-method causal inference or manuscript result is authorized while data, missingness, and method-equivalence gates remain open.",
    }
    review_workspace.mkdir(parents=True, exist_ok=False)
    (review_workspace / "ga-sensitivity-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (review_workspace / "paired-differences.csv").open("w", encoding="utf-8", newline="") as stream:
        fieldnames = list(comparison_rows[0])
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(comparison_rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args()
    run_id = build_run_id()
    source_workspace = PROJECT_ROOT / "tests" / "results" / "artifacts" / f"ga-hyperparameter-sensitivity_{args.source_run_id}"
    review_workspace = RESULTS_DIR / "artifacts" / f"ga-sensitivity-review_{run_id}"
    log_path = LOGS_DIR / f"ga-sensitivity-review_{run_id}.log"
    started = datetime.now(timezone.utc).isoformat()
    append_log(log_path, f"Source run: {source_workspace}")
    status, error = "passed", None
    try:
        report = analyze_workspace(source_workspace, review_workspace)
        append_log(log_path, f"Validated {len(report['profile_scope_validation'])} variants and {len(report['paired_ga_differences_vs_baseline'])} paired metric groups")
    except Exception as exc:
        status, error = "failed", f"{type(exc).__name__}: {exc}"
        append_log(log_path, error)
    payload = {
        "schema_version": "1.0",
        "experiment": "ga-sensitivity-review",
        "run_id": run_id,
        "status": status,
        "started_at_utc": started,
        "source_sensitivity_run_id": args.source_run_id,
        "artifact_workspace": str(review_workspace.relative_to(PROJECT_ROOT)) if review_workspace.exists() else None,
        "log": str(log_path.relative_to(PROJECT_ROOT)),
        "error": error,
    }
    result_path = save_result("ga-sensitivity-review", run_id, payload)
    print(f"Result: {result_path}")
    print(f"Log: {log_path}")
    if status != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
