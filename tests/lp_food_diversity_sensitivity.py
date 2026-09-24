"""Run profile-specific LP-Food minimum-diversity MILP diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.experiments.runner import source_provenance
from diet_optimization.optimization.linear_optimizer import (
    food_names_in_diets,
    optimize_food_level,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.optimization.utils import load_json_file, parse_quantity_in_grams
from tests.lp_daily_quantity_support_sensitivity import cap_map, daily_quantity_support
from diet_optimization.experiments.diagnostics import evaluate_plan


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")


def source_day_food_counts(plans: list[dict[str, Any]]) -> list[int]:
    """Count distinct positively consumed foods in each source day."""
    counts: list[int] = []
    for plan in plans:
        for day in plan.values():
            if not isinstance(day, dict):
                continue
            names = {
                item["alimento"]
                for meal in day.values() if isinstance(meal, list)
                for item in meal
                if isinstance(item, dict)
                and isinstance(item.get("alimento"), str)
                and parse_quantity_in_grams(item.get("quantidade", 0)) > 0
            }
            counts.append(len(names))
    return counts


def observed_order_statistic(values: list[int], quantile: float) -> int:
    """Use the lower order statistic at floor(q * (n - 1)); no interpolation."""
    if not values:
        raise ValueError("At least one source day is required")
    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be in [0, 1]")
    ordered = sorted(values)
    return ordered[int(quantile * (len(ordered) - 1))]


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    context = build_context({
        "tbca_map": str(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"),
        "tbca_db": str(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"),
        "footprint_map": str(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"),
    })
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    results: list[dict[str, Any]] = []
    profile_support: dict[str, Any] = {}

    for profile in PROFILES:
        source = load_json_file(PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json")
        plans, removals = prepare_profile_diets(source, profile, exclusions[profile])
        counts = source_day_food_counts(plans)
        q25 = observed_order_statistic(counts, 0.25)
        median = observed_order_statistic(counts, 0.50)
        support = daily_quantity_support(plans)
        caps = cap_map(support, "observed_max")
        candidates = food_names_in_diets(plans)
        profile_support[profile] = {
            "source_day_count": len(counts),
            "unique_foods_per_day_min": min(counts),
            "unique_foods_per_day_q25_order_statistic": q25,
            "unique_foods_per_day_median_order_statistic": median,
            "unique_foods_per_day_max": max(counts),
            "minimum_food_floors_tested": sorted({q25, median}),
            "quantity_cap_basis": "per-food observed maximum daily total in this profile",
            "candidate_food_count": len(candidates),
            "excluded_source_occurrences": len(removals),
        }

        scenarios: list[tuple[str, int | None]] = [("observed_max_caps_only", None)]
        scenarios.extend((f"observed_max_caps_min_foods_{floor}", floor)
                         for floor in sorted({q25, median}))
        for scenario, floor in scenarios:
            solver: dict[str, Any] = {}
            solution = optimize_food_level(
                context,
                allowed_food_names=candidates,
                footprint_key="carbon_footprint",
                diagnostics=solver,
                minimum_goals=protocol["minimum_goals"],
                maximum_goals=protocol["maximum_goals"],
                maximum_daily_grams_by_food=caps,
                minimum_selected_foods=floor,
            )
            final_plan = solution[0] if solution else None
            selected = {
                item.get("alimento")
                for day in (final_plan or {}).values()
                for meal in day.values()
                for item in meal if isinstance(item, dict)
            }
            results.append({
                "profile": profile,
                "scenario": scenario,
                "minimum_selected_foods": floor,
                "status": "solution_returned" if final_plan else "no_solution",
                "selected_food_count": len(selected),
                "selected_foods": sorted(selected),
                "selected_foods_over_observed_max_cap": sorted(
                    name for name in selected
                    if any(
                        float(item.get("quantidade", 0)) > caps[name] + 0.11
                        for day in (final_plan or {}).values()
                        for meal in day.values()
                        for item in meal if item.get("alimento") == name
                    )
                ),
                "solver": solver,
                "metrics_and_violations": evaluate_plan(
                    final_plan, context,
                    minimum_goals=protocol["minimum_goals"],
                    maximum_goals=protocol["maximum_goals"],
                    protocol_id=protocol["protocol_id"],
                    data_quality_fields=set(protocol["minimum_goals"])
                    | set(protocol["maximum_goals"]),
                ) if final_plan else None,
                "final_solution": solution,
            })

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_not_a_meal_plan_or_serving_recommendation",
        "model": "mixed_integer_food_level_basket_with_daily_caps_and_optional_cardinality_floor",
        "protocol_id": protocol["protocol_id"],
        "source_provenance": source_provenance(),
        "diversity_rule": "minimum distinct foods with quantity >= 1 g; floors are profile-specific q25 and median lower order statistics from source-day counts",
        "quantity_cap_rule": "per-food maximum positive daily total observed in that profile's source plans, summed across meal slots",
        "interpretation_warning": "This aggregate daily basket has no meal slots, recipe compatibility, frequency rule, or clinical serving interpretation. It is a diagnostic MILP sensitivity under unresolved mapping, ingredient, missingness, and method-equivalence gates.",
        "profile_source_support": profile_support,
        "optimization_results": results,
    }
    path = output_dir / "lp-food-diversity-sensitivity.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "scenario_count": len(results),
        "results": [{
            "profile": row["profile"],
            "scenario": row["scenario"],
            "status": row["status"],
            "selected_food_count": row["selected_food_count"],
            "fallback_used": row["solver"].get("fallback_used"),
            "nonzero_slacks": row["solver"].get("slack_analysis", {}).get("nonzero_slack_count"),
        } for row in results],
        "output": str(path),
    }, ensure_ascii=False, indent=2))
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
