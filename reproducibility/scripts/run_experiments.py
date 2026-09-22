#!/usr/bin/env python3
"""Reproduce or audit the optimization experiments from the article.

The optimization implementation under ``reproducibility/code`` is an exact
source snapshot from the parent repository at commit e5f760c. This runner adds
only path staging, an explicit seed for new runs, and a machine-readable run
manifest. The original March 2026 GA seeds were not recorded; consequently,
``--mode archived`` reproduces the published aggregates from archived outputs,
whereas ``--mode rerun`` performs a new deterministic replication.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
REPRO_DIR = SCRIPT_PATH.parents[1]
REPOSITORY_ROOT = SCRIPT_PATH.parents[2]
CODE_DIR = REPRO_DIR / "code"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from otimizar.hyperparameters import GeneticAlgorithmHyperparameters  # noqa: E402
from otimizar.linear_optimizer import optimize_food_level, optimize_meal_level  # noqa: E402
from otimizar.pipeline import build_context, process_optimization_pipeline  # noqa: E402
from otimizar.utils import load_json_file, save_json_file  # noqa: E402


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
        default=REPRO_DIR / "generated",
        help="New output workspace. It must not already contain a run.",
    )
    return parser.parse_args()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def stage_inputs(workspace: Path) -> dict[str, Path]:
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(
            f"Output directory is not empty: {workspace}. Choose a fresh path."
        )
    workspace.mkdir(parents=True, exist_ok=True)

    diet_files: dict[str, Path] = {}
    for profile in PROFILES:
        source = REPOSITORY_ROOT / "diets-base" / f"dietas-{profile}.json"
        destination = workspace / "data" / "diets" / "base" / source.name
        copy_file(source, destination)
        diet_files[profile] = destination

    input_map = {
        REPOSITORY_ROOT / "maps" / "base" / "mapa-nome-tbca.json": (
            workspace / "data" / "maps" / "base" / "mapa-nome-tbca.json"
        ),
        REPOSITORY_ROOT / "maps" / "base" / "mapa-sustentavel-nome.json": (
            workspace / "data" / "maps" / "base" / "mapa-sustentavel-nome.json"
        ),
        REPOSITORY_ROOT / "maps" / "derived" / "mapa-sustentavel-tbca.json": (
            workspace / "data" / "maps" / "derived" / "mapa-sustentavel-tbca.json"
        ),
        REPRO_DIR / "inputs" / "mapa-tbca-completo.json": (
            workspace / "data" / "maps" / "base" / "mapa-tbca-completo.json"
        ),
        REPRO_DIR / "inputs" / "mapa-sustentavel-pegadas.json": (
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
    table_source_root = REPRO_DIR / "published-table-solutions"
    for source in sorted(table_source_root.rglob("*.json")):
        relative = source.relative_to(table_source_root)
        copy_file(source, optimized_root / relative)

    all_runs_root = workspace / "data" / "outputs" / "all_run_solutions"
    for source in sorted((REPOSITORY_ROOT / "optimized-diets").rglob("*.json")):
        relative = source.relative_to(REPOSITORY_ROOT / "optimized-diets")
        copy_file(source, all_runs_root / relative)

    run_root = workspace / "data" / "outputs" / "optimization_runs"
    for source in sorted((REPRO_DIR / "archived-runs").rglob("*.json")):
        relative = source.relative_to(REPRO_DIR / "archived-runs")
        copy_file(source, run_root / relative)


def run_optimizers(
    workspace: Path, diet_files: dict[str, Path], runs: int, seed: int
) -> None:
    previous_cwd = Path.cwd()
    try:
        os.chdir(workspace)
        random.seed(seed)
        process_optimization_pipeline(
            diet_files=[str(diet_files[p]) for p in PROFILES],
            context_files=context_files(workspace),
            number_of_runs=runs,
            hyperparameters=GeneticAlgorithmHyperparameters(),
        )

        context = build_context(context_files(workspace))
        footprint_key = "carbon_footprint"
        for profile in PROFILES:
            food_result = optimize_food_level(context, footprint_key=footprint_key)
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

            meal_result = optimize_meal_level(
                load_json_file(diet_files[profile]),
                context,
                footprint_key=footprint_key,
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
    diet_files = stage_inputs(workspace)
    if args.mode == "archived":
        stage_archived_results(workspace)
    else:
        run_optimizers(workspace, diet_files, args.runs, args.seed)

    write_manifest(workspace, args.mode, args.runs, args.seed, sys.argv)
    analysis_script = SCRIPT_PATH.with_name("generate_article_outputs.py")
    subprocess.run(
        [sys.executable, str(analysis_script), "--workspace", str(workspace)],
        check=True,
    )
    print(f"Reproduction workspace: {workspace}")


if __name__ == "__main__":
    main()

