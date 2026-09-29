"""Validate and summarize the paired objective-weight GA sensitivity."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from tests.ga_sensitivity_review import paired_summary, read_ga_metrics
from tests.logging_utils import LOGS_DIR, append_log, build_run_id
from tests.result_writer import RESULTS_DIR, save_result
from tests.validate_candidate_scope import audit_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline", "environmental-weight-0.5", "environmental-weight-2.0")
SOURCE_PREFIX = "ga-objective-weight-sensitivity_"


def resolve_source_workspace(source_run_id: str) -> Path:
    normalized_id = source_run_id.removeprefix(SOURCE_PREFIX)
    if not normalized_id or "/" in normalized_id or "\\" in normalized_id:
        raise ValueError("Expected a GA objective-weight sensitivity run ID")
    return PROJECT_ROOT / "tests" / "results" / "artifacts" / f"{SOURCE_PREFIX}{normalized_id}" / "audit"


def analyze(source_workspace: Path, review_workspace: Path) -> dict[str, Any]:
    summary = json.loads((source_workspace / "sensitivity-summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "completed" or summary.get("runs_per_profile_and_granularity") != 10:
        raise ValueError("Expected a completed ten-run paired objective-weight matrix")
    if {entry["variant"] for entry in summary.get("variants", [])} != set(VARIANTS):
        raise ValueError("Objective-weight matrix has missing or unexpected variants")

    metrics: dict[str, dict[tuple, float]] = {}
    manifests: dict[str, dict[str, Any]] = {}
    scope: dict[str, dict[str, Any]] = {}
    for variant in VARIANTS:
        workspace = source_workspace / variant
        manifest = json.loads((workspace / "run-manifest.json").read_text(encoding="utf-8"))
        manifests[variant] = manifest
        if manifest.get("replication_base_seed") != summary["paired_base_seed"]:
            raise ValueError(f"Seed mismatch in {variant}")
        if manifest.get("ga_runs_per_profile_and_granularity") != 10:
            raise ValueError(f"Run count mismatch in {variant}")
        metrics[variant] = read_ga_metrics(workspace)
        scope_report = audit_workspace(workspace)
        scope[variant] = {
            "status": scope_report["status"],
            "checked_outputs": scope_report["checked_outputs"],
            "violations": scope_report["violations"],
        }
        if scope_report["status"] != "passed" or scope_report["checked_outputs"] != 66:
            raise ValueError(f"Profile-scope validation failed for {variant}")
    commits = {m.get("source_provenance", {}).get("git_commit") for m in manifests.values()}
    if len(commits) != 1 or any(m.get("source_provenance", {}).get("git_worktree_dirty") for m in manifests.values()):
        raise ValueError("Variants must share a clean source revision")
    input_hashes = [m.get("source_provenance", {}).get("input_sha256") for m in manifests.values()]
    if not input_hashes[0] or any(item != input_hashes[0] for item in input_hashes[1:]):
        raise ValueError("Input hashes differ across objective-weight variants")
    if any(set(metrics[variant]) != set(metrics["baseline"]) for variant in VARIANTS[1:]):
        raise ValueError("GA run-level metric keys are not paired across variants")

    comparisons = []
    for index, variant in enumerate(VARIANTS[1:], start=1):
        grouped: dict[tuple[str, str, str], list[tuple[int, float]]] = {}
        for key, value in metrics[variant].items():
            profile, method, metric, execution_id = key
            grouped.setdefault((profile, method, metric), []).append(
                (execution_id, value - metrics["baseline"][key])
            )
        for group, pairs in sorted(grouped.items()):
            pairs.sort()
            ids = [execution_id for execution_id, _ in pairs]
            if ids != list(range(1, 11)):
                raise ValueError(f"Expected paired IDs 1..10 for {variant}/{group}; got {ids}")
            comparisons.append({
                "variant": variant,
                "profile": group[0],
                "method": group[1],
                "metric": group[2],
                **paired_summary([difference for _, difference in pairs], summary["paired_base_seed"] + index),
            })
    report = {
        "schema_version": "1.0",
        "status": "diagnostic_paired_objective_weight_sensitivity_not_primary_result",
        "source_sensitivity_run_id": source_workspace.parent.name.removeprefix(SOURCE_PREFIX),
        "paired_base_seed": summary["paired_base_seed"],
        "runs_per_profile_and_granularity": 10,
        "effective_weight_scenarios": {
            variant: manifests[variant].get("ga_overrides", {}).get("environmental_criterion_weight", 1.0)
            for variant in VARIANTS
        },
        "source_git_commit": next(iter(commits)),
        "input_sha256": input_hashes[0],
        "profile_scope_validation": scope,
        "paired_differences_vs_baseline": comparisons,
        "interpretation": "Within-profile and within-granularity paired diagnostics only; results do not establish a clinically appropriate weight or cross-method causal effect. Mapping, ingredient, missingness, and formulation-equivalence gates remain open.",
    }
    review_workspace.mkdir(parents=True, exist_ok=False)
    (review_workspace / "ga-objective-weight-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (review_workspace / "paired-differences.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True)
    args = parser.parse_args()
    run_id = build_run_id()
    source = resolve_source_workspace(args.source_run_id)
    output = RESULTS_DIR / "artifacts" / f"ga-objective-weight-review_{run_id}"
    log_path = LOGS_DIR / f"ga-objective-weight-review_{run_id}.log"
    append_log(log_path, f"Source run: {source}")
    status, error = "passed", None
    try:
        report = analyze(source, output)
        append_log(log_path, f"Validated {len(report['profile_scope_validation'])} variants and {len(report['paired_differences_vs_baseline'])} paired groups")
    except Exception as exc:
        status, error = "failed", f"{type(exc).__name__}: {exc}"
        append_log(log_path, error)
    result_path = save_result("ga-objective-weight-review", run_id, {
        "schema_version": "1.0", "experiment": "ga-objective-weight-review", "run_id": run_id,
        "status": status, "source_sensitivity_run_id": args.source_run_id,
        "artifact_workspace": str(output.relative_to(PROJECT_ROOT)) if output.exists() else None,
        "log": str(log_path.relative_to(PROJECT_ROOT)), "error": error,
    })
    print(f"Result: {result_path}")
    print(f"Log: {log_path}")
    if status != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
