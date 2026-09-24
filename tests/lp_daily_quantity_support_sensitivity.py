"""Run diagnostic LP-Food daily quantity-cap scenarios from source-diet support."""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.experiments.runner import source_provenance
from diet_optimization.experiments.diagnostics import evaluate_plan
from diet_optimization.optimization.linear_optimizer import food_names_in_diets, optimize_food_level
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.optimization.utils import load_json_file, parse_quantity_in_grams


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")
ROBUST_PERCENTILE_MIN_POSITIVE_DAYS = 20


def daily_quantity_support(plans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize per-food daily grams, including source days where the food is absent."""
    all_days: list[tuple[int, dict[str, float]]] = []
    food_plan_ids: defaultdict[str, set[int]] = defaultdict(set)
    for plan_index, plan in enumerate(plans, start=1):
        for day in plan.values():
            if not isinstance(day, dict):
                continue
            totals: defaultdict[str, float] = defaultdict(float)
            for items in day.values():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or not isinstance(item.get("alimento"), str):
                        continue
                    grams = parse_quantity_in_grams(item.get("quantidade", 0))
                    if grams <= 0 or not math.isfinite(grams):
                        continue
                    name = item["alimento"]
                    totals[name] += grams
                    food_plan_ids[name].add(plan_index)
            all_days.append((plan_index, dict(totals)))

    rows: list[dict[str, Any]] = []
    for name in sorted(food_plan_ids):
        positive_daily_grams = [
            totals.get(name, 0.0) for _plan_index, totals in all_days
            if totals.get(name, 0.0) > 0
        ]
        if not positive_daily_grams:
            continue
        percentile_cap = (
            float(np.percentile(positive_daily_grams, 95))
            if len(positive_daily_grams) >= ROBUST_PERCENTILE_MIN_POSITIVE_DAYS
            else max(positive_daily_grams)
        )
        rows.append({
            "food_original": name,
            "source_plans_with_food": len(food_plan_ids[name]),
            "source_days": len(all_days),
            "positive_days": len(positive_daily_grams),
            "minimum_positive_daily_g": round(min(positive_daily_grams), 6),
            "observed_max_daily_g": round(max(positive_daily_grams), 6),
            "p95_positive_daily_g": round(float(np.percentile(positive_daily_grams, 95)), 6)
            if len(positive_daily_grams) >= ROBUST_PERCENTILE_MIN_POSITIVE_DAYS else None,
            "p95_cap_g": round(percentile_cap, 6),
            "p95_cap_basis": "positive_day_p95" if len(positive_daily_grams) >= ROBUST_PERCENTILE_MIN_POSITIVE_DAYS
            else "observed_max_fallback_below_20_positive_days",
        })
    return rows


def cap_map(rows: list[dict[str, Any]], scenario: str) -> dict[str, float]:
    if scenario == "observed_max":
        return {row["food_original"]: float(row["observed_max_daily_g"]) for row in rows}
    if scenario == "p95_positive_or_max_fallback":
        return {row["food_original"]: float(row["p95_cap_g"]) for row in rows}
    raise ValueError(f"Unsupported quantity-cap scenario: {scenario}")


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    context = build_context({
        "tbca_map": str(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"),
        "tbca_db": str(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"),
        "footprint_map": str(PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"),
    })
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    rows_by_profile: dict[str, list[dict[str, Any]]] = {}
    results: list[dict[str, Any]] = []

    for profile in PROFILES:
        source_path = PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json"
        source_plans = load_json_file(source_path)
        plans, removals = prepare_profile_diets(source_plans, profile, exclusions[profile])
        support_rows = daily_quantity_support(plans)
        rows_by_profile[profile] = support_rows
        allowed_food_names = food_names_in_diets(plans)

        scenarios: list[tuple[str, dict[str, float]]] = [
            ("unbounded", {}),
            ("observed_max", cap_map(support_rows, "observed_max")),
            ("p95_positive_or_max_fallback", cap_map(support_rows, "p95_positive_or_max_fallback")),
        ]
        for scenario, caps in scenarios:
            solver_diagnostics: dict[str, Any] = {}
            solution = optimize_food_level(
                context,
                allowed_food_names=allowed_food_names,
                footprint_key="carbon_footprint",
                diagnostics=solver_diagnostics,
                minimum_goals=protocol["minimum_goals"],
                maximum_goals=protocol["maximum_goals"],
                maximum_daily_grams_by_food=caps or None,
            )
            final_plan = solution[0] if solution else None
            selected_names = {
                item.get("alimento")
                for day in (final_plan or {}).values()
                for meal in day.values()
                for item in meal if isinstance(item, dict)
            }
            results.append({
                "profile": profile,
                "scenario": scenario,
                "status": "solution_returned" if final_plan else "no_solution",
                "input_exclusion_count": len(removals),
                "candidate_food_count": len(allowed_food_names),
                "selected_food_count": len(selected_names),
                "selected_foods_with_no_source_daily_support": sorted(selected_names - set(cap_map(support_rows, "observed_max"))),
                "selected_foods_over_scenario_cap": sorted(
                    name for name in selected_names
                    if name in caps and any(
                        float(item.get("quantidade", 0)) > caps[name] + 0.11
                        for day in (final_plan or {}).values()
                        for meal in day.values()
                        for item in meal if item.get("alimento") == name
                    )
                ),
                "solver": solver_diagnostics,
                "metrics_and_violations": evaluate_plan(
                    final_plan, context,
                    minimum_goals=protocol["minimum_goals"],
                    maximum_goals=protocol["maximum_goals"],
                    protocol_id=protocol["protocol_id"],
                    data_quality_fields=set(protocol["minimum_goals"]) | set(protocol["maximum_goals"]),
                ) if final_plan else None,
                "final_solution": solution,
            })

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_not_a_serving_recommendation",
        "protocol_id": protocol["protocol_id"],
        "source_provenance": source_provenance(),
        "support_unit": "positive total grams of a food per source day, summed across all meal slots",
        "p95_rule": "95th percentile of positive daily totals when at least 20 positive days are observed; otherwise observed maximum is used and explicitly labeled as a low-support fallback",
        "scenarios": ["unbounded", "observed_max", "p95_positive_or_max_fallback"],
        "profile_food_daily_support": rows_by_profile,
        "optimization_results": results,
        "interpretation_warning": "Empirical generated-diet support is not a clinically validated portion range. LP-Food has no meal slots, so these are daily per-food caps, not meal-level bounds. Results remain diagnostic under unresolved mapping, ingredient, missingness, and method-equivalence gates.",
    }
    (output_dir / "lp-daily-quantity-support-sensitivity.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "status": report["status"],
        "profiles": len(PROFILES),
        "support_rows": {profile: len(rows) for profile, rows in rows_by_profile.items()},
        "solver_scenarios": len(results),
        "scenario_statuses": [
            {"profile": row["profile"], "scenario": row["scenario"], "status": row["status"],
             "fallback_used": row["solver"].get("fallback_used"),
             "nonzero_slacks": row["solver"].get("slack_analysis", {}).get("nonzero_slack_count")}
            for row in results
        ],
        "output": str(output_dir / "lp-daily-quantity-support-sensitivity.json"),
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
