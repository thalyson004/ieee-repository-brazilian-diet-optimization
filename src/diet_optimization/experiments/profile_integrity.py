"""Explicit, auditable exclusions from *derived* profile input copies.

The original LLM diets are never edited. This list covers only two known,
unambiguous vegan contradictions; it does not certify all remaining foods.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path


def load_exclusions(config_path: Path) -> dict[str, set[str]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return {
        profile: {entry["food_name"] for entry in entries}
        for profile, entries in config["profiles"].items()
    }


def prepare_profile_diets(diets: list[dict], profile: str, excluded: set[str]) -> tuple[list[dict], list[dict]]:
    """Remove only exact configured names, returning a row-level audit trail."""
    prepared = copy.deepcopy(diets)
    removals: list[dict] = []
    for plan_index, plan in enumerate(prepared, start=1):
        for day, meals in plan.items():
            if not isinstance(meals, dict):
                continue
            for meal_name, items in meals.items():
                if not isinstance(items, list):
                    continue
                retained = []
                for item in items:
                    if item.get("alimento") in excluded:
                        removals.append({
                            "profile": profile, "plan_index": plan_index,
                            "day": day, "meal": meal_name,
                            "food_name": item["alimento"],
                            "quantity": item.get("quantidade"),
                        })
                    else:
                        retained.append(item)
                meals[meal_name] = retained
    return prepared, removals
