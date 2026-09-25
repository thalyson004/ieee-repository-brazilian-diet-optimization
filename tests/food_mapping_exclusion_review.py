"""Audit paired full replications with and without unresolved mapped foods."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tests.ga_sensitivity_review import (
    paired_summary,
    read_computational_metrics,
    read_ga_metrics,
)
from tests.logging_utils import LOGS_DIR, append_log, build_run_id
from tests.result_writer import RESULTS_DIR, save_result
from tests.validate_candidate_scope import audit_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PREFIX = "food-mapping-exclusion-sensitivity_"
VARIANTS = ("baseline", "pending-mappings-excluded")


def resolve_source_workspace(source_run_id: str) -> Path:
    normalized_id = source_run_id.removeprefix(SOURCE_PREFIX)
    if not normalized_id or "/" in normalized_id or "\\" in normalized_id:
        raise ValueError("Expected a food-mapping exclusion sensitivity run ID")
    return PROJECT_ROOT / "tests" / "results" / "artifacts" / f"{SOURCE_PREFIX}{normalized_id}" / "audit"


def analyze(source_workspace: Path, review_workspace: Path) -> dict[str, Any]:
    summary = json.loads((source_workspace / "sensitivity-summary.json").read_text(encoding="utf-8"))
    if summary.get("status") != "completed" or summary.get("runs_per_profile_and_granularity") != 10:
        raise ValueError("Expected a completed ten-run paired mapping-exclusion sensitivity")
    if {entry["variant"] for entry in summary.get("variants", [])} != set(VARIANTS):
        raise ValueError("Mapping-exclusion sensitivity is missing a comparison variant")

    metrics: dict[str, dict[tuple, float]] = {}
    computational: dict[str, dict[tuple, float]] = {}
    manifests: dict[str, dict[str, Any]] = {}
    scope: dict[str, dict[str, Any]] = {}
    preparation: dict[str, Any] = {}
    for variant in VARIANTS:
        workspace = source_workspace / variant
        manifest = json.loads((workspace / "run-manifest.json").read_text(encoding="utf-8"))
        manifests[variant] = manifest
        if manifest.get("replication_base_seed") != summary["paired_base_seed"]:
            raise ValueError(f"Seed mismatch in {variant}")
        if manifest.get("ga_runs_per_profile_and_granularity") != 10:
            raise ValueError(f"Run count mismatch in {variant}")
        expected_exclusion = variant == "pending-mappings-excluded"
        if manifest.get("pending_mapping_exclusions_enabled") is not expected_exclusion:
            raise ValueError(f"Mapping exclusion flag mismatch in {variant}")
        report = json.loads((workspace / "input-preparation.json").read_text(encoding="utf-8"))
        if report.get("pending_mapping_exclusions_enabled") is not expected_exclusion:
            raise ValueError(f"Input-preparation audit mismatch in {variant}")
        preparation[variant] = report.get("pending_mapping_exclusion_counts_by_profile", {})
        metrics[variant] = read_ga_metrics(workspace)
        computational[variant] = read_computational_metrics(workspace)
        if sum(key[2] == "runtime_seconds" for key in computational[variant]) != 60:
            raise ValueError(f"Expected cost metrics for 60 GA runs in {variant}")
        scope_report = audit_workspace(workspace)
        scope[variant] = {
            "status": scope_report["status"],
            "checked_outputs": scope_report["checked_outputs"],
            "violations": scope_report["violations"],
        }
        if scope_report["status"] != "passed" or scope_report["checked_outputs"] != 66:
            raise ValueError(f"Profile-scope validation failed for {variant}")

    provenance = [manifest.get("source_provenance", {}) for manifest in manifests.values()]
    commits = {item.get("git_commit") for item in provenance}
    if len(commits) != 1 or any(item.get("git_worktree_dirty") for item in provenance):
        raise ValueError("Variants must share one clean source revision")
    hashes = [item.get("input_sha256") for item in provenance]
    if not hashes[0] or hashes[0] != hashes[1]:
        raise ValueError("Baseline and exclusion variants must use identical versioned inputs")
    if set(metrics["baseline"]) != set(metrics["pending-mappings-excluded"]):
        raise ValueError("Outcome metrics are not paired across variants")
    if set(computational["baseline"]) != set(computational["pending-mappings-excluded"]):
        raise ValueError("Computational metrics are not paired across variants")

    def compare(left: dict[tuple, float], right: dict[tuple, float], seed_offset: int) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str, str], list[tuple[int, float]]] = {}
        for key, value in right.items():
            profile, method, metric, execution_id = key
            grouped.setdefault((profile, method, metric), []).append(
                (execution_id, value - left[key])
            )
        rows = []
        for group, pairs in sorted(grouped.items()):
            pairs.sort()
            if [execution_id for execution_id, _ in pairs] != list(range(1, 11)):
                raise ValueError(f"Expected paired execution IDs 1..10 for {group}")
            rows.append({
                "variant": "pending-mappings-excluded",
                "profile": group[0],
                "method": group[1],
                "metric": group[2],
                **paired_summary(
                    [difference for _, difference in pairs],
                    summary["paired_base_seed"] + seed_offset,
                ),
            })
        return rows

    outcomes = compare(metrics["baseline"], metrics["pending-mappings-excluded"], 101)
    costs = compare(computational["baseline"], computational["pending-mappings-excluded"], 102)
    report = {
        "schema_version": "1.0",
        "status": "diagnostic_mapping_exclusion_sensitivity_not_primary_result",
        "source_run_id": source_workspace.parent.name.removeprefix(SOURCE_PREFIX),
        "mapping_queue_run_id": summary["mapping_queue_run_id"],
        "paired_base_seed": summary["paired_base_seed"],
        "runs_per_profile_and_granularity": 10,
        "source_git_commit": next(iter(commits)),
        "input_sha256": hashes[0],
        "profile_scope_validation": scope,
        "pending_exclusion_preparation_audit": preparation,
        "paired_outcome_differences": outcomes,
        "paired_computational_differences": costs,
        "limitations": [
            "Excluding unresolved labels measures sensitivity to their inclusion; it does not identify the correct TBCA target or recipe.",
            "The exclusion scenario may change candidate availability and can be selective; report its exact removals per profile.",
            "Bootstrap intervals are unadjusted across multiple outcomes and strata.",
            "Nutrient missingness, environmental line attribution, and GA-LP formulation equivalence remain unresolved.",
        ],
    }
    review_workspace.mkdir(parents=True, exist_ok=False)
    (review_workspace / "food-mapping-exclusion-review.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Write the report here when managed by tests.run_experiments.",
    )
    args = parser.parse_args()
    source = resolve_source_workspace(args.source_run_id)
    if args.output_dir is not None:
        report = analyze(source, args.output_dir)
        print(f"Artifact: {args.output_dir / 'food-mapping-exclusion-review.json'}")
        print(
            f"Validated {len(report['profile_scope_validation'])} variants, "
            f"{len(report['paired_outcome_differences'])} outcome groups, and "
            f"{len(report['paired_computational_differences'])} computational groups"
        )
        return
    run_id = build_run_id()
    output = RESULTS_DIR / "artifacts" / f"food-mapping-exclusion-review_{run_id}"
    log_path = LOGS_DIR / f"food-mapping-exclusion-review_{run_id}.log"
    append_log(log_path, f"Source run: {source}")
    status, error = "passed", None
    try:
        report = analyze(source, output)
        append_log(
            log_path,
            f"Validated {len(report['profile_scope_validation'])} variants, "
            f"{len(report['paired_outcome_differences'])} outcome groups, and "
            f"{len(report['paired_computational_differences'])} computational groups",
        )
    except Exception as exc:
        status, error = "failed", f"{type(exc).__name__}: {exc}"
        append_log(log_path, error)
    result = save_result("food-mapping-exclusion-review", run_id, {
        "schema_version": "1.0",
        "experiment": "food-mapping-exclusion-review",
        "run_id": run_id,
        "status": status,
        "source_run_id": args.source_run_id,
        "artifact_workspace": str(output.relative_to(PROJECT_ROOT)) if output.exists() else None,
        "log": str(log_path.relative_to(PROJECT_ROOT)),
        "error": error,
    })
    print(f"Result: {result}")
    print(f"Log: {log_path}")
    if status != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
