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


def load_pending_mapping_exclusions(config_path: Path) -> dict[str, set[str]]:
    """Load exact-name exclusions for a diagnostic mapping-uncertainty scenario."""
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("status") != "diagnostic_exclusion_sensitivity_only_not_an_adjudication":
        raise ValueError("Pending mapping exclusions must remain explicitly diagnostic")
    profiles = config.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != {"regular", "vegetariana", "vegana"}:
        raise ValueError("Pending mapping exclusions must define all three diet profiles")
    loaded: dict[str, set[str]] = {}
    for profile, names in profiles.items():
        if not isinstance(names, list) or any(not isinstance(name, str) or not name for name in names):
            raise ValueError(f"Invalid pending mapping exclusion names for {profile}")
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate pending mapping exclusion name for {profile}")
        loaded[profile] = set(names)
    declared = config.get("unresolved_source_foods")
    if declared != len(set.union(*loaded.values())):
        raise ValueError("Declared unresolved food count does not match exact profile lists")
    return loaded


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
