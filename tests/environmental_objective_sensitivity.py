"""Compare separate environmental-objective endpoints without composite weights."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from diet_optimization.experiments.diagnostics import evaluate_plan
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
from tests.lp_daily_quantity_support_sensitivity import cap_map, daily_quantity_support


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")
OBJECTIVES = (
    "carbon_footprint",
    "water_footprint",
    "ecological_footprint",
)
METHODS = ("LP-Food-capped", "LP-Meal")


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    context = build_context({
        "tbca_map": str(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"),
        "tbca_db": str(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"),
        "footprint_map": str(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"),
    })
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    rows: list[dict[str, Any]] = []
    profile_inputs: dict[str, Any] = {}

    for profile in PROFILES:
        source = load_json_file(PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json")
        plans, removals = prepare_profile_diets(source, profile, exclusions[profile])
        support = daily_quantity_support(plans)
        observed_max_caps = cap_map(support, "observed_max")
        allowed_names = food_names_in_diets(plans)
        profile_inputs[profile] = {
            "source_plan_count": len(source),
            "eligible_candidate_name_count": len(allowed_names),
            "mapped_daily_cap_count": len(observed_max_caps),
            "removed_occurrence_count": len(removals),
            "lp_food_quantity_cap": "profile-specific observed maximum daily quantity per food",
            "lp_meal_constraint": "selects intact source meals with the current required meal-type counts and energy shares",
        }

        for method in METHODS:
            for objective in OBJECTIVES:
                solver: dict[str, Any] = {}
                if method == "LP-Food-capped":
                    solution = optimize_food_level(
                        context,
                        allowed_food_names=allowed_names,
                        footprint_key=objective,
                        diagnostics=solver,
                        minimum_goals=protocol["minimum_goals"],
                        maximum_goals=protocol["maximum_goals"],
                        maximum_daily_grams_by_food=observed_max_caps,
                    )
                else:
                    solution = optimize_meal_level(
                        plans,
                        context,
                        footprint_key=objective,
                        diagnostics=solver,
                        minimum_goals=protocol["minimum_goals"],
                        maximum_goals=protocol["maximum_goals"],
                    )
                final_plan = solution[0] if solution else None
                metrics = evaluate_plan(
                    final_plan, context,
                    minimum_goals=protocol["minimum_goals"],
                    maximum_goals=protocol["maximum_goals"],
                    protocol_id=protocol["protocol_id"],
                    data_quality_fields=set(protocol["minimum_goals"])
                    | set(protocol["maximum_goals"]),
                ) if final_plan else None
                selected_foods: set[str] = set()
                for day in (final_plan or {}).values():
                    if not isinstance(day, dict):
                        continue
                    for meal_or_items in day.values():
                        item_lists = (
                            meal_or_items.values()
                            if isinstance(meal_or_items, dict)
                            else [meal_or_items]
                        )
                        for items in item_lists:
                            if isinstance(items, list):
                                selected_foods.update(
                                    item["alimento"] for item in items
                                    if isinstance(item, dict)
                                    and isinstance(item.get("alimento"), str)
                                )
                rows.append({
                    "profile": profile,
                    "method": method,
                    "objective": objective,
                    "status": "solution_returned" if final_plan else "no_solution",
                    "selected_food_count": len(selected_foods),
                    "solver": solver,
                    "mean_daily_footprints": metrics.get("mean_daily_footprints") if metrics else None,
                    "nutrient_data_coverage": metrics.get("nutrient_data_coverage") if metrics else None,
                    "mean_daily_violations": metrics.get("mean_daily_violations") if metrics else None,
                    "violation_count": metrics.get("violation_count") if metrics else None,
                    "final_solution": solution,
                })

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_environmental_maps_unadjudicated",
        "protocol_id": protocol["protocol_id"],
        "source_provenance": source_provenance(),
        "objectives": list(OBJECTIVES),
        "methods": list(METHODS),
        "weighting": "No composite objective weights were invented; each endpoint is optimized independently.",
        "comparability_warning": "LP-Food uses profile-specific observed-maximum daily caps and has no meal slots. LP-Meal selects intact meals with meal-type constraints. Their endpoints are not directly comparable as a causal method ranking.",
        "data_warning": "Environmental food pairings and nutrient mappings are not fully adjudicated; missing nutrient fields in current calculations may be scored as zero. All values remain diagnostic and must not be transferred to the manuscript.",
        "profile_inputs": profile_inputs,
        "results": rows,
    }
    path = output_dir / "environmental-objective-sensitivity.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "result_count": len(rows),
        "statuses": [{
            "profile": row["profile"], "method": row["method"],
            "objective": row["objective"], "status": row["status"],
            "fallback_used": row["solver"].get("fallback_used"),
            "nonzero_slacks": row["solver"].get("slack_analysis", {}).get("nonzero_slack_count"),
        } for row in rows],
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
