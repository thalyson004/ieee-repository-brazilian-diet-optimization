"""Fast deterministic checks; no full GA execution is performed here."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from diet_optimization.analysis.diet_audit import audit
from diet_optimization.optimization.pipeline import derive_execution_seed
from tests.run_experiments import EXPERIMENTS, commands_for


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

    def test_published_prompt_hashes_match_manifest(self) -> None:
        manifest = json.loads(
            (PROJECT_ROOT / "prompts" / "manifest.json").read_text(encoding="utf-8")
        )
        for entry in manifest["files"]:
            content = (PROJECT_ROOT / entry["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), entry["sha256"])

    def test_unverified_generation_settings_remain_explicitly_unknown(self) -> None:
        metadata = json.loads(
            (PROJECT_ROOT / "generation" / "original-generation-metadata.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(metadata["raw_api_responses_preserved"])
        self.assertFalse(metadata["request_logs_preserved"])
        self.assertEqual(metadata["fields"]["model_identifier"]["status"], "conflicting_not_recovered")
        for field in ("temperature", "top_p", "top_k", "max_output_tokens", "seed"):
            self.assertIsNone(metadata["fields"][field]["value"])


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


class BaseDietAuditTests(unittest.TestCase):
    def test_all_150_base_diets_are_auditable_and_mapped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "audit"
            totals = audit(output)["totals"]
            mapping_lines = (output / "food_mapping_audit.csv").read_text(
                encoding="utf-8"
            ).splitlines()

        self.assertEqual(totals["plans"], 150)
        self.assertEqual(totals["plans_with_valid_schema"], 150)
        self.assertEqual(totals["unmapped_tbca_occurrences"], 0)
        self.assertEqual(totals["unmapped_environmental_occurrences"], 0)
        self.assertEqual(
            totals["identity_food_mappings"]
            + totals["non_identity_mappings_without_preserved_classification"],
            totals["unique_food_names"],
        )
        self.assertEqual(len(mapping_lines), totals["unique_food_names"] + 1)


class RevisedNutritionProtocolTests(unittest.TestCase):
    def test_revised_protocol_has_16_complete_core_targets(self) -> None:
        protocol = json.loads(
            (PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json").read_text(
                encoding="utf-8"
            )
        )
        targets = protocol["core_targets"]
        self.assertEqual(len(targets), 16)
        self.assertEqual(len({target["nutrient"] for target in targets}), 16)
        for target in targets:
            self.assertTrue(target["unit"])
            self.assertTrue(target["source"])
            self.assertTrue(target["model_rule"])
            self.assertTrue(
                target["lower"] is not None or target["upper"] is not None,
                target["nutrient"],
            )

    def test_revised_protocol_does_not_silently_reuse_historical_sex_mismatch(self) -> None:
        protocol = json.loads(
            (PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json").read_text(
                encoding="utf-8"
            )
        )
        targets = {target["nutrient"]: target for target in protocol["core_targets"]}
        self.assertEqual(targets["Vitamina A"]["tbca_field"], "Vitamina A (RAE)")
        self.assertEqual(targets["Vitamina A"]["lower"], 700.0)
        self.assertEqual(targets["Magnésio"]["lower"], 310.0)
        self.assertEqual(targets["Vitamina C"]["lower"], 75.0)


if __name__ == "__main__":
    unittest.main()
