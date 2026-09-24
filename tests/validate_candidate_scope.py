"""Audit profile-specific food eligibility in all four optimizer outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


PROFILES = ("regular", "vegetariana", "vegana")
METHODS = {
    "GA-Food": ("ag-alimentos", "stochastic"),
    "GA-Meal": ("ag-refeicoes", "stochastic"),
    "LP-Food": ("pl-alimentos", "single"),
    "LP-Meal": ("pl-refeicoes", "single"),
}


def item_names(value: object) -> set[str]:
    names: set[str] = set()
    if isinstance(value, dict):
        name = value.get("alimento")
        if isinstance(name, str):
            names.add(name)
        for child in value.values():
            names.update(item_names(child))
    elif isinstance(value, list):
        for child in value:
            names.update(item_names(child))
    return names


def plan_from(payload: dict) -> object:
    plan = payload.get("final_solution")
    if isinstance(plan, list) and plan:
        return plan[0]
    return plan


def audit_workspace(workspace: Path) -> dict:
    run_root = workspace / "data" / "outputs" / "optimization_runs"
    records = []
    violations = []
    for profile in PROFILES:
        diets_path = workspace / "data" / "diets" / "base" / f"dietas-{profile}.json"
        diets = json.loads(diets_path.read_text(encoding="utf-8"))
        allowed = item_names(diets)
        if not allowed:
            raise ValueError(f"No source foods found for profile {profile}")
        for method, (resolution, kind) in METHODS.items():
            if kind == "stochastic":
                paths = sorted((run_root / resolution / "runs" / f"dietas-{profile}").glob("execution-*.json"))
            else:
                paths = [run_root / resolution / f"execution-{profile}.json"]
            if not paths or any(not path.is_file() for path in paths):
                raise FileNotFoundError(f"Missing output for {profile}/{method}: {paths}")
            for path in paths:
                payload = json.loads(path.read_text(encoding="utf-8"))
                plan = plan_from(payload)
                if not isinstance(plan, (dict, list)):
                    raise ValueError(f"Missing plan in {path}")
                selected = item_names(plan)
                outside = sorted(selected - allowed)
                record = {
                    "profile": profile,
                    "method": method,
                    "execution_id": payload.get("execution_id", 1),
                    "source_food_count": len(allowed),
                    "selected_unique_food_count": len(selected),
                    "outside_profile_pool": outside,
                    "artifact": str(path.relative_to(workspace)).replace("\\", "/"),
                }
                if method.startswith("GA-") and (
                    "source_diet_file" in payload
                    or "candidate_pool_profile" in payload
                    or "candidate_food_names" in payload
                ):
                    expected_file = f"dietas-{profile}.json"
                    recorded_file = payload.get("source_diet_file")
                    recorded_profile = payload.get("candidate_pool_profile")
                    recorded_candidates = set(payload.get("candidate_food_names", []))
                    if recorded_file != expected_file or (
                        recorded_profile is not None and recorded_profile != profile
                    ):
                        violations.append({**record, "reason": "GA candidate pool profile provenance mismatch"})
                    if recorded_candidates and not recorded_candidates.issubset(allowed):
                        violations.append({**record, "reason": "GA candidate pool contains off-profile foods"})
                if outside:
                    violations.append({**record, "reason": "selected foods outside profile source pool"})
                records.append(record)
    report = {
        "schema_version": "1.0",
        "status": "passed" if not violations else "failed",
        "scope_rule": "all four methods may select foods only from the matching profile's staged base diets",
        "profiles": list(PROFILES),
        "methods": list(METHODS),
        "checked_outputs": len(records),
        "ga_pool_provenance_complete": all(
            "candidate_pool_profile" in json.loads(path.read_text(encoding="utf-8"))
            and "candidate_food_names" in json.loads(path.read_text(encoding="utf-8"))
            for profile in PROFILES
            for resolution in ("ag-alimentos", "ag-refeicoes")
            for path in (run_root / resolution / "runs" / f"dietas-{profile}").glob("execution-*.json")
        ),
        "violations": violations,
        "records": records,
    }
    output = workspace / "article_outputs" / "profile-scope-validation.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    report = audit_workspace(args.workspace.resolve())
    print(f"Checked {report['checked_outputs']} outputs; status={report['status']}")
    if report["violations"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
