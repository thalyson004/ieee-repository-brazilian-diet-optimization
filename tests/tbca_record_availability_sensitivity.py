"""Paired diagnostic sensitivity to a blank current TBCA record page."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tests.ga_sensitivity_review import paired_summary, read_computational_metrics, read_ga_metrics
from tests.validate_candidate_scope import audit_workspace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline-local-snapshot", "current-record-food-excluded")


def execute_variant(variant: str, runs: int, seed: int, nutrition_protocol: str, output_dir: Path) -> Path:
    workspace = output_dir / variant
    command = [
        sys.executable, "-m", "diet_optimization.experiments.runner",
        "--mode", "rerun", "--runs", str(runs), "--seed", str(seed),
        "--nutrition-protocol", nutrition_protocol, "--output-dir", str(workspace),
    ]
    if variant == "current-record-food-excluded":
        command.append("--exclude-tbca-unavailable-record-foods")
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    return workspace


def summarize_metrics(left: dict[tuple, float], right: dict[tuple, float], seed: int) -> list[dict[str, Any]]:
    if set(left) != set(right):
        raise ValueError("Baseline and exclusion variants do not have paired metric keys")
    grouped: dict[tuple[str, str, str], list[tuple[int, float]]] = {}
    for key, value in right.items():
        profile, method, metric, execution_id = key
        grouped.setdefault((profile, method, metric), []).append((execution_id, value - left[key]))
    rows = []
    for group, values in sorted(grouped.items()):
        values.sort()
        expected = list(range(1, len(values) + 1))
        if [execution_id for execution_id, _ in values] != expected:
            raise ValueError(f"Nonconsecutive run IDs for {group}")
        rows.append({
            "profile": group[0], "method": group[1], "metric": group[2],
            **paired_summary([difference for _, difference in values], seed),
        })
    return rows


def run(runs: int, seed: int, nutrition_protocol: str, output_dir: Path) -> dict[str, Any]:
    if runs < 2:
        raise ValueError("At least two paired GA runs are needed for this sensitivity")
    output_dir.mkdir(parents=True, exist_ok=False)
    workspaces = {
        variant: execute_variant(variant, runs, seed, nutrition_protocol, output_dir)
        for variant in VARIANTS
    }
    manifests = {
        key: json.loads((path / "run-manifest.json").read_text(encoding="utf-8"))
        for key, path in workspaces.items()
    }
    provenance = [manifest.get("source_provenance", {}) for manifest in manifests.values()]
    commits = {item.get("git_commit") for item in provenance}
    hashes = [item.get("input_sha256") for item in provenance]
    if len(commits) != 1 or any(item.get("git_worktree_dirty") for item in provenance):
        raise ValueError("Sensitivity variants must share one clean source commit")
    if not hashes[0] or hashes[0] != hashes[1]:
        raise ValueError("Sensitivity variants must use identical hashed inputs")

    scope: dict[str, dict[str, Any]] = {}
    prep: dict[str, Any] = {}
    outcomes = {}
    computational = {}
    lp: dict[str, list[dict[str, Any]]] = {}
    for variant, workspace in workspaces.items():
        audit = audit_workspace(workspace)
        scope[variant] = {
            "status": audit["status"],
            "checked_outputs": audit["checked_outputs"],
            "violations": audit["violations"],
        }
        if audit["status"] != "passed" or audit["checked_outputs"] != 6 * (runs + 1):
            raise ValueError(f"Profile scope validation failed for {variant}")
        report = json.loads((workspace / "input-preparation.json").read_text(encoding="utf-8"))
        prep[variant] = report["tbca_unavailable_record_exclusion_counts_by_profile"]
        expected_enabled = variant == "current-record-food-excluded"
        if report["tbca_unavailable_record_exclusions_enabled"] is not expected_enabled:
            raise ValueError(f"Incorrect record-exclusion flag in {variant}")
        outcomes[variant] = read_ga_metrics(workspace)
        computational[variant] = read_computational_metrics(workspace)
        lp_rows = []
        for method_dir, method in (("pl-alimentos", "LP-Food"), ("pl-refeicoes", "LP-Meal")):
            for profile in ("regular", "vegetariana", "vegana"):
                path = workspace / "data" / "outputs" / "optimization_runs" / method_dir / f"execution-{profile}.json"
                execution = json.loads(path.read_text(encoding="utf-8"))
                lp_rows.append({
                    "method": method, "profile": profile,
                    "solution_present": execution.get("final_solution") is not None,
                    "violation_count": (execution.get("metrics_and_violations") or {}).get("violation_count"),
                    "fallback_used": bool((execution.get("solver") or {}).get("fallback_used", False)),
                })
        lp[variant] = lp_rows

    if prep["baseline-local-snapshot"]["vegan"]["incremental_source_occurrences_removed"] != 0:
        raise ValueError("Baseline unexpectedly excluded the unavailable-source food")
    if prep["current-record-food-excluded"]["vegana"]["incremental_source_occurrences_removed"] != 40:
        raise ValueError("Expected exactly the 40 vegan source occurrences of the flagged food")
    if any(prep["current-record-food-excluded"][p]["incremental_source_occurrences_removed"] for p in ("regular", "vegetariana")):
        raise ValueError("The flagged exclusion must remain vegan-profile-specific")

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_current_tbca_record_availability_sensitivity_not_primary_result",
        "source_git_commit": next(iter(commits)),
        "input_sha256": hashes[0],
        "base_seed": seed,
        "ga_runs_per_profile_and_granularity": runs,
        "nutrition_protocol": nutrition_protocol,
        "excluded_food": "Coco, polpa, in natura",
        "tbca_code": "BRC0013C",
        "profile_scope_validation": scope,
        "preparation_audit": prep,
        "lp_execution_status": lp,
        "paired_ga_outcome_differences": summarize_metrics(
            outcomes[VARIANTS[0]], outcomes[VARIANTS[1]], seed + 201
        ),
        "paired_ga_computational_differences": summarize_metrics(
            computational[VARIANTS[0]], computational[VARIANTS[1]], seed + 202
        ),
        "limitations": [
            "This contrasts the local numeric snapshot with exclusion of one food whose current TBCA page has no table; it does not recover the snapshot version or establish which input is correct.",
            "The exclusion is exact-name and vegan-profile-specific because the 40 source occurrences are all in the vegan input; the base diets are unchanged.",
            "All contrasts remain diagnostic while mapping, nutrition-marker, ingredient eligibility, and method-comparability gates remain open.",
            "Bootstrap intervals are unadjusted across multiple metrics and strata.",
        ],
    }
    result_path = output_dir / "tbca-record-availability-sensitivity.json"
    result_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TBCA record-availability sensitivity: {result_path}")
    return report


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
        "source_git_commit": report["source_git_commit"],
        "runs_per_profile_and_granularity": report["ga_runs_per_profile_and_granularity"],
        "profile_scope_validation": report["profile_scope_validation"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
