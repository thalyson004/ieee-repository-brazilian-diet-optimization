"""Stress-test LP endpoints across observed official POF-row coefficient ranges."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.experiments.runner import source_provenance
from diet_optimization.optimization.linear_optimizer import (
    food_names_in_diets,
    optimize_food_level,
    optimize_meal_level,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.optimization.utils import load_json_file
from tests.environmental_source_audit import (
    METRICS,
    PROJECT_ROOT,
    SOURCE_SHA256,
    fetch_pinned_workbook,
    parse_official_preparation_sheet,
)
from tests.lp_daily_quantity_support_sensitivity import cap_map, daily_quantity_support
from diet_optimization.experiments.diagnostics import evaluate_plan


PROFILES = ("regular", "vegetariana", "vegana")
METHODS = ("LP-Food-capped", "LP-Meal")


def source_range_maps(
    distributed: dict[str, dict[str, float]],
    source_values: dict[str, list[tuple[float, float, float]]],
    metric: str,
) -> dict[str, dict[str, Any]]:
    """Return current, min, and max maps for one metric, changing ambiguous labels only."""
    metric_index = next(index for name, index, _unit in METRICS if name == metric)
    current = copy.deepcopy(distributed)
    lower = copy.deepcopy(distributed)
    upper = copy.deepcopy(distributed)
    changed = 0
    for name, official_rows in source_values.items():
        if name not in distributed:
            continue
        values = [row[metric_index] for row in official_rows]
        if len(set(values)) <= 1:
            continue
        lower[name][metric] = min(values)
        upper[name][metric] = max(values)
        changed += 1
    return {"current": current, "source_min": lower, "source_max": upper,
            "changed_ambiguous_labels": changed}


def _map_digest(mapping: dict[str, Any]) -> str:
    payload = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def summarize_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize each within-method/profile/objective source-row envelope."""
    summaries: list[dict[str, Any]] = []
    for profile in PROFILES:
        for method in METHODS:
            for metric, _index, unit in METRICS:
                rows = {
                    row["coefficient_scenario"]: row
                    for row in results
                    if row["profile"] == profile
                    and row["method"] == method
                    and row["objective"] == metric
                }
                if set(rows) != {"current", "source_min", "source_max"}:
                    raise ValueError(f"Incomplete range scenarios for {profile}/{method}/{metric}")
                values = {
                    scenario: rows[scenario]["mean_daily_footprints"][metric]
                    for scenario in ("current", "source_min", "source_max")
                }
                if any(value is None or not math.isfinite(float(value)) for value in values.values()):
                    raise ValueError(f"Non-finite objective score for {profile}/{method}/{metric}")
                canonical_plans = {
                    scenario: json.dumps(rows[scenario]["final_solution"], sort_keys=True, ensure_ascii=False)
                    for scenario in values
                }
                summaries.append({
                    "profile": profile,
                    "method": method,
                    "objective": metric,
                    "unit": unit,
                    "source_min_score": values["source_min"],
                    "current_score": values["current"],
                    "source_max_score": values["source_max"],
                    "optimized_endpoint_score_min": min(values["source_min"], values["source_max"]),
                    "optimized_endpoint_score_max": max(values["source_min"], values["source_max"]),
                    "selected_plan_unchanged_across_scenarios": len(set(canonical_plans.values())) == 1,
                    "fallback_scenarios": [
                        scenario for scenario, row in rows.items()
                        if row["solver"].get("fallback_used")
                    ],
                    "nonzero_slack_count_by_scenario": {
                        scenario: rows[scenario]["solver"].get("slack_analysis", {}).get("nonzero_slack_count")
                        for scenario in rows
                    },
                })
    return summaries


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    maps_dir = output_dir / "scenario_maps"
    maps_dir.mkdir()
    workbook = fetch_pinned_workbook()
    source_values = parse_official_preparation_sheet(workbook)
    source_map = load_json_file(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json")
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    scenario_maps: dict[str, dict[str, Any]] = {}
    scenario_paths: dict[str, Path] = {}
    scenario_info: dict[str, dict[str, Any]] = {}
    for metric, _index, _unit in METRICS:
        variants = source_range_maps(source_map, source_values, metric)
        for scenario in ("current", "source_min", "source_max"):
            variant_id = f"{metric}__{scenario}"
            mapping = variants[scenario]
            scenario_maps[variant_id] = mapping
            if scenario == "current":
                scenario_paths[variant_id] = PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"
            else:
                path = maps_dir / f"{variant_id}.json"
                path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                scenario_paths[variant_id] = path
            scenario_info[variant_id] = {
                "metric_varied": metric,
                "coefficient_scenario": scenario,
                "changed_ambiguous_labels": 0 if scenario == "current" else variants["changed_ambiguous_labels"],
                "map_sha256": _map_digest(mapping),
                "map_file": str(scenario_paths[variant_id]),
            }

    profile_data: dict[str, dict[str, Any]] = {}
    for profile in PROFILES:
        plans, removals = prepare_profile_diets(
            load_json_file(PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json"),
            profile,
            exclusions[profile],
        )
        support = daily_quantity_support(plans)
        profile_data[profile] = {
            "plans": plans,
            "exclusions": removals,
            "allowed_foods": food_names_in_diets(plans),
            "food_caps": cap_map(support, "observed_max"),
        }

    results: list[dict[str, Any]] = []
    context_cache: dict[str, Any] = {}
    for metric, _index, _unit in METRICS:
        for source_scenario in ("current", "source_min", "source_max"):
            variant_id = f"{metric}__{source_scenario}"
            context = context_cache.get(variant_id)
            if context is None:
                context = build_context({
                    "tbca_map": str(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"),
                    "tbca_db": str(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"),
                    "footprint_map": str(scenario_paths[variant_id]),
                })
                context_cache[variant_id] = context
            for profile in PROFILES:
                data = profile_data[profile]
                for method in METHODS:
                    diagnostics: dict[str, Any] = {}
                    if method == "LP-Food-capped":
                        solutions = optimize_food_level(
                            context,
                            allowed_food_names=data["allowed_foods"],
                            footprint_key=metric,
                            diagnostics=diagnostics,
                            minimum_goals=protocol["minimum_goals"],
                            maximum_goals=protocol["maximum_goals"],
                            maximum_daily_grams_by_food=data["food_caps"],
                        )
                    else:
                        solutions = optimize_meal_level(
                            data["plans"], context,
                            footprint_key=metric,
                            diagnostics=diagnostics,
                            minimum_goals=protocol["minimum_goals"],
                            maximum_goals=protocol["maximum_goals"],
                        )
                    final_plan = solutions[0] if solutions else None
                    metrics = evaluate_plan(
                        final_plan, context,
                        minimum_goals=protocol["minimum_goals"],
                        maximum_goals=protocol["maximum_goals"],
                        protocol_id=protocol["protocol_id"],
                        data_quality_fields=set(protocol["minimum_goals"])
                        | set(protocol["maximum_goals"]),
                    ) if final_plan else None
                    results.append({
                        "profile": profile,
                        "method": method,
                        "objective": metric,
                        "coefficient_scenario": source_scenario,
                        "status": "solution_returned" if final_plan else "no_solution",
                        "mean_daily_footprints": metrics.get("mean_daily_footprints") if metrics else None,
                        "mean_daily_violations": metrics.get("mean_daily_violations") if metrics else None,
                        "violation_count": metrics.get("violation_count") if metrics else None,
                        "solver": diagnostics,
                        "final_solution": solutions,
                    })

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_source_row_outer_envelope_not_probability_interval",
        "protocol_id": protocol["protocol_id"],
        "source_provenance": source_provenance(),
        "official_workbook_sha256": hashlib.sha256(workbook).hexdigest(),
        "expected_official_workbook_sha256": SOURCE_SHA256,
        "coefficient_rule": "For the active objective only, ambiguous labels use the minimum or maximum exact source value among rows sharing the standardized preparation label; unambiguous labels retain the distributed value. Other footprint fields remain unchanged.",
        "envelope_warning": "Per-label extrema form a source-supported outer envelope, not a probabilistic interval or necessarily a joint realized map. Multiple POF source rows can reflect different foods, production locations, and system boundaries; no row is adjudicated by this sensitivity.",
        "method_warning": "LP-Food uses profile-specific observed-maximum daily food caps and no meal slots. LP-Meal selects complete source meals. Compare endpoints within method/profile only; do not infer causal rankings.",
        "scenario_maps": scenario_info,
        "within_method_profile_objective_summary": summarize_results(results),
        "results": results,
    }
    path = output_dir / "environmental-source-range-sensitivity.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "result_count": len(results),
        "map_scenarios": {
            key: {"changed_ambiguous_labels": value["changed_ambiguous_labels"],
                  "sha256": value["map_sha256"]}
            for key, value in scenario_info.items()
        },
        "solution_statuses": [{
            "profile": row["profile"], "method": row["method"],
            "objective": row["objective"], "coefficient_scenario": row["coefficient_scenario"],
            "status": row["status"], "fallback_used": row["solver"].get("fallback_used"),
            "nonzero_slacks": row["solver"].get("slack_analysis", {}).get("nonzero_slack_count"),
        } for row in results],
        "within_method_profile_objective_summary": report["within_method_profile_objective_summary"],
        "output": str(path),
    }, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    run(parse_args().output_dir)


if __name__ == "__main__":
    main()
