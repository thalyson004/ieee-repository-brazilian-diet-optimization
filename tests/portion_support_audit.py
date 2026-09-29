"""Derive empirical positive food-by-meal quantity support from the 150 inputs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from diet_optimization.optimization.utils import parse_quantity_in_grams

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")


def collect_support(profile: str, diet_plans: list[dict]) -> list[dict]:
    observed: dict[tuple[str, str], list[tuple[float, int]]] = defaultdict(list)
    for plan_index, plan in enumerate(diet_plans, start=1):
        for meals in plan.values():
            if not isinstance(meals, dict):
                continue
            for meal_name, items in meals.items():
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    food_name = str(item.get("alimento", ""))
                    try:
                        quantity = float(parse_quantity_in_grams(item.get("quantidade", 0)))
                    except (TypeError, ValueError):
                        continue
                    if food_name and quantity > 0:
                        observed[(food_name, meal_name)].append((quantity, plan_index))

    rows = []
    for (food_name, meal_name), values in sorted(observed.items()):
        quantities = np.asarray([value for value, _ in values], dtype=float)
        n_diets = len({diet_index for _, diet_index in values})
        rows.append({
            "profile": profile,
            "food_name": food_name,
            "meal_name": meal_name,
            "positive_occurrences": int(len(quantities)),
            "distinct_source_diets": int(n_diets),
            "minimum_positive_g": round(float(np.min(quantities)), 6),
            "maximum_positive_g": round(float(np.max(quantities)), 6),
            "p05_positive_g": round(float(np.percentile(quantities, 5)), 6) if len(quantities) >= 20 else None,
            "p95_positive_g": round(float(np.percentile(quantities, 95)), 6) if len(quantities) >= 20 else None,
            "robust_percentile_sensitivity_available": len(quantities) >= 20,
            "support_strength": "weak_lt_5_occurrences" if len(quantities) < 5 else "observed_support",
            "is_serving_recommendation": False,
        })
    return rows


def build_report() -> list[dict]:
    result = []
    for profile in PROFILES:
        path = PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json"
        plans = json.loads(path.read_text(encoding="utf-8"))
        result.extend(collect_support(profile, plans))
    return result


def write_report(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_report()
    json_path = output_dir / "food-meal-quantity-support.json"
    csv_path = output_dir / "food-meal-quantity-support.csv"
    payload = {
        "schema_version": "1.0",
        "status": "descriptive_empirical_support_not_clinical_portion_guidance",
        "source": "150 preserved base plans, analyzed separately within each profile",
        "percentile_rule": "5th and 95th percentiles reported only at 20 or more positive occurrences",
        "rows": rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    columns = list(rows[0]) if rows else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    json_path, csv_path = write_report(args.output_dir.resolve())
    print(f"Support rows: {len(build_report())}")
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")


if __name__ == "__main__":
    main()
