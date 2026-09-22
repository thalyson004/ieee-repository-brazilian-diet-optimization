"""Fast deterministic checks; no full GA execution is performed here."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests.run_experiments import EXPERIMENTS, commands_for
from diet_optimization.optimization.pipeline import derive_execution_seed


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ArtifactPopulationTests(unittest.TestCase):
    def test_base_diet_population(self) -> None:
        for path in (PROJECT_ROOT / "diets-base").glob("dietas-*.json"):
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 50, path)

    def test_archived_ga_population(self) -> None:
        for path in (PROJECT_ROOT / "optimized-diets").glob("ag-*/*.json"):
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 10, path)

    def test_submitted_solution_population(self) -> None:
        paths = list((PROJECT_ROOT / "archive" / "published-table-solutions").rglob("*.json"))
        self.assertEqual(len(paths), 12)
        for path in paths:
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 1, path)


class CommandCatalogTests(unittest.TestCase):
    def test_every_registered_experiment_has_a_command(self) -> None:
        workspace = PROJECT_ROOT / "tests" / "results" / "artifacts" / "test"
        for experiment in EXPERIMENTS:
            self.assertTrue(commands_for(experiment, workspace, 10, 20260323))

    def test_ga_execution_seeds_are_stable_and_independent(self) -> None:
        seeds = {
            derive_execution_seed(20260323, resolution, profile, run)
            for resolution in ("ag-alimentos", "ag-refeicoes")
            for profile in ("regular", "vegetariana", "vegana")
            for run in range(1, 11)
        }
        self.assertEqual(len(seeds), 60)
        self.assertEqual(
            derive_execution_seed(20260323, "ag-alimentos", "regular", 1),
            derive_execution_seed(20260323, "ag-alimentos", "regular", 1),
        )


if __name__ == "__main__":
    unittest.main()
