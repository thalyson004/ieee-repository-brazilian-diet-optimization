"""Aggregate runtime, convergence, exact GA evaluations, and sampled RSS."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _describe(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"n": 0, "mean": None, "median": None, "sample_sd": None, "min": None, "max": None}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        "min": min(values),
        "max": max(values),
    }


def audit(source_run_id: str, output_dir: Path) -> dict[str, Any]:
    if not source_run_id or any(char not in "0123456789T_Zabcdefghijklmnopqrstuvwxyz" for char in source_run_id):
        raise ValueError("source_run_id contains unsupported filename characters")
    source_result_path = PROJECT_ROOT / "tests" / "results" / f"full-replication_{source_run_id}.json"
    source_result = json.loads(source_result_path.read_text(encoding="utf-8"))
    if source_result.get("status") != "passed":
        raise ValueError("source full-replication result did not pass its runner checks")
    workspace = PROJECT_ROOT / source_result["artifact_workspace"]
    manifest = json.loads((workspace / "run-manifest.json").read_text(encoding="utf-8"))
    files = list(workspace.rglob("execution-*.json"))
    executions = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    ga = [item for item in executions if item.get("resolution", "").startswith("ag-")]
    lp = [item for item in executions if item.get("resolution", "").startswith("pl-")]
    if len(ga) != 60 or len(lp) != 6:
        raise ValueError(f"Expected 60 GA and 6 LP records; found {len(ga)} GA and {len(lp)} LP")
    missing_counts = [item.get("execution_id") for item in ga if not isinstance(item.get("fitness_evaluation_count"), int)]
    if missing_counts:
        raise ValueError(f"GA records lack exact evaluation counts: {missing_counts[:5]}")

    group_rows: list[dict[str, Any]] = []
    for resolution in ("ag-alimentos", "ag-refeicoes"):
        for profile in ("regular", "vegetariana", "vegana"):
            records = [
                item for item in ga
                if item["resolution"] == resolution
                and item.get("candidate_pool_profile") == profile
            ]
            if len(records) != 10:
                raise ValueError(f"Expected 10 GA records for {resolution}/{profile}; found {len(records)}")
            group_rows.append({
                "method": resolution,
                "profile": profile,
                "runs": len(records),
                "runtime_seconds": _describe([float(item["duration_seconds"]) for item in records]),
                "fitness_evaluations": _describe([float(item["fitness_evaluation_count"]) for item in records]),
                "stop_generation": _describe([float(item["stop_generation"]) for item in records]),
                "stop_reasons": dict(Counter(item.get("stop_criterion", "unknown") for item in records)),
                "sampled_peak_rss_bytes": _describe([
                    float(item["process_memory"]["peak_sampled_rss_bytes"])
                    for item in records
                    if item.get("process_memory", {}).get("peak_sampled_rss_bytes") is not None
                ]),
                "memory_samples_per_run": [
                    item.get("process_memory", {}).get("sample_count") for item in records
                ],
            })

    lp_rows = [{
        "profile": item["profile"],
        "method": item["resolution"],
        "runtime_seconds": item["duration_seconds"],
        "initial_solver_status": item.get("solver", {}).get("initial_status"),
        "fallback_used": item.get("solver", {}).get("fallback_used"),
        "nonzero_slack_count": item.get("solver", {}).get("slack_analysis", {}).get("nonzero_slack_count"),
    } for item in lp]
    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": "1.0",
        "status": "diagnostic_resource_profile_not_primary_scientific_result",
        "source_run_id": source_run_id,
        "source_result_status": source_result["status"],
        "source_manifest_commit": manifest.get("source_provenance", {}).get("git_commit"),
        "source_manifest_worktree_dirty": manifest.get("source_provenance", {}).get("git_worktree_dirty"),
        "run_duration_seconds": source_result["duration_seconds"],
        "execution_environment": manifest.get("execution_environment"),
        "ga_expected": 60,
        "ga_observed": len(ga),
        "lp_expected": 6,
        "lp_observed": len(lp),
        "ga_groups": group_rows,
        "lp_executions": lp_rows,
        "limitations": [
            "RSS is sampled at 100-ms intervals and may miss shorter peaks.",
            "The reported RSS is whole-process memory, not memory attributable only to the optimizer.",
            "Runtime and resource use are conditional on the recorded software and hardware environment.",
            "This audit does not resolve mapping, ingredient, missing-nutrient, or method-equivalence gates.",
        ],
    }
    output = output_dir / "replication-resource-audit.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "source_run_id": source_run_id,
        "ga_records": len(ga),
        "lp_records": len(lp),
        "ga_groups": [{
            "method": group["method"], "profile": group["profile"],
            "runtime_mean_s": group["runtime_seconds"]["mean"],
            "fitness_evaluations_mean": group["fitness_evaluations"]["mean"],
            "stop_generation_mean": group["stop_generation"]["mean"],
            "sampled_peak_rss_max_bytes": group["sampled_peak_rss_bytes"]["max"],
        } for group in group_rows],
        "output": str(output),
    }, ensure_ascii=False, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    audit(args.source_run_id, args.output_dir)


if __name__ == "__main__":
    main()
