"""Compare explicit LP fallback-penalty settings with logs/results per run."""

from __future__ import annotations

import argparse
from pathlib import Path

from diet_optimization.experiments.runner import (
    PROJECT_ROOT,
    PROFILES,
    context_files,
    stage_inputs,
)
from diet_optimization.experiments.diagnostics import evaluate_plan
from diet_optimization.optimization.hyperparameters import GeneticAlgorithmHyperparameters
from diet_optimization.optimization.linear_optimizer import (
    food_names_in_diets,
    optimize_food_level,
    optimize_meal_level,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.pipeline import build_context
from diet_optimization.optimization.utils import load_json_file, save_json_file


PENALTIES = (1e2, 1e3, 1e4, 1e5)


def _apply_revised_protocol(parameters: GeneticAlgorithmHyperparameters) -> None:
    protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
    parameters.nutritional_minimum_goals = protocol["minimum_goals"]
    parameters.nutritional_maximum_goals = protocol["maximum_goals"]
    parameters.nutrition_protocol_id = protocol["protocol_id"]
    parameters.secondary_nutrition_targets = protocol["secondary_targets"]
    parameters.descriptive_nutrition_targets = protocol["descriptive_targets"]
    parameters.meal_energy_share_limits = protocol["meal_energy_share_limits"]


def _data_quality_fields(parameters: GeneticAlgorithmHyperparameters) -> set[str]:
    return (
        set(parameters.nutritional_minimum_goals)
        | set(parameters.nutritional_maximum_goals)
        | {str(target["tbca_field"]) for target in parameters.secondary_nutrition_targets}
        | {str(target["tbca_field"]) for target in parameters.descriptive_nutrition_targets}
    )


def run(output_dir: Path) -> Path:
    output_dir = output_dir.resolve()
    diet_files = stage_inputs(output_dir, "rerun")
    context = build_context(context_files(output_dir))
    parameters = GeneticAlgorithmHyperparameters()
    _apply_revised_protocol(parameters)
    rows = []

    for profile in PROFILES:
        base_diets = load_json_file(diet_files[profile])
        allowed_foods = food_names_in_diets(base_diets)
        for method in ("LP-Food", "LP-Meal"):
            for penalty in PENALTIES:
                diagnostics: dict = {}
                kwargs = {
                    "diagnostics": diagnostics,
                    "minimum_goals": parameters.nutritional_minimum_goals,
                    "maximum_goals": parameters.nutritional_maximum_goals,
                    "slack_penalty": penalty,
                }
                if method == "LP-Food":
                    solution = optimize_food_level(
                        context, allowed_foods, **kwargs
                    )
                else:
                    solution = optimize_meal_level(
                        base_diets,
                        context,
                        meal_energy_share_limits=parameters.meal_energy_share_limits,
                        **kwargs,
                    )
                metrics = evaluate_plan(
                    solution[0], context,
                    minimum_goals=parameters.nutritional_minimum_goals,
                    maximum_goals=parameters.nutritional_maximum_goals,
                    meal_energy_share_limits=parameters.meal_energy_share_limits,
                    protocol_id=parameters.nutrition_protocol_id,
                    data_quality_fields=_data_quality_fields(parameters),
                ) if solution else None
                rows.append({
                    "profile": profile,
                    "method": method,
                    "slack_penalty": penalty,
                    "status": "relaxed" if diagnostics.get("fallback_used") else (
                        "strict_optimum" if solution else "no_solution"
                    ),
                    "solver": diagnostics,
                    "metrics_and_violations_after_plan_construction": metrics,
                    "final_solution": solution,
                })

    result = {
        "schema_version": "1.0",
        "experiment": "lp-slack-sensitivity",
        "scientific_readiness": "diagnostic_until_data_and_model_review_complete",
        "nutrition_protocol_id": parameters.nutrition_protocol_id,
        "penalty_grid": list(PENALTIES),
        "outputs": rows,
    }
    result_path = output_dir / "lp-slack-sensitivity.json"
    save_json_file(result_path, result)
    summary_path = output_dir / "lp-slack-sensitivity-summary.csv"
    lines = ["profile,method,slack_penalty,status,nonzero_slack_count,slack_constraints,violation_count"]
    for row in rows:
        slack = row["solver"].get("slack_analysis", {})
        nonzero = [item for item in slack.get("constraints", []) if item.get("slack_absolute", 0) > 1e-7]
        violations = row["metrics_and_violations_after_plan_construction"]
        violation_count = len(violations.get("mean_daily_violations", [])) if violations else ""
        names = ";".join(item["constraint"] for item in nonzero)
        lines.append(
            f"{row['profile']},{row['method']},{row['slack_penalty']},{row['status']},"
            f"{len(nonzero)},\"{names}\",{violation_count}"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} LP penalty scenarios: {result_path}")
    print(f"Summary: {summary_path}")
    return result_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
