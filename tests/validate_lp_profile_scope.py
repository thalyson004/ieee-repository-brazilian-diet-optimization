"""Run each LP-Food profile with only food names from its 50 base diets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from diet_optimization.optimization.linear_optimizer import food_names_in_diets, optimize_food_level
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets


ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("regular", "vegetariana", "vegana")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(output)
    output.mkdir(parents=True, exist_ok=True)

    context = build_context({
        "tbca_map": str(ROOT / "maps/derived/mapa-sustentavel-tbca.json"),
        "tbca_db": str(ROOT / "maps/base/mapa-tbca-completo.json"),
        "footprint_map": str(ROOT / "maps/base/mapa-sustentavel-pegadas.json"),
    })
    report = {"schema_version": "1.0", "protocol": "historical_numeric_targets_profile_scoped_food_pool",
              "profiles": {}}
    exclusions = load_exclusions(ROOT / "configs" / "profile-exclusions.json")
    for profile in PROFILES:
        source_diets = json.loads((ROOT / "diets-base" / f"dietas-{profile}.json").read_text(encoding="utf-8"))
        if len(source_diets) != 50:
            raise AssertionError(f"Expected 50 base diets for {profile}")
        diets, removals = prepare_profile_diets(source_diets, profile, exclusions[profile])
        allowed = food_names_in_diets(diets)
        diagnostics: dict = {}
        solution = optimize_food_level(context, allowed_food_names=allowed, diagnostics=diagnostics)
        selected = {item["alimento"] for item in solution[0]["1"]["Refeição LP"]} if solution else set()
        outside = sorted(selected - allowed)
        report["profiles"][profile] = {
            "base_diets": len(diets), "allowed_food_names": len(allowed),
            "selected_food_names": sorted(selected), "outside_profile_pool": outside,
            "explicit_source_exclusions": removals,
            "excluded_foods_selected": sorted(selected & exclusions[profile]),
            "solver": diagnostics, "solution": solution,
        }
        if outside or (selected & exclusions[profile]) or not solution:
            raise AssertionError(f"LP-Food scope or feasibility failed for {profile}: {outside}")
    (output / "lp-profile-scope.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Verified LP-Food profile scope: {output / 'lp-profile-scope.json'}")


if __name__ == "__main__":
    main()
