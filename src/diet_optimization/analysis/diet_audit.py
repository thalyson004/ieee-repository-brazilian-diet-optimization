#!/usr/bin/env python3
"""Audit the 150 archived LLM-generated base diets without modifying them."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from diet_optimization.optimization.data_types import NutritionalContext
from diet_optimization.optimization.hyperparameters import (
    MAXIMUM_GOALS,
    MEAL_ORDER,
    MINIMUM_GOALS,
)
from diet_optimization.optimization.utils import calculate_totals


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROFILE_FILES = {
    "regular": "dietas-regular.json",
    "vegetarian": "dietas-vegetariana.json",
    "vegan": "dietas-vegana.json",
}
EXPECTED_DAYS = tuple(str(index) for index in range(1, 6))
MAX_SCREENING_QUANTITY_GRAMS = 1000.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_quantity(raw: Any) -> tuple[float | None, str]:
    if raw is None or isinstance(raw, bool):
        return None, "missing_or_boolean"
    try:
        value = float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        return None, "non_numeric"
    if value <= 0:
        return value, "non_positive"
    if value > MAX_SCREENING_QUANTITY_GRAMS:
        return value, "above_screening_threshold"
    return value, "valid"


def write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def audit(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    name_to_tbca = load_json(PROJECT_ROOT / "maps" / "base" / "mapa-nome-tbca.json")
    generated_to_tbca_name = load_json(
        PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-nome.json"
    )
    generated_to_tbca_code = load_json(
        PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json"
    )
    footprint_map = load_json(
        PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json"
    )
    tbca_database = load_json(
        PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json"
    )
    context = NutritionalContext(
        tbca_map=generated_to_tbca_code,
        tbca_database=tbca_database,
        footprint_map=footprint_map,
    )
    shared_targets = Counter(generated_to_tbca_name.values())

    item_rows: list[dict[str, Any]] = []
    plan_rows: list[dict[str, Any]] = []
    nutrient_rows: list[dict[str, Any]] = []
    file_evidence: list[dict[str, Any]] = []
    total_occurrences = 0

    for profile, filename in PROFILE_FILES.items():
        diet_path = PROJECT_ROOT / "diets-base" / filename
        plans = load_json(diet_path)
        file_evidence.append(
            {
                "profile": profile,
                "path": diet_path.relative_to(PROJECT_ROOT).as_posix(),
                "sha256": sha256(diet_path),
                "json_valid": True,
                "plan_count": len(plans) if isinstance(plans, list) else 0,
            }
        )
        if not isinstance(plans, list):
            continue

        for plan_index, plan in enumerate(plans, start=1):
            schema_issues: list[str] = []
            missing_days: list[str] = []
            unexpected_days: list[str] = []
            missing_meals: list[str] = []
            unexpected_meals: list[str] = []
            invalid_items = 0
            invalid_quantities = 0
            screened_large_quantities = 0
            duplicate_items = 0
            unmapped_tbca = 0
            unmapped_footprint = 0
            all_items: list[dict[str, Any]] = []

            if not isinstance(plan, dict):
                schema_issues.append("plan_not_object")
                plan = {}

            missing_days = sorted(set(EXPECTED_DAYS) - set(plan))
            unexpected_days = sorted(set(plan) - set(EXPECTED_DAYS))
            if missing_days:
                schema_issues.append("missing_days")
            if unexpected_days:
                schema_issues.append("unexpected_days")

            for day in EXPECTED_DAYS:
                meals = plan.get(day, {})
                if not isinstance(meals, dict):
                    schema_issues.append(f"day_{day}_not_object")
                    continue
                day_missing = sorted(set(MEAL_ORDER) - set(meals))
                day_unexpected = sorted(set(meals) - set(MEAL_ORDER))
                missing_meals.extend(f"{day}:{meal}" for meal in day_missing)
                unexpected_meals.extend(f"{day}:{meal}" for meal in day_unexpected)
                if day_missing:
                    schema_issues.append(f"day_{day}_missing_meals")
                if day_unexpected:
                    schema_issues.append(f"day_{day}_unexpected_meals")

                for meal in MEAL_ORDER:
                    items = meals.get(meal, [])
                    if not isinstance(items, list):
                        schema_issues.append(f"day_{day}_{meal}_not_list")
                        continue
                    names_in_meal: Counter[str] = Counter()
                    for item_index, item in enumerate(items, start=1):
                        total_occurrences += 1
                        if not isinstance(item, dict):
                            invalid_items += 1
                            schema_issues.append("item_not_object")
                            continue
                        food_name = item.get("alimento")
                        if not isinstance(food_name, str) or not food_name.strip():
                            invalid_items += 1
                            food_name = ""
                        quantity, quantity_status = parse_quantity(item.get("quantidade"))
                        if quantity_status in {"missing_or_boolean", "non_numeric", "non_positive"}:
                            invalid_quantities += 1
                        elif quantity_status == "above_screening_threshold":
                            screened_large_quantities += 1

                        names_in_meal[food_name] += 1
                        normalized_name = generated_to_tbca_name.get(food_name)
                        tbca_code = generated_to_tbca_code.get(food_name)
                        tbca_record_exists = bool(tbca_code and tbca_code in tbca_database)
                        footprint_exists = food_name in footprint_map
                        exact_tbca_name_exists = food_name in name_to_tbca
                        if not tbca_record_exists:
                            unmapped_tbca += 1
                        if not footprint_exists:
                            unmapped_footprint += 1
                        if food_name and quantity is not None and quantity > 0:
                            all_items.append(item)

                        item_rows.append(
                            {
                                "profile": profile,
                                "plan_index": plan_index,
                                "day": day,
                                "meal": meal,
                                "item_index": item_index,
                                "food_original": food_name,
                                "quantity_raw": item.get("quantidade"),
                                "quantity_grams": quantity,
                                "quantity_status": quantity_status,
                                "tbca_name_normalized": normalized_name,
                                "tbca_code": tbca_code,
                                "tbca_record_exists": tbca_record_exists,
                                "food_name_is_exact_tbca_name": exact_tbca_name_exists,
                                "environmental_mapping_exists": footprint_exists,
                                "mapping_target_source_count": (
                                    shared_targets.get(normalized_name, 0) if normalized_name else 0
                                ),
                                "potentially_unmapped_or_hallucinated": not tbca_record_exists,
                            }
                        )
                    duplicate_items += sum(count - 1 for count in names_in_meal.values() if count > 1)

            nutrient_totals, footprint_totals = calculate_totals(all_items, context)
            average_daily = {
                nutrient: value / len(EXPECTED_DAYS)
                for nutrient, value in nutrient_totals.items()
            }
            violations = 0
            for nutrient, target in MINIMUM_GOALS.items():
                actual = float(average_daily.get(nutrient, 0.0))
                violated = actual < target
                violations += int(violated)
                nutrient_rows.append(
                    {
                        "profile": profile,
                        "plan_index": plan_index,
                        "nutrient": nutrient,
                        "rule": "minimum",
                        "target": target,
                        "actual_daily_mean": actual,
                        "absolute_violation": max(0.0, target - actual),
                        "relative_violation": max(0.0, target - actual) / target,
                        "violated": violated,
                    }
                )
            for nutrient, specification in MAXIMUM_GOALS.items():
                limit = specification["meta"] * specification["tolerancia"]
                actual = float(average_daily.get(nutrient, 0.0))
                violated = actual > limit
                violations += int(violated)
                nutrient_rows.append(
                    {
                        "profile": profile,
                        "plan_index": plan_index,
                        "nutrient": nutrient,
                        "rule": "maximum",
                        "target": limit,
                        "actual_daily_mean": actual,
                        "absolute_violation": max(0.0, actual - limit),
                        "relative_violation": max(0.0, actual - limit) / limit,
                        "violated": violated,
                    }
                )

            plan_rows.append(
                {
                    "profile": profile,
                    "plan_index": plan_index,
                    "schema_valid": not schema_issues,
                    "schema_issues": "|".join(sorted(set(schema_issues))),
                    "missing_days": "|".join(missing_days),
                    "unexpected_days": "|".join(unexpected_days),
                    "missing_meals": "|".join(missing_meals),
                    "unexpected_meals": "|".join(unexpected_meals),
                    "invalid_items": invalid_items,
                    "invalid_quantities": invalid_quantities,
                    "quantities_above_1000g_screening_threshold": screened_large_quantities,
                    "duplicate_items_within_meal": duplicate_items,
                    "unmapped_tbca_items": unmapped_tbca,
                    "unmapped_environmental_items": unmapped_footprint,
                    "nutritional_target_violations": violations,
                    "mean_daily_carbon_footprint": footprint_totals["carbon_footprint"]
                    / len(EXPECTED_DAYS),
                }
            )

    write_csv(output_dir / "diet_audit_items.csv", item_rows, list(item_rows[0]))
    write_csv(output_dir / "diet_audit_plans.csv", plan_rows, list(plan_rows[0]))
    write_csv(output_dir / "diet_audit_nutrients.csv", nutrient_rows, list(nutrient_rows[0]))

    unique_foods = {row["food_original"] for row in item_rows if row["food_original"]}
    used_targets = {
        food: generated_to_tbca_name.get(food)
        for food in unique_foods
        if generated_to_tbca_name.get(food)
    }
    target_to_used_sources: dict[str, set[str]] = {}
    for source, target in used_targets.items():
        target_to_used_sources.setdefault(target, set()).add(source)
    by_profile = {}
    for profile in PROFILE_FILES:
        profile_plans = [row for row in plan_rows if row["profile"] == profile]
        by_profile[profile] = {
            "plans": len(profile_plans),
            "schema_valid": sum(bool(row["schema_valid"]) for row in profile_plans),
            "nutritional_target_violations": sum(
                int(row["nutritional_target_violations"]) for row in profile_plans
            ),
        }
    violations_by_nutrient = Counter(
        row["nutrient"] for row in nutrient_rows if row["violated"]
    )
    summary = {
        "schema_version": "1.0",
        "scope": "archived normalized diet files; raw API responses were not preserved",
        "files": file_evidence,
        "totals": {
            "profiles": len(PROFILE_FILES),
            "plans": len(plan_rows),
            "plans_with_valid_schema": sum(bool(row["schema_valid"]) for row in plan_rows),
            "food_occurrences": total_occurrences,
            "unique_food_names": len(unique_foods),
            "unique_food_names_exactly_in_tbca_name_map": len(unique_foods & set(name_to_tbca)),
            "unique_food_names_requiring_explicit_name_mapping": len(unique_foods - set(name_to_tbca)),
            "used_mapping_targets_with_multiple_source_names": sum(
                len(sources) > 1 for sources in target_to_used_sources.values()
            ),
            "invalid_items": sum(int(row["invalid_items"]) for row in plan_rows),
            "invalid_quantities": sum(int(row["invalid_quantities"]) for row in plan_rows),
            "quantities_above_1000g_screening_threshold": sum(
                int(row["quantities_above_1000g_screening_threshold"]) for row in plan_rows
            ),
            "duplicate_items_within_meal": sum(
                int(row["duplicate_items_within_meal"]) for row in plan_rows
            ),
            "unmapped_tbca_occurrences": sum(int(row["unmapped_tbca_items"]) for row in plan_rows),
            "unmapped_environmental_occurrences": sum(
                int(row["unmapped_environmental_items"]) for row in plan_rows
            ),
            "plans_with_nutritional_target_violations": sum(
                int(row["nutritional_target_violations"]) > 0 for row in plan_rows
            ),
            "nutritional_target_violations": sum(
                int(row["nutritional_target_violations"]) for row in plan_rows
            ),
        },
        "by_profile": by_profile,
        "nutritional_violation_counts_by_nutrient": dict(
            sorted(violations_by_nutrient.items())
        ),
        "interpretation_limits": [
            "JSON validity before aggregation and counts of failed/regenerated API calls cannot be reconstructed.",
            "A mapped food is not proof that the LLM originally copied it from the attached list.",
            "The 1000 g threshold is a screening flag, not a clinically validated portion limit.",
            "Nutritional violations use the thresholds implemented by the submitted optimizer and do not establish clinical safety.",
        ],
    }
    (output_dir / "diet_audit_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    totals = summary["totals"]
    markdown = f"""# Base-diet audit summary

