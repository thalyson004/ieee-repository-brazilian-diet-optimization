"""Quantify nutrient-field missingness and strict complete-case pool attrition."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILE_FILES = {
    "regular": "dietas-regular.json",
    "vegetarian": "dietas-vegetariana.json",
    "vegan": "dietas-vegana.json",
}


def _numeric_value(value: Any) -> bool:
    if isinstance(value, bool) or value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def required_nutrients(protocol: dict[str, Any]) -> list[dict[str, str]]:
    """Return core and additional nutrients with an enforced bound."""
    rules: list[dict[str, Any]] = list(protocol.get("core_targets", []))
    rules.extend(
        rule
        for rule in protocol.get("additional_rules", [])
        if (rule.get("lower") is not None or rule.get("upper") is not None)
        and str(rule.get("model_rule", "")).lower().startswith("hard")
    )
    unique: dict[str, dict[str, str]] = {}
    for rule in rules:
        field = str(rule.get("tbca_field", ""))
        nutrient = str(rule.get("nutrient", field))
        if field:
            unique[field] = {"nutrient": nutrient, "tbca_field": field}
    return list(unique.values())


def summarize_profile(
    profile: str,
    plans: list[dict[str, Any]],
    tbca_map: dict[str, str],
    tbca_database: dict[str, Any],
    nutrients: list[dict[str, str]],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    """Summarize field coverage and strict complete-case attrition for one profile."""
    food_counts: Counter[str] = Counter()
    food_grams: defaultdict[str, float] = defaultdict(float)
    food_plan_counts: defaultdict[str, set[int]] = defaultdict(set)
    for plan_index, plan in enumerate(plans, start=1):
        for meals in plan.values():
            if not isinstance(meals, dict):
                continue
            for items in meals.values():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict) or not isinstance(item.get("alimento"), str):
                        continue
                    name = item["alimento"]
                    try:
                        grams = float(str(item.get("quantidade", "0")).replace(",", "."))
                    except (TypeError, ValueError):
                        grams = 0.0
                    if grams <= 0 or not math.isfinite(grams):
                        continue
                    food_counts[name] += 1
                    food_grams[name] += grams
                    food_plan_counts[name].add(plan_index)

    missing_by_food: dict[str, list[str]] = {}
    field_rows: list[dict[str, Any]] = []
    for name in sorted(food_counts):
        code = tbca_map.get(name)
        entry = tbca_database.get(code, {}) if code else {}
        composition = entry.get("nutrientes", {}) if isinstance(entry, dict) else {}
        missing_by_food[name] = [
            nutrient["tbca_field"]
            for nutrient in nutrients
            if not _numeric_value(composition.get(nutrient["tbca_field"]))
        ]

    for nutrient in nutrients:
        field = nutrient["tbca_field"]
        missing_foods = []
        for name in food_counts:
            code = tbca_map.get(name)
            entry = tbca_database.get(code, {}) if code else {}
            composition = entry.get("nutrientes", {}) if isinstance(entry, dict) else {}
            if not _numeric_value(composition.get(field)):
                missing_foods.append(name)
        field_rows.append(
            {
                "profile": profile,
                "nutrient": nutrient["nutrient"],
                "tbca_field": field,
                "candidate_foods": len(food_counts),
                "foods_with_numeric_value": len(food_counts) - len(missing_foods),
                "foods_missing_or_nonnumeric": len(missing_foods),
                "food_occurrences": sum(food_counts.values()),
                "occurrences_exposed_to_missing_value": sum(food_counts[name] for name in missing_foods),
                "grams_exposed_to_missing_value": round(sum(food_grams[name] for name in missing_foods), 6),
                "plans_exposed_to_missing_value": len(
                    set().union(*(food_plan_counts[name] for name in missing_foods))
                    if missing_foods else set()
                ),
            }
        )

    complete_case_foods = {name for name, missing in missing_by_food.items() if not missing}
    excluded_foods = set(food_counts) - complete_case_foods
    total_occurrences = sum(food_counts.values())
    excluded_occurrences = sum(food_counts[name] for name in excluded_foods)
    total_grams = sum(food_grams.values())
    excluded_grams = sum(food_grams[name] for name in excluded_foods)
    complete_case_plans = sum(
        1
        for plan_index in range(1, len(plans) + 1)
        if any(plan_index in food_plan_counts[name] for name in complete_case_foods)
    )
    summary = {
        "profile": profile,
        "base_plans": len(plans),
        "candidate_foods": len(food_counts),
        "food_occurrences": total_occurrences,
        "food_grams": round(total_grams, 6),
        "primary_nutrients_required": len(nutrients),
        "strict_complete_case_foods_retained": len(complete_case_foods),
        "strict_complete_case_foods_excluded": len(excluded_foods),
        "strict_complete_case_occurrences_retained": total_occurrences - excluded_occurrences,
        "strict_complete_case_occurrences_excluded": excluded_occurrences,
        "strict_complete_case_occurrences_retained_pct": round(
            100.0 * (total_occurrences - excluded_occurrences) / total_occurrences, 4
        ) if total_occurrences else None,
        "strict_complete_case_grams_retained": round(total_grams - excluded_grams, 6),
        "strict_complete_case_grams_excluded": round(excluded_grams, 6),
        "strict_complete_case_grams_retained_pct": round(
            100.0 * (total_grams - excluded_grams) / total_grams, 4
        ) if total_grams else None,
        "plans_with_at_least_one_complete_case_food": complete_case_plans,
        "strict_complete_case_is_primary_recommendation": False,
    }
    food_rows = [
        {
            "profile": profile,
            "food_original": name,
            "tbca_code": tbca_map.get(name),
            "occurrences": food_counts[name],
            "total_grams": round(food_grams[name], 6),
            "plans": len(food_plan_counts[name]),
            "missing_or_nonnumeric_primary_fields": "|".join(missing_by_food[name]),
            "strict_complete_case_retained": not missing_by_food[name],
        }
        for name in sorted(food_counts)
    ]
    return summary, field_rows, food_rows


def audit(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    protocol = load(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    tbca_map = load(PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json")
    tbca_database = load(PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json")
    nutrients = required_nutrients(protocol)
    summaries: list[dict[str, Any]] = []
    field_rows: list[dict[str, Any]] = []
    food_rows: list[dict[str, Any]] = []
    for profile, filename in PROFILE_FILES.items():
        plans = load(PROJECT_ROOT / "diets-base" / filename)
        summary, per_field, per_food = summarize_profile(
            profile, plans, tbca_map, tbca_database, nutrients
        )
        summaries.append(summary)
        field_rows.extend(per_field)
        food_rows.extend(per_food)

    report = {
        "schema_version": "1.0",
        "status": "diagnostic_only_missingness_policy_not_adjudicated",
        "current_calculator_behavior": "missing nutrient fields contribute zero in legacy nutrient totals and optimizer vectors",
        "strict_scenario": "retain a food only when every enforced core/additional nutrient field is numeric in the local TBCA snapshot",
        "strict_scenario_warning": "complete-case food filtering is an attrition sensitivity, not an endorsed primary policy or an imputation of true zero",
        "protocol_id": protocol.get("protocol_id"),
        "required_nutrients": nutrients,
        "profiles": summaries,
        "missingness_by_profile_and_nutrient": field_rows,
    }
    (output_dir / "nutrient-missingness-summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for filename, rows in (
        ("nutrient-missingness-by-field.csv", field_rows),
        ("nutrient-missingness-by-food.csv", food_rows),
    ):
        if rows:
            with (output_dir / filename).open("x", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Missingness audit artifacts: {output_dir}")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit(args.output_dir)


if __name__ == "__main__":
    main()
