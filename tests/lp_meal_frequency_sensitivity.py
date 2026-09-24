"""Test empirical repeat-frequency limits for the profile-specific LP-Meal."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.experiments.runner import source_provenance
from diet_optimization.optimization.data_types import NutritionalContext
from diet_optimization.optimization.hyperparameters import DAYS_PER_PLAN
from diet_optimization.optimization.linear_optimizer import (
    _unique_meal_signature,
    optimize_meal_level,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.optimization.utils import load_json_file
from tests.lp_food_diversity_sensitivity import observed_order_statistic
from diet_optimization.experiments.diagnostics import evaluate_plan


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")


def source_max_repetitions_by_plan(plans: list[dict[str, Any]]) -> list[int]:
    """Maximum within-slot frequency of one exact recipe, by source plan."""
    maxima: list[int] = []
    for plan in plans:
        repetitions: Counter[tuple[str, tuple[tuple[str, float], ...]]] = Counter()
        for day in plan.values():
            if not isinstance(day, dict):
                continue
            for meal_type, items in day.items():
                if isinstance(items, list) and items:
                    repetitions[(meal_type, _unique_meal_signature(items))] += 1
        maxima.append(max(repetitions.values(), default=0))
    return maxima


def plan_max_repetitions(plan: dict[str, Any]) -> int:
    counts: Counter[tuple[str, tuple[tuple[str, float], ...]]] = Counter()
    for day in plan.values():
        if not isinstance(day, dict):
            continue
        for meal_type, items in day.items():
            if isinstance(items, list) and items:
                counts[(meal_type, _unique_meal_signature(items))] += 1
    return max(counts.values(), default=0)


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    context: NutritionalContext = build_context({
        "tbca_map": str(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"),
        "tbca_db": str(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"),
        "footprint_map": str(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"),
    })
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    support_by_profile: dict[str, Any] = {}
    results: list[dict[str, Any]] = []

    for profile in PROFILES:
        source = load_json_file(PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json")
        plans, removals = prepare_profile_diets(source, profile, exclusions[profile])
        observed = source_max_repetitions_by_plan(plans)
        q95 = max(1, observed_order_statistic(observed, 0.95))
        support_by_profile[profile] = {
            "source_plan_count": len(plans),
            "days_per_plan": DAYS_PER_PLAN,
            "source_plan_maximum_repeat_min": min(observed),
            "source_plan_maximum_repeat_median": observed_order_statistic(observed, 0.50),
            "source_plan_maximum_repeat_q95_order_statistic": q95,
            "source_plan_maximum_repeat_max": max(observed),
            "profile_excluded_occurrence_count": len(removals),
            "repeat_cap_interpretation": "q95 is the lower order statistic of each source plan's most repeated exact meal within a meal slot; not a clinical frequency rule",
        }
        scenarios: list[tuple[str, int | None]] = [
            ("unbounded_repetition", None),
            ("at_most_once_per_five_day_plan", 1),
            ("profile_source_q95", q95),
        ]
        for scenario, repeat_cap in scenarios:
            solver: dict[str, Any] = {}
            solutions = optimize_meal_level(
                plans,
                context,
                footprint_key="carbon_footprint",
                days_per_plan=DAYS_PER_PLAN,
                diagnostics=solver,
                minimum_goals=protocol["minimum_goals"],
                maximum_goals=protocol["maximum_goals"],
                maximum_repetitions_per_unique_meal=repeat_cap,
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
            observed_output_max = plan_max_repetitions(final_plan) if final_plan else None
            results.append({
                "profile": profile,
                "scenario": scenario,
                "repeat_cap": repeat_cap,
                "status": "solution_returned" if final_plan else "no_solution",
                "output_maximum_repeat": observed_output_max,
                "repeat_cap_respected": (
                    observed_output_max <= repeat_cap
                    if final_plan and repeat_cap is not None else None
                ),
                "solver": solver,
                "mean_daily_footprints": metrics.get("mean_daily_footprints") if metrics else None,
                "mean_daily_violations": metrics.get("mean_daily_violations") if metrics else None,
                "violation_count": metrics.get("violation_count") if metrics else None,
                "nutrient_data_coverage": metrics.get("nutrient_data_coverage") if metrics else None,
                "final_solution": solutions,
            })

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_meal_frequency_sensitivity",
        "protocol_id": protocol["protocol_id"],
        "source_provenance": source_provenance(),
        "candidate_identity": "exact food names and aggregated quantities within each meal slot; duplicate source meals are deduplicated only in capped scenarios",
        "scenarios": ["no repetition cap", "maximum one appearance in five days", "profile-specific observed q95 of source-plan max repetition"],
        "profile_source_support": support_by_profile,
        "interpretation_warning": "A frequency cap is a computational sensitivity, not a dietary recommendation. It does not resolve uncertain recipes, mapping, missing nutrients, or LP/GA comparability; all results are diagnostic.",
        "results": results,
    }
    path = output_dir / "lp-meal-frequency-sensitivity.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "scenario_count": len(results),
        "profile_q95_caps": {
            profile: support["source_plan_maximum_repeat_q95_order_statistic"]
            for profile, support in support_by_profile.items()
        },
        "results": [{
            "profile": row["profile"],
            "scenario": row["scenario"],
            "status": row["status"],
            "repeat_cap": row["repeat_cap"],
            "output_maximum_repeat": row["output_maximum_repeat"],
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
    run(parse_args().output_dir)


if __name__ == "__main__":
    main()
