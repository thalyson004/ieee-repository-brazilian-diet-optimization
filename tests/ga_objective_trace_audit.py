"""Validate and summarize per-generation objective decompositions from a GA run."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPONENTS = (
    "weighted_nutritional_penalty",
    "weighted_environmental_penalty",
    "weighted_meal_energy_share_penalty",
)


def validate_trace(execution: dict[str, Any], tolerance: float = 1e-7) -> dict[str, Any]:
    history = execution.get("objective_by_generation")
    trace = execution.get("objective_components_by_generation")
    if not isinstance(history, list) or not isinstance(trace, list) or not history:
        raise ValueError("GA execution is missing a non-empty objective history or decomposition")
    if len(history) != len(trace):
        raise ValueError("scalar objective history and component trace lengths differ")
    previous_evaluations = -1
    for index, (scalar, row) in enumerate(zip(history, trace, strict=True)):
        if row.get("generation") != index:
            raise ValueError(f"generation index mismatch at row {index}")
        if any(not isinstance(row.get(key), (int, float)) for key in COMPONENTS):
            raise ValueError(f"missing numeric objective component at generation {index}")
        reconstructed = -sum(float(row[key]) for key in COMPONENTS)
        if abs(reconstructed - float(scalar)) > tolerance or abs(float(row.get("fitness", float("nan"))) - float(scalar)) > tolerance:
            raise ValueError(f"fitness decomposition mismatch at generation {index}")
        evaluations = row.get("cumulative_fitness_evaluations")
        if not isinstance(evaluations, int) or evaluations < previous_evaluations:
            raise ValueError(f"invalid cumulative evaluation count at generation {index}")
        previous_evaluations = evaluations
    return {"generations": len(trace), "final_fitness": float(history[-1])}


def _summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
    }


def audit(source_run_id: str, output_dir: Path) -> dict[str, Any]:
    if not source_run_id or any(char not in "0123456789T_Zabcdefghijklmnopqrstuvwxyz" for char in source_run_id):
        raise ValueError("source_run_id contains unsupported filename characters")
    result_path = PROJECT_ROOT / "tests" / "results" / f"full-replication_{source_run_id}.json"
    source = json.loads(result_path.read_text(encoding="utf-8"))
    if source.get("status") != "passed":
        raise ValueError("source full-replication did not pass its runner checks")
    workspace = PROJECT_ROOT / source["artifact_workspace"]
    manifest = json.loads((workspace / "run-manifest.json").read_text(encoding="utf-8"))
    files = list(workspace.rglob("execution-*.json"))
    executions = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    ga = [row for row in executions if row.get("resolution", "").startswith("ag-")]
    lp_count = sum(row.get("resolution", "").startswith("pl-") for row in executions)
    if len(ga) != 60 or lp_count != 6:
        raise ValueError(f"expected 60 GA and 6 LP records; found {len(ga)} GA and {lp_count} LP")

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    generation_count = 0
    for execution in ga:
        validate_trace(execution)
        generation_count += len(execution["objective_components_by_generation"])
        groups[(execution["resolution"], execution["candidate_pool_profile"])].append(execution)
    group_reports = []
    for (method, profile), records in sorted(groups.items()):
        if len(records) != 10:
            raise ValueError(f"expected 10 runs for {method}/{profile}; found {len(records)}")
        components = {}
        for key in COMPONENTS:
            first = [float(row["objective_components_by_generation"][0][key]) for row in records]
            last = [float(row["objective_components_by_generation"][-1][key]) for row in records]
            components[key] = {"first_generation": _summary(first), "final_generation": _summary(last)}
        group_reports.append({"method": method, "profile": profile, "runs": len(records), "component_penalties": components})

    output_dir.mkdir(parents=True, exist_ok=False)
    report = {
        "schema_version": "1.0",
        "status": "passed_diagnostic_objective_trace_integrity",
        "source_run_id": source_run_id,
        "source_result_status": source["status"],
        "source_manifest_commit": manifest.get("source_provenance", {}).get("git_commit"),
        "source_manifest_worktree_dirty": manifest.get("source_provenance", {}).get("git_worktree_dirty"),
        "ga_records": len(ga),
        "lp_records": lp_count,
        "generation_records_validated": generation_count,
        "groups": group_reports,
        "interpretation_limits": [
            "The trace decomposes the implemented scalar objective; it does not identify causal mechanisms.",
            "Nutrient values inherit current missing-data and mapping limitations.",
            "All values are diagnostic and are not approved for the manuscript's primary results.",
        ],
    }
    (output_dir / "ga-objective-trace-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": report["status"], "source_run_id": source_run_id,
                      "ga_records": len(ga), "lp_records": lp_count,
                      "generation_records_validated": generation_count,
                      "output": str(output_dir / "ga-objective-trace-audit.json")}, indent=2))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    audit(args.source_run_id, args.output_dir)


if __name__ == "__main__":
    main()
