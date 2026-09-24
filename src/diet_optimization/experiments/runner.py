#!/usr/bin/env python3
"""Run archived reconstruction or new optimization experiments.

The optimization package originated from parent-repository commit ``e5f760c``.
Archived mode reconstructs the submitted artifacts; rerun mode executes a new
seeded replication. The original March 2026 GA seeds were not recorded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ARCHIVE_ROOT = PROJECT_ROOT / "archive"

from diet_optimization.optimization.hyperparameters import GeneticAlgorithmHyperparameters
from diet_optimization.optimization.linear_optimizer import (
    food_names_in_diets,
    optimize_food_level,
    optimize_meal_level,
)
from diet_optimization.optimization.pipeline import build_context, process_optimization_pipeline
from diet_optimization.optimization.utils import load_json_file, save_json_file
from diet_optimization.experiments.diagnostics import environment_metadata, evaluate_plan
from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.optimization.nutritional_targets import load_protocol


PROFILES = ("regular", "vegetariana", "vegana")
ARCHIVE_COMMIT = "e5f760c"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("archived", "rerun"),
        default="archived",
        help="Use archived solutions or execute GA and LP again.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=10,
        help="Independent GA executions per profile and granularity for a rerun.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20260323,
        help="Base Python random seed for a new deterministic replication.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "tests" / "results" / "artifacts" / "manual-run",
        help="New output workspace. It must not already contain a run.",
    )
    parser.add_argument(
        "--nutrition-protocol",
        choices=("historical", "revised"),
        default="revised",
        help="Explicit constraint set for a new rerun; archived reconstruction ignores it.",
    )
    parser.add_argument(
        "--ga-overrides",
        type=Path,
        help="JSON object of approved GA hyperparameter overrides for sensitivity runs.",
    )
    return parser.parse_args()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def stage_inputs(workspace: Path, mode: str) -> dict[str, Path]:
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty: {workspace}. Choose a fresh path."
        )
    workspace.mkdir(parents=True, exist_ok=True)

    diet_files: dict[str, Path] = {}
    exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
    preparation_report = {"mode": mode, "status": "only_exact_known_contradictions_excluded; complete_review_pending",
                          "removed_items": []}
    for profile in PROFILES:
        source = PROJECT_ROOT / "diets-base" / f"dietas-{profile}.json"
        destination = workspace / "data" / "diets" / "base" / source.name
        copy_file(source, destination)
        if mode == "rerun":
            copy_file(source, workspace / "data" / "diets" / "source" / source.name)
            prepared, removals = prepare_profile_diets(load_json_file(destination), profile, exclusions[profile])
            save_json_file(destination, prepared)
            preparation_report["removed_items"].extend(removals)
        diet_files[profile] = destination
    if mode == "rerun":
        save_json_file(workspace / "input-preparation.json", preparation_report)

    input_map = {
        PROJECT_ROOT / "maps" / "base" / "mapa-nome-tbca.json": (
            workspace / "data" / "maps" / "base" / "mapa-nome-tbca.json"
        ),
        PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-nome.json": (
            workspace / "data" / "maps" / "base" / "mapa-sustentavel-nome.json"
        ),
        PROJECT_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json": (
            workspace / "data" / "maps" / "derived" / "mapa-sustentavel-tbca.json"
        ),
        PROJECT_ROOT / "maps" / "base" / "mapa-tbca-completo.json": (
            workspace / "data" / "maps" / "base" / "mapa-tbca-completo.json"
        ),
        PROJECT_ROOT / "maps" / "base" / "mapa-sustentavel-pegadas.json": (
            workspace / "data" / "maps" / "base" / "mapa-sustentavel-pegadas.json"
        ),
    }
    for source, destination in input_map.items():
        copy_file(source, destination)
    return diet_files


def context_files(workspace: Path) -> dict[str, str]:
    return {
        "tbca_map": str(
            workspace / "data" / "maps" / "derived" / "mapa-sustentavel-tbca.json"
        ),
        "tbca_db": str(
            workspace / "data" / "maps" / "base" / "mapa-tbca-completo.json"
        ),
        "footprint_map": str(
            workspace
            / "data"
            / "maps"
            / "base"
            / "mapa-sustentavel-pegadas.json"
        ),
    }


def stage_archived_results(workspace: Path) -> None:
    # The main numerical tables were generated from the single selected GA
    # solution snapshot at fb34919. The later e5f760c release replaced each GA
    # file with 10 runs and updated diversity, but did not regenerate the main
    # tables. Preserve both populations so the published artifacts are exactly
    # reconstructable and the inconsistency remains auditable.
    optimized_root = workspace / "data" / "outputs" / "optimized_diets"
    table_source_root = ARCHIVE_ROOT / "published-table-solutions"
    for source in sorted(table_source_root.rglob("*.json")):
        relative = source.relative_to(table_source_root)
        copy_file(source, optimized_root / relative)

    all_runs_root = workspace / "data" / "outputs" / "all_run_solutions"
    for source in sorted((PROJECT_ROOT / "optimized-diets").rglob("*.json")):
        relative = source.relative_to(PROJECT_ROOT / "optimized-diets")
        copy_file(source, all_runs_root / relative)

    run_root = workspace / "data" / "outputs" / "optimization_runs"
    for source in sorted((ARCHIVE_ROOT / "optimization-runs").rglob("*.json")):
        relative = source.relative_to(ARCHIVE_ROOT / "optimization-runs")
        copy_file(source, run_root / relative)


def run_optimizers(
    workspace: Path, diet_files: dict[str, Path], runs: int, seed: int,
    hyperparameters: GeneticAlgorithmHyperparameters,
) -> None:
    previous_cwd = Path.cwd()
    try:
        os.chdir(workspace)
        process_optimization_pipeline(
            diet_files=[str(diet_files[p]) for p in PROFILES],
            context_files=context_files(workspace),
            number_of_runs=runs,
            hyperparameters=hyperparameters,
            base_seed=seed,
        )

        context = build_context(context_files(workspace))
        _write_nutrient_coverage_audit(workspace, diet_files, context, hyperparameters)
        footprint_key = "carbon_footprint"
        for profile in PROFILES:
            profile_diets = load_json_file(diet_files[profile])
            allowed_food_names = food_names_in_diets(profile_diets)
            food_diagnostics: dict = {}
            started = time.perf_counter()
            food_result = optimize_food_level(
                context,
                allowed_food_names=allowed_food_names,
                footprint_key=footprint_key,
                diagnostics=food_diagnostics,
                minimum_goals=hyperparameters.nutritional_minimum_goals,
                maximum_goals=hyperparameters.nutritional_maximum_goals,
            )
            food_duration = time.perf_counter() - started
            save_json_file(
                workspace / "data" / "outputs" / "optimization_runs" / "pl-alimentos"
                / f"execution-{profile}.json",
                {"schema_version": "1.0", "profile": profile, "resolution": "pl-alimentos",
                 "solver": food_diagnostics, "duration_seconds": food_duration,
                 "final_solution": food_result,
                 "effective_nutritional_constraints": {
                     "protocol_id": hyperparameters.nutrition_protocol_id,
                     "minimum_goals": hyperparameters.nutritional_minimum_goals,
                     "maximum_goals": hyperparameters.nutritional_maximum_goals,
                 },
                 "metrics_and_violations": evaluate_plan(
                     food_result[0], context,
                     minimum_goals=hyperparameters.nutritional_minimum_goals,
                     maximum_goals=hyperparameters.nutritional_maximum_goals,
                     meal_energy_share_limits=hyperparameters.meal_energy_share_limits,
                     protocol_id=hyperparameters.nutrition_protocol_id,
                     data_quality_fields=(
                         set(hyperparameters.nutritional_minimum_goals)
                         | set(hyperparameters.nutritional_maximum_goals)
                         | {target["tbca_field"] for target in hyperparameters.secondary_nutrition_targets}
                         | {target["tbca_field"] for target in hyperparameters.descriptive_nutrition_targets}
                     ),
                 ) if food_result else None},
            )
            if food_result:
                save_json_file(
                    workspace
                    / "data"
                    / "outputs"
                    / "optimized_diets"
                    / "pl-alimentos"
                    / f"otimizada-dietas-{profile}.json",
                    food_result,
                )

            meal_diagnostics: dict = {}
            started = time.perf_counter()
            meal_result = optimize_meal_level(
                profile_diets,
                context,
                footprint_key=footprint_key,
                minimum_goals=hyperparameters.nutritional_minimum_goals,
                maximum_goals=hyperparameters.nutritional_maximum_goals,
                meal_energy_share_limits=hyperparameters.meal_energy_share_limits,
                diagnostics=meal_diagnostics,
            )
            meal_duration = time.perf_counter() - started
            save_json_file(
                workspace / "data" / "outputs" / "optimization_runs" / "pl-refeicoes"
                / f"execution-{profile}.json",
                {"schema_version": "1.0", "profile": profile, "resolution": "pl-refeicoes",
                 "solver": meal_diagnostics, "duration_seconds": meal_duration,
                 "final_solution": meal_result,
                 "effective_nutritional_constraints": {
                     "protocol_id": hyperparameters.nutrition_protocol_id,
                     "minimum_goals": hyperparameters.nutritional_minimum_goals,
                     "maximum_goals": hyperparameters.nutritional_maximum_goals,
                 },
                 "metrics_and_violations": evaluate_plan(
                     meal_result[0], context,
                     minimum_goals=hyperparameters.nutritional_minimum_goals,
                     maximum_goals=hyperparameters.nutritional_maximum_goals,
                     meal_energy_share_limits=hyperparameters.meal_energy_share_limits,
                     protocol_id=hyperparameters.nutrition_protocol_id,
                     data_quality_fields=(
                         set(hyperparameters.nutritional_minimum_goals)
                         | set(hyperparameters.nutritional_maximum_goals)
                         | {target["tbca_field"] for target in hyperparameters.secondary_nutrition_targets}
                         | {target["tbca_field"] for target in hyperparameters.descriptive_nutrition_targets}
                     ),
                 ) if meal_result else None},
            )
            if meal_result:
                save_json_file(
                    workspace
                    / "data"
                    / "outputs"
                    / "optimized_diets"
                    / "pl-refeicoes"
                    / f"otimizada-dietas-{profile}.json",
                    meal_result,
                )
    finally:
        os.chdir(previous_cwd)


def _write_nutrient_coverage_audit(
    workspace: Path,
    diet_files: dict[str, Path],
    context,
    hyperparameters: GeneticAlgorithmHyperparameters,
) -> None:
    target_fields = sorted(
        set(hyperparameters.nutritional_minimum_goals)
        | set(hyperparameters.nutritional_maximum_goals)
        | {target["tbca_field"] for target in hyperparameters.secondary_nutrition_targets}
        | {target["tbca_field"] for target in hyperparameters.descriptive_nutrition_targets}
    )
    by_profile = {}
    for profile, path in diet_files.items():
        diets = load_json_file(path)
        names = sorted(food_names_in_diets(diets))
        field_report = {}
        for field in target_fields:
            present, missing = [], []
            for name in names:
                code = context.tbca_map.get(name)
                nutrient_record = context.tbca_database.get(code, {}).get("nutrientes", {}) if code else {}
                value = nutrient_record.get(field)
                (present if value is not None else missing).append(name)
            field_report[field] = {
                "available_food_count": len(present),
                "missing_food_count": len(missing),
                "missing_food_names": missing,
            }
        by_profile[profile] = {
            "distinct_source_food_count": len(names),
            "fields": field_report,
        }
    report = {
        "protocol_id": hyperparameters.nutrition_protocol_id,
        "missing_value_policy": "zero_contribution_in_legacy_calculators; missingness is explicitly listed and requires sensitivity analysis",
        "profiles": by_profile,
    }
    save_json_file(workspace / "nutrition-field-coverage.json", report)


def source_provenance() -> dict:
    """Identify the exact repository revision and data files used by a run."""
    input_paths = [
        "configs/revised-nutrition-protocol.json",
        "configs/profile-exclusions.json",
        "configs/ga-sensitivity/reduced-population.json",
        "configs/ga-sensitivity/higher-mutation.json",
        "configs/ga-sensitivity/shorter-stagnation.json",
        "diets-base/dietas-regular.json",
        "diets-base/dietas-vegetariana.json",
        "diets-base/dietas-vegana.json",
        "maps/base/mapa-nome-tbca.json",
        "maps/base/mapa-tbca-completo.json",
        "maps/base/mapa-sustentavel-nome.json",
        "maps/base/mapa-sustentavel-pegadas.json",
        "maps/derived/mapa-sustentavel-tbca.json",
    ]
    input_sha256 = {}
    for relative_path in input_paths:
        path = PROJECT_ROOT / relative_path
        input_sha256[relative_path] = (
            hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        )

    commit = None
    worktree_dirty = None
    try:
        commit_result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        commit = commit_result.stdout.strip()
        status_result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
        worktree_dirty = bool(status_result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "git_commit": commit,
        "git_worktree_dirty": worktree_dirty,
        "input_sha256": input_sha256,
    }


GA_OVERRIDE_LIMITS = {
    "population_size": (int, 1, None),
    "max_stagnation_generations": (int, 1, None),
    "max_generations": (int, 1, None),
    "default_global_mutation_rate": (float, 0.0, 1.0),
    "default_local_mutation_rate": (float, 0.0, 1.0),
    "hyper_global_mutation_rate": (float, 0.0, 1.0),
    "hyper_local_mutation_rate": (float, 0.0, 1.0),
}


def apply_ga_overrides(
    hyperparameters: GeneticAlgorithmHyperparameters, overrides: dict
) -> dict:
    """Validate and apply the deliberately narrow GA sensitivity surface."""
    if not isinstance(overrides, dict):
        raise ValueError("GA overrides must be a JSON object")
    unknown = sorted(set(overrides) - set(GA_OVERRIDE_LIMITS))
    if unknown:
        raise ValueError(f"Unsupported GA override(s): {', '.join(unknown)}")
    applied = {}
    for name, value in overrides.items():
        expected_type, minimum, maximum = GA_OVERRIDE_LIMITS[name]
        if expected_type is int:
            valid_type = isinstance(value, int) and not isinstance(value, bool)
        else:
            valid_type = isinstance(value, (int, float)) and not isinstance(value, bool)
        if not valid_type or not math.isfinite(value) or value < minimum:
            raise ValueError(f"Invalid value for GA override {name}: {value!r}")
        if maximum is not None and value > maximum:
            raise ValueError(f"GA override {name} must be at most {maximum}")
        normalized = int(value) if expected_type is int else float(value)
        setattr(hyperparameters, name, normalized)
        applied[name] = normalized
    return applied


def write_manifest(
    workspace: Path, mode: str, runs: int, seed: int, command: list[str],
    nutrition_protocol_id: str, nutrition_constraints_sha256: str,
    ga_overrides: dict | None = None,
) -> None:
    normalized_overrides = ga_overrides or {}
    overrides_hash = hashlib.sha256(
        json.dumps(normalized_overrides, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "archive_source_commit": ARCHIVE_COMMIT,
        "source_provenance": source_provenance(),
        "ga_overrides": normalized_overrides,
        "ga_overrides_sha256": overrides_hash,
        "original_random_seeds_recorded": False,
        "replication_base_seed": seed if mode == "rerun" else None,
        "ga_runs_per_profile_and_granularity": runs if mode == "rerun" else 10,
        "python": sys.version,
        "platform": platform.platform(),
        "execution_environment": environment_metadata(),
        "input_preparation_report": "input-preparation.json" if mode == "rerun" else None,
        "nutrition_protocol_id": nutrition_protocol_id if mode == "rerun" else None,
        "effective_nutrition_constraints_sha256": nutrition_constraints_sha256 if mode == "rerun" else None,
        "scientific_readiness": (
            "diagnostic_pending_food_mapping_review_and_nutrient_missingness_sensitivity"
            if mode == "rerun" else "archived_reconstruction"
        ),
        "command": command,
        "notes": [
            "Archived mode rebuilds main tables from the fb34919 selected-solution snapshot and diversity from the e5f760c ten-run solution files, matching the published artifact history.",
            "Rerun mode is deterministic from the supplied base seed but cannot recreate the unrecorded random streams of March 2026.",
            "The 150 LLM-generated base diets are inputs; original API-call logs and inference settings were not preserved in this repository.",
            "Reruns are diagnostic until the non-identity food mappings and nutrient missingness policy are adjudicated; the field-coverage report enumerates absent composition values.",
        ],
    }
    (workspace / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    workspace = args.output_dir.resolve()
    diet_files = stage_inputs(workspace, args.mode)
    hyperparameters = GeneticAlgorithmHyperparameters()
    override_payload = {}
    if args.ga_overrides is not None:
        override_path = args.ga_overrides.resolve()
        override_payload = json.loads(override_path.read_text(encoding="utf-8"))
    applied_overrides = apply_ga_overrides(hyperparameters, override_payload)
    protocol_payload = {
        "protocol_id": hyperparameters.nutrition_protocol_id,
        "minimum_goals": hyperparameters.nutritional_minimum_goals,
        "maximum_goals": hyperparameters.nutritional_maximum_goals,
        "meal_energy_share_limits": hyperparameters.meal_energy_share_limits,
        "meal_energy_share_penalty_weight": hyperparameters.meal_energy_share_penalty_weight,
    }
    if args.mode == "rerun" and args.nutrition_protocol == "revised":
        source_path = PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json"
        protocol_payload = load_protocol(source_path)
        hyperparameters.nutritional_minimum_goals = protocol_payload["minimum_goals"]
        hyperparameters.nutritional_maximum_goals = protocol_payload["maximum_goals"]
        hyperparameters.nutrition_protocol_id = protocol_payload["protocol_id"]
        hyperparameters.secondary_nutrition_targets = protocol_payload["secondary_targets"]
        hyperparameters.descriptive_nutrition_targets = protocol_payload["descriptive_targets"]
        hyperparameters.meal_energy_share_limits = protocol_payload["meal_energy_share_limits"]
        hyperparameters.meal_energy_share_penalty_weight = protocol_payload["meal_energy_share_penalty_weight"]
    effective_constraints = {
        "protocol_id": hyperparameters.nutrition_protocol_id,
        "minimum_goals": hyperparameters.nutritional_minimum_goals,
        "maximum_goals": hyperparameters.nutritional_maximum_goals,
        "secondary_targets": hyperparameters.secondary_nutrition_targets,
        "descriptive_targets": hyperparameters.descriptive_nutrition_targets,
        "meal_energy_share_limits": hyperparameters.meal_energy_share_limits,
        "meal_energy_share_penalty_weight": hyperparameters.meal_energy_share_penalty_weight,
    }
    effective_constraints_json = json.dumps(effective_constraints, ensure_ascii=False, sort_keys=True)
    constraints_hash = hashlib.sha256(effective_constraints_json.encode("utf-8")).hexdigest()
    write_manifest(
        workspace, args.mode, args.runs, args.seed, sys.argv,
        hyperparameters.nutrition_protocol_id, constraints_hash,
        ga_overrides=applied_overrides,
    )
    if args.mode == "rerun":
        (workspace / "effective-nutrition-constraints.json").write_text(
            json.dumps({**effective_constraints, "sha256": constraints_hash}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    if args.mode == "archived":
        stage_archived_results(workspace)
    else:
        run_optimizers(workspace, diet_files, args.runs, args.seed, hyperparameters)

    subprocess.run(
        [sys.executable, "-m", "diet_optimization.analysis.article_outputs", "--workspace", str(workspace)],
        check=True,
    )
    if args.mode == "rerun":
        subprocess.run(
            [sys.executable, "-m", "diet_optimization.analysis.run_statistics", "--workspace", str(workspace)],
            check=True,
        )
    print(f"Reproduction workspace: {workspace}")


if __name__ == "__main__":
    main()

