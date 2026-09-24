"""Fast deterministic checks; no full GA execution is performed here."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from diet_optimization.analysis.diet_audit import audit
from diet_optimization.optimization.pipeline import derive_execution_seed
from diet_optimization.optimization.linear_optimizer import (
    _build_meal_energy_share_constraints,
    _build_nutrient_constraints,
    _compute_food_vectors,
    _solve_relaxed_meal_level,
    food_names_in_diets,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.fitness_functions import criterion_penalty_for_nutritional_constraints
from diet_optimization.experiments.profile_integrity import load_exclusions, prepare_profile_diets
from diet_optimization.analysis.run_statistics import STATISTICAL_READINESS_STATUS, summarize_values
from diet_optimization.optimization.data_types import NutritionalContext
from diet_optimization.experiments.diagnostics import environment_metadata, evaluate_plan
from tests.validate_candidate_scope import item_names
from tests.run_experiments import EXPERIMENTS, commands_for
from tests.mapping_review_queue import build_queue, normalize_name
from tests.portion_support_audit import collect_support
from tests.profile_ingredient_audit import build_queue as build_profile_ingredient_queue, risk_hits
from tests.nutrient_missingness_audit import required_nutrients, summarize_profile


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
        for experiment in ("ga-smoke", "full-replication"):
            commands = commands_for(experiment, workspace, 10, 20260323)
            self.assertIn("tests.validate_candidate_scope", commands[-1])
        self.assertIn("tests.mapping_review_queue", commands_for("mapping-review-queue", workspace, 10, 20260323)[0])
        self.assertIn("--current-maps", commands_for("mapping-review-queue-current", workspace, 10, 20260323)[0])
        self.assertIn("tests.portion_support_audit", commands_for("portion-support-audit", workspace, 10, 20260323)[0])
        self.assertIn("tests.profile_ingredient_audit", commands_for("profile-ingredient-audit", workspace, 10, 20260323)[0])
        self.assertIn("tests.nutrient_missingness_audit", commands_for("nutrient-missingness-audit", workspace, 10, 20260323)[0])

    def test_missingness_complete_case_is_numeric_and_keeps_reported_zero(self) -> None:
        protocol = {
            "core_targets": [{"nutrient": "A", "tbca_field": "A"}],
            "additional_rules": [{"nutrient": "B", "tbca_field": "B", "upper": 10, "model_rule": "hard daily upper bound"}],
        }
        nutrients = required_nutrients(protocol)
        self.assertEqual([row["tbca_field"] for row in nutrients], ["A", "B"])
        plans = [{"1": {"Lunch": [
            {"alimento": "complete", "quantidade": 100},
            {"alimento": "reported-zero", "quantidade": 50},
            {"alimento": "missing", "quantidade": 25},
        ]}}]
        summary, field_rows, food_rows = summarize_profile(
            "vegan", plans, {"complete": "1", "reported-zero": "2", "missing": "3"},
            {
                "1": {"nutrientes": {"A": 1, "B": 2}},
                "2": {"nutrientes": {"A": 0, "B": 2}},
                "3": {"nutrientes": {"A": None, "B": 2}},
            },
            nutrients,
        )
        self.assertEqual(summary["strict_complete_case_foods_retained"], 2)
        self.assertEqual(summary["strict_complete_case_occurrences_excluded"], 1)
        self.assertEqual(summary["strict_complete_case_grams_excluded"], 25)
        self.assertEqual(field_rows[0]["occurrences_exposed_to_missing_value"], 1)
        self.assertTrue(next(row for row in food_rows if row["food_original"] == "reported-zero")["strict_complete_case_retained"])

    def test_mapping_review_queue_never_auto_accepts_fuzzy_candidates(self) -> None:
        queue = build_queue()
        self.assertEqual(len(queue), 170)
        self.assertTrue(all(row["review_status"] == "PENDING_MANUAL_REVIEW" for row in queue))
        self.assertTrue(all(row["automatic_acceptance"] is False for row in queue))
        self.assertTrue(all(row["decision"] == "" for row in queue))
        self.assertIn("evidence_url_or_reference", queue[0])
        self.assertTrue(all(len(row["suggestions"]) == 5 for row in queue))
        self.assertEqual(normalize_name("Pão francês, c/ óleo"), "pao frances oleo")
        self.assertEqual(sum(row["current_target_normalized_match"] for row in queue), 95)
        tomato = next(row for row in queue if row["food_original"].startswith("Tomate"))
        self.assertIn("Tomate", tomato["suggestions"][0]["candidate_name"])

    def test_portion_support_keeps_profile_meal_observations_separate(self) -> None:
        plans = [{"1": {"Lunch": [{"alimento": "beans", "quantidade": 100}]}}]
        rows = collect_support("regular", plans)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["minimum_positive_g"], 100.0)
        self.assertIsNone(rows[0]["p05_positive_g"])
        self.assertFalse(rows[0]["is_serving_recommendation"])

    def test_profile_ingredient_screen_flags_known_animal_terms_without_deciding(self) -> None:
        self.assertIn("meat_or_fish", risk_hits("Feijao cozido com carne de boi", "vegana"))
        self.assertIn("dairy", risk_hits("Leite de vaca integral", "vegana"))
        self.assertEqual(risk_hits("Couve, manteiga, refogada", "vegana"), {})
        self.assertIn("dairy", risk_hits("Couve refogada com manteiga", "vegana"))
        self.assertIn("meat_or_fish", risk_hits("Omelete, frios, c/ sal", "vegetariana"))
        self.assertEqual(risk_hits("Coco, leite", "vegana"), {})
        self.assertIn("dairy", risk_hits("Leite, vaca, c/ coco", "vegana"))
        self.assertIn("dairy", risk_hits("Tapioca, c/ leite condensado e coco", "vegana"))
        self.assertIn("dairy", risk_hits("Leite de coco misturado a leite integral", "vegana"))
        self.assertIn("other_animal_derived", risk_hits("Mel, natural", "vegana"))
        self.assertEqual(risk_hits("Melancia, polpa, in natura", "vegana"), {})
        self.assertEqual(risk_hits("Iogurte natural", "vegetariana"), {})
        self.assertEqual(risk_hits("Ovo, galinha, cozido", "vegetariana"), {})
        self.assertEqual(risk_hits("Coco, leite", "vegana"), {})
        self.assertEqual(risk_hits("Tapioca, sem manteiga", "vegana"), {})
        self.assertIn("egg", risk_hits("Omelete de vegetais", "vegana"))

    def test_profile_ingredient_audit_marks_only_configured_exact_exclusions(self) -> None:
        rows = build_profile_ingredient_queue()
        excluded = [row for row in rows if row["review_status"] == "EXCLUDED_FROM_DERIVED_PROFILE_POOL"]
        self.assertEqual(len(excluded), 2)
        self.assertTrue(all(row["ingredient_evidence"].startswith("configs/profile-exclusions.json") for row in excluded))
        kale = next(row for row in rows if row["food_name"].startswith("Couve, manteiga") and row["profile"] == "vegana")
        self.assertEqual(kale["lexical_risk_hits"], {})
        self.assertEqual(kale["review_status"], "PENDING_INGREDIENT_VERIFICATION")

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


class ExecutionDiagnosticsTests(unittest.TestCase):
    def test_relaxed_lp_exports_named_absolute_and_relative_slacks(self) -> None:
        diagnostics = {
            "inequality_constraints": [
                {"constraint": "Protein:minimum", "kind": "nutrient_minimum",
                 "nutrient": "Protein", "target": 1.0, "unit": "g_over_plan"},
                {"constraint": "Sodium:maximum", "kind": "nutrient_maximum",
                 "nutrient": "Sodium", "target": 0.0, "unit": "mg_over_plan"},
            ]
        }
        solution = _solve_relaxed_meal_level(
            c=np.array([0.0]),
            A_ub=np.array([[-1.0], [1.0]]),
            b_ub=np.array([-1.0, 0.0]),
            A_eq=np.zeros((0, 1)),
            b_eq=np.zeros(0),
            variable_list=[("breakfast", 0)],
            days_per_plan=1,
            big_m=1.0,
            diagnostics=diagnostics,
        )
        self.assertIsNotNone(solution)
        self.assertTrue(diagnostics["slack_analysis"]["used"])
        self.assertGreater(diagnostics["slack_analysis"]["nonzero_slack_count"], 0)
        self.assertEqual(
            [row["constraint"] for row in diagnostics["slack_analysis"]["constraints"]],
            ["Protein:minimum", "Sodium:maximum"],
        )
        self.assertIsNotNone(
            diagnostics["slack_analysis"]["constraints"][0]["slack_relative_to_target"]
        )
        self.assertIsNone(
            diagnostics["slack_analysis"]["constraints"][1]["slack_relative_to_target"]
        )

    def test_scope_audit_extracts_foods_from_nested_plans(self) -> None:
        plan = {
            "1": {"Lunch": [{"alimento": "beans", "quantidade": 100}]},
            "2": {"Dinner": [{"alimento": "rice", "quantidade": 150}]},
        }
        self.assertEqual(item_names(plan), {"beans", "rice"})

    def test_run_statistics_refuses_to_invent_single_run_interval(self) -> None:
        self.assertIn("missingness", STATISTICAL_READINESS_STATUS)
        self.assertIn("method_equivalence", STATISTICAL_READINESS_STATUS)
        one = summarize_values([10.0], 123)
        self.assertIsNone(one["sample_sd"])
        self.assertIsNone(one["mean_bootstrap_percentile_95_ci"])
        repeated = summarize_values([10.0, 20.0, 30.0], 123, bootstrap_draws=100)
        self.assertEqual(repeated["median"], 20.0)
        self.assertEqual(repeated["sample_sd"], 10.0)
        self.assertEqual(repeated["mean_bootstrap_percentile_95_ci"],
                         summarize_values([10.0, 20.0, 30.0], 123, bootstrap_draws=100)["mean_bootstrap_percentile_95_ci"])

    def test_known_vegan_contradictions_are_removed_only_from_derived_copy(self) -> None:
        source = json.loads((PROJECT_ROOT / "diets-base" / "dietas-vegana.json").read_text(encoding="utf-8"))
        excluded = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")["vegana"]
        prepared, removals = prepare_profile_diets(source, "vegana", excluded)
        self.assertEqual(len(removals), 5)
        self.assertEqual(len(source), len(prepared))
        self.assertTrue(excluded <= food_names_in_diets(source))
        self.assertFalse(excluded & food_names_in_diets(prepared))

    def test_lp_food_candidates_are_restricted_to_source_profile(self) -> None:
        diets = [{"1": {"Lunch": [{"alimento": "tofu", "quantidade": 100}]}}]
        allowed = food_names_in_diets(diets)
        self.assertEqual(allowed, {"tofu"})
        names, _, _ = _compute_food_vectors(
            {"tofu": "1", "beef": "2"},
            {"1": {"nutrientes": {"Energia": 100}}, "2": {"nutrientes": {"Energia": 200}}},
            {"tofu": {"carbon_footprint": 10}, "beef": {"carbon_footprint": 20}},
            allowed,
        )
        self.assertEqual(names, ["tofu"])

    def test_violations_include_daily_and_plan_mean(self) -> None:
        context = NutritionalContext(
            tbca_map={"test-food": "1"},
            tbca_database={"1": {"nutrientes": {"Energia": 100.0}}},
            footprint_map={"test-food": {"carbon_footprint": 20.0}},
        )
        plan = {"1": {"Lunch": [{"alimento": "test-food", "quantidade": "100"}]}}
        report = evaluate_plan(plan, context)
        self.assertEqual(report["mean_daily_nutrients"]["Energia"], 100.0)
        self.assertEqual(report["mean_daily_footprints"]["carbon_footprint"], 20.0)
        self.assertTrue(any(v["nutrient"] == "Energia" for v in report["daily"][0]["violations"]))
        self.assertTrue(any(v["nutrient"] == "Energia" for v in report["mean_daily_violations"]))
        self.assertTrue(report["nutrient_data_coverage"]["missing_values_are_currently_scored_as_zero"])
        self.assertEqual(report["nutrient_data_coverage"]["by_nutrient"]["Energia"]["missing_occurrences"], 0)

    def test_environment_identifies_lp_backend(self) -> None:
        report = environment_metadata()
        self.assertTrue(report["os"])
        self.assertGreater(report["logical_cpu_count"], 0)
        self.assertTrue(report["physical_ram_bytes"])
        self.assertTrue(report["dependencies"]["scipy"])
        self.assertEqual(report["lp_solver"]["method"], "highs")


class BaseDietAuditTests(unittest.TestCase):
    def test_all_150_base_diets_are_auditable_and_mapped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "audit"
            totals = audit(output)["totals"]
            mapping_lines = (output / "food_mapping_audit.csv").read_text(
                encoding="utf-8"
            ).splitlines()
            current_queue = build_queue(output / "food_mapping_audit.csv")

        self.assertEqual(totals["plans"], 150)
        self.assertEqual(totals["plans_with_valid_schema"], 150)
        self.assertEqual(totals["unmapped_tbca_occurrences"], 0)
        self.assertEqual(totals["unmapped_environmental_occurrences"], 0)
        self.assertEqual(
            totals["identity_food_mappings"]
            + totals["non_identity_mappings_with_recorded_target_decision"]
            + totals["non_identity_mappings_without_recorded_target_decision"],
            totals["unique_food_names"],
        )
        adjudication = json.loads(
            (PROJECT_ROOT / "archive/audits/adjudicated-food-map-sources.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(adjudication["source_food_names"]), 84)
        self.assertEqual(totals["non_identity_mappings_with_recorded_target_decision"], 84)
        self.assertEqual(totals["non_identity_mappings_without_recorded_target_decision"], 86)
        self.assertEqual(len(mapping_lines), totals["unique_food_names"] + 1)
        self.assertEqual(len(current_queue), 86)
        self.assertTrue(all(row["automatic_acceptance"] is False for row in current_queue))


class RevisedNutritionProtocolTests(unittest.TestCase):
    def test_meal_energy_share_constraints_use_injected_energy_target(self) -> None:
        matrix, bounds = _build_meal_energy_share_constraints(
            meal_pool={
                "Café da Manhã": [{"nutrientes": {"Energia": 100.0}}]
            },
            variable_list=[("Café da Manhã", 0)],
            n_vars=1,
            days_per_plan=1,
            meal_energy_share_limits={"Café da Manhã": {"min": 0.5, "max": 0.75}},
            energy_target_kcal=200.0,
        )
        np.testing.assert_allclose(matrix[:, 0], [-100.0, 100.0])
        np.testing.assert_allclose(bounds, [-100.0, 150.0])

    def test_protocol_loader_builds_expected_primary_and_secondary_constraints(self) -> None:
        protocol = load_protocol(PROJECT_ROOT / "configs" / "revised-nutrition-protocol.json")
        self.assertEqual(protocol["protocol_id"], "ieee2026-revision-adult-female-30-v1")
        self.assertEqual(protocol["minimum_goals"]["Energia"], 1900.0)
        self.assertEqual(protocol["maximum_goals"]["Energia"]["meta"], 2100.0)
        self.assertEqual(protocol["maximum_goals"]["S\u00f3dio"]["meta"], 2000.0)
        self.assertNotIn("Colesterol", protocol["maximum_goals"])
        self.assertEqual([target["nutrient"] for target in protocol["secondary_targets"]], ["Ferro"])

    def test_rerun_manifest_cannot_label_unreviewed_data_as_final(self) -> None:
        from diet_optimization.experiments.runner import write_manifest

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            write_manifest(workspace, "rerun", 1, 7, [], "test-protocol", "abc")
            manifest = json.loads((workspace / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(
            manifest["scientific_readiness"],
            "diagnostic_pending_food_mapping_review_and_nutrient_missingness_sensitivity",
        )

    def test_injected_protocol_targets_drive_ga_penalty_and_lp_constraints(self) -> None:
        minimums = {"Energia": 100.0, "Prote\u00edna": 40.0}
        maximums = {"Energia": {"meta": 120.0, "tolerancia": 1.0}}
        penalty = criterion_penalty_for_nutritional_constraints(
            {"Energia": 90.0, "Prote\u00edna": 20.0},
            minimum_goals=minimums,
            maximum_goals=maximums,
        )
        self.assertGreater(penalty, 0)

        matrix, bounds = _build_nutrient_constraints(
            {"Energia": np.array([1.0]), "Prote\u00edna": np.array([1.0])},
            1,
            minimum_goals=minimums,
            maximum_goals=maximums,
        )
        self.assertEqual(matrix.shape, (3, 1))
        self.assertEqual(bounds.tolist(), [-100.0, -40.0, 120.0])

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
