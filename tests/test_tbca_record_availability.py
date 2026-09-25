from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from diet_optimization.experiments.profile_integrity import (
    load_tbca_unavailable_record_exclusions,
    prepare_profile_diets,
)
from tests.run_experiments import commands_for


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TbcaRecordAvailabilityTests(unittest.TestCase):
    def test_config_is_explicit_and_limited_to_the_vegan_pool(self) -> None:
        config_path = PROJECT_ROOT / "configs" / "tbca-unavailable-record-exclusions.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        exclusions = load_tbca_unavailable_record_exclusions(config_path)
        self.assertIn("diagnostic_sensitivity_only", config["status"])
        self.assertIn("BRC0013C", config["exclusions"]["vegana"][0]["tbca_code"])
        self.assertEqual(exclusions["regular"], set())
        self.assertEqual(exclusions["vegetariana"], set())
        self.assertEqual(exclusions["vegana"], {"Coco, polpa, in natura"})

    def test_exact_exclusion_does_not_mutate_the_source_or_other_profile(self) -> None:
        source = [{"day": {"Lunch": [{"alimento": "Coco, polpa, in natura", "quantidade": 100}]}}]
        exclusions = load_tbca_unavailable_record_exclusions(
            PROJECT_ROOT / "configs" / "tbca-unavailable-record-exclusions.json"
        )
        vegan, removed = prepare_profile_diets(source, "vegana", exclusions["vegana"])
        regular, regular_removed = prepare_profile_diets(source, "regular", exclusions["regular"])
        self.assertEqual(len(removed), 1)
        self.assertEqual(vegan[0]["day"]["Lunch"], [])
        self.assertEqual(regular, source)
        self.assertEqual(regular_removed, [])
        self.assertEqual(source[0]["day"]["Lunch"][0]["quantidade"], 100)

    def test_named_command_runs_the_registered_paired_sensitivity(self) -> None:
        with TemporaryDirectory() as temp:
            workspace = Path(temp) / "run"
            command = commands_for("tbca-record-availability-sensitivity", workspace, 10, 20260938)[0]
        self.assertIn("tests.tbca_record_availability_sensitivity", command)
        self.assertEqual(command[command.index("--runs") + 1], "10")
        self.assertEqual(command[command.index("--seed") + 1], "20260938")

    def test_staging_removes_exactly_40_occurrences_only_when_scenario_is_enabled(self) -> None:
        from diet_optimization.experiments.runner import stage_inputs

        with TemporaryDirectory() as temp:
            workspace = Path(temp) / "workspace"
            paths = stage_inputs(workspace, "rerun", exclude_tbca_unavailable_record_foods=True)
            report = json.loads((workspace / "input-preparation.json").read_text(encoding="utf-8"))
            prepared = json.loads(paths["vegana"].read_text(encoding="utf-8"))
            source = json.loads(
                (workspace / "data" / "diets" / "source" / "dietas-vegana.json").read_text(encoding="utf-8")
            )
        self.assertEqual(report["tbca_unavailable_record_exclusion_counts_by_profile"]["vegana"]["incremental_source_occurrences_removed"], 40)
        self.assertEqual(report["tbca_unavailable_record_exclusion_counts_by_profile"]["regular"]["incremental_source_occurrences_removed"], 0)
        self.assertEqual(report["tbca_unavailable_record_exclusion_counts_by_profile"]["vegetariana"]["incremental_source_occurrences_removed"], 0)
        self.assertEqual(
            sum(1 for plan in source for day in plan.values() for items in day.values()
                for item in items if item.get("alimento") == "Coco, polpa, in natura"),
            40,
        )
        self.assertEqual(
            sum(1 for plan in prepared for day in plan.values() for items in day.values()
                for item in items if item.get("alimento") == "Coco, polpa, in natura"),
            0,
        )


if __name__ == "__main__":
    unittest.main()
