#!/usr/bin/env python3
"""Run archived reconstruction or new optimization experiments.

The optimization package originated from parent-repository commit ``e5f760c``.
Archived mode reconstructs the submitted artifacts; rerun mode executes a new
seeded replication. The original March 2026 GA seeds were not recorded.
"""

from __future__ import annotations

import argparse
import json
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
    workspace: Path, diet_files: dict[str, Path], runs: int, seed: int
) -> None:
    previous_cwd = Path.cwd()
    try:
        os.chdir(workspace)
        process_optimization_pipeline(
            diet_files=[str(diet_files[p]) for p in PROFILES],
            context_files=context_files(workspace),
            number_of_runs=runs,
            hyperparameters=GeneticAlgorithmHyperparameters(),
            base_seed=seed,
        )

        context = build_context(context_files(workspace))
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
            )
            food_duration = time.perf_counter() - started
            save_json_file(
                workspace / "data" / "outputs" / "optimization_runs" / "pl-alimentos"
                / f"execution-{profile}.json",
                {"schema_version": "1.0", "profile": profile, "resolution": "pl-alimentos",
                 "solver": food_diagnostics, "duration_seconds": food_duration,
                 "final_solution": food_result,
                 "metrics_and_violations": evaluate_plan(food_result[0], context) if food_result else None},
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
                diagnostics=meal_diagnostics,
            )
            meal_duration = time.perf_counter() - started
            save_json_file(
                workspace / "data" / "outputs" / "optimization_runs" / "pl-refeicoes"
                / f"execution-{profile}.json",
                {"schema_version": "1.0", "profile": profile, "resolution": "pl-refeicoes",
                 "solver": meal_diagnostics, "duration_seconds": meal_duration,
                 "final_solution": meal_result,
                 "metrics_and_violations": evaluate_plan(meal_result[0], context) if meal_result else None},
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


def write_manifest(
    workspace: Path, mode: str, runs: int, seed: int, command: list[str]
) -> None:
    manifest = {
        "schema_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "archive_source_commit": ARCHIVE_COMMIT,
        "original_random_seeds_recorded": False,
        "replication_base_seed": seed if mode == "rerun" else None,
        "ga_runs_per_profile_and_granularity": runs if mode == "rerun" else 10,
        "python": sys.version,
        "platform": platform.platform(),
        "execution_environment": environment_metadata(),
        "input_preparation_report": "input-preparation.json" if mode == "rerun" else None,
        "command": command,
        "notes": [
            "Archived mode rebuilds main tables from the fb34919 selected-solution snapshot and diversity from the e5f760c ten-run solution files, matching the published artifact history.",
            "Rerun mode is deterministic from the supplied base seed but cannot recreate the unrecorded random streams of March 2026.",
            "The 150 LLM-generated base diets are inputs; original API-call logs and inference settings were not preserved in this repository.",
        ],
    }
    (workspace / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    args = parse_args()
    workspace = args.output_dir.resolve()
    diet_files = stage_inputs(workspace, args.mode)
    write_manifest(workspace, args.mode, args.runs, args.seed, sys.argv)
    if args.mode == "archived":
        stage_archived_results(workspace)
    else:
        run_optimizers(workspace, diet_files, args.runs, args.seed)

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