- Scope: {summary['scope']}.
- Plans: {totals['plans']} ({totals['plans_with_valid_schema']} with the expected 5-day/6-meal schema).
- Food occurrences: {totals['food_occurrences']} across {totals['unique_food_names']} unique names.
- Exact TBCA names: {totals['unique_food_names_exactly_in_tbca_name_map']}; names requiring the explicit preserved mapping: {totals['unique_food_names_requiring_explicit_name_mapping']}.
- Used TBCA targets reached by multiple generated names: {totals['used_mapping_targets_with_multiple_source_names']}.
- Invalid quantities: {totals['invalid_quantities']}.
- Quantities above the 1000 g screening threshold: {totals['quantities_above_1000g_screening_threshold']}.
- Duplicate foods within the same meal: {totals['duplicate_items_within_meal']}.
- TBCA-unmapped occurrences: {totals['unmapped_tbca_occurrences']}.
- Environmental-unmapped occurrences: {totals['unmapped_environmental_occurrences']}.
- Plans with at least one implemented nutritional-target violation: {totals['plans_with_nutritional_target_violations']}.
- Total implemented nutritional-target violations: {totals['nutritional_target_violations']}.

The machine-readable item, plan, nutrient, and summary files in this directory are the authoritative audit output. Raw API failure and regeneration counts cannot be inferred from these normalized JSON files.
"""
    (output_dir / "diet_audit_summary.md").write_text(markdown, encoding="utf-8")
    return summary


def main() -> None:
    output_dir = parse_args().output_dir.resolve()
    summary = audit(output_dir)
    print(json.dumps(summary["totals"], ensure_ascii=False, indent=2))
    print(f"Audit artifacts: {output_dir}")


if __name__ == "__main__":
    main()
