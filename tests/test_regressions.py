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
from diet_optimization.optimization.genetic_algorithm import GeneticAlgorithm
from diet_optimization.experiments.resource_monitor import SampledProcessMemory
from diet_optimization.optimization.linear_optimizer import (
    _build_meal_energy_share_constraints,
    _build_nutrient_constraints,
    _compute_food_vectors,
    _solve_relaxed_meal_level,
    food_names_in_diets,
    optimize_food_level,
)
from diet_optimization.optimization.nutritional_targets import load_protocol
from diet_optimization.optimization.hyperparameters import GeneticAlgorithmHyperparameters
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
from tests.lp_food_diversity_sensitivity import observed_order_statistic, source_day_food_counts
from tests.environmental_objective_sensitivity import OBJECTIVES as ENVIRONMENTAL_OBJECTIVES
from tests.environmental_source_audit import compare_rounded_values
from tests.environmental_source_range_sensitivity import METHODS as SOURCE_RANGE_METHODS
from tests.environmental_source_range_sensitivity import PROFILES as SOURCE_RANGE_PROFILES
from tests.environmental_source_range_sensitivity import source_range_maps, summarize_results
from tests.lp_meal_frequency_sensitivity import source_max_repetitions_by_plan
from tests.ga_objective_weight_review import resolve_source_workspace
from tests.food_mapping_exclusion_review import resolve_source_workspace as resolve_mapping_exclusion_workspace
from tests.food_mapping_exclusion_sensitivity import latest_mapping_queue_run_id


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ArtifactPopulationTests(unittest.TestCase):
    def test_lp_execution_audit_records_strict_status_and_fallback(self) -> None:
        from tests.food_mapping_exclusion_review import read_lp_execution_audit

        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            for method_dir in ("pl-alimentos", "pl-refeicoes"):
                for profile in ("regular", "vegetariana", "vegana"):
                    output = workspace / "data/outputs/optimization_runs" / method_dir
                    output.mkdir(parents=True, exist_ok=True)
                    fallback = method_dir == "pl-refeicoes" and profile == "vegana"
                    (output / f"execution-{profile}.json").write_text(json.dumps({
                        "profile": profile,
                        "solver": {"initial_status": 2 if fallback else 0, "fallback_used": fallback},
                        "final_solution": {"meals": []},
                        "metrics_and_violations": {"violation_count": 2},
                    }), encoding="utf-8")
            report = read_lp_execution_audit(workspace)
            self.assertEqual(report["observed_records"], 6)
            self.assertEqual(report["strict_status_zero_records"], 5)
            self.assertEqual(report["relaxed_fallback_records"], 1)
            self.assertEqual(report["records_without_solution"], 0)

    def test_mapping_exclusion_sensitivity_uses_latest_successful_queue_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result_dir = Path(directory)
            fixtures = [
                ("mapping-review-queue-current_old.json", "old", "2026-09-24T10:00:00Z", "passed"),
                ("mapping-review-queue-current_latest.json", "latest", "2026-09-24T11:00:00Z", "passed"),
                ("mapping-review-queue-current_failed.json", "failed", "2026-09-24T12:00:00Z", "failed"),
            ]
            for filename, run_id, started, status in fixtures:
                (result_dir / filename).write_text(json.dumps({
                    "run_id": run_id,
                    "started_at_utc": started,
                    "status": status,
                }), encoding="utf-8")
            self.assertEqual(latest_mapping_queue_run_id(result_dir), "latest")

    def test_pending_mapping_exclusion_config_is_exact_and_scenario_only(self) -> None:
        from diet_optimization.experiments.profile_integrity import load_pending_mapping_exclusions

        config_path = PROJECT_ROOT / "configs" / "pending-food-mapping-exclusions.json"
        exclusions = load_pending_mapping_exclusions(config_path)
        self.assertEqual(set(exclusions), {"regular", "vegetariana", "vegana"})
        self.assertEqual(len(set.union(*exclusions.values())), 8)
        self.assertEqual(tuple(len(exclusions[profile]) for profile in ("regular", "vegetariana", "vegana")), (1, 6, 5))
        self.assertNotIn("Leite, vaca, c/ chocolate", exclusions["vegana"])
        known_exclusions = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
        self.assertIn("Leite, vaca, c/ chocolate", known_exclusions["vegana"])
        self.assertNotIn("Feijoada vegetariana", exclusions["vegana"])
        self.assertNotIn("Feijoada vegetariana", exclusions["vegetariana"])
        self.assertTrue(all(
            "Salada, folhas e vegetais, c/ óleo de soja e c/ sal" not in foods
            for foods in exclusions.values()
        ))

    def test_mapping_exclusion_sensitivity_removes_exact_source_occurrences(self) -> None:
        from diet_optimization.experiments.profile_integrity import load_pending_mapping_exclusions

        pending = load_pending_mapping_exclusions(
            PROJECT_ROOT / "configs" / "pending-food-mapping-exclusions.json"
        )
        known = load_exclusions(PROJECT_ROOT / "configs" / "profile-exclusions.json")
        expected_incremental = {"regular": 17, "vegetariana": 107, "vegana": 132}
        files = {"regular": "regular", "vegetariana": "vegetariana", "vegana": "vegana"}
        for profile, suffix in files.items():
            diets = json.loads(
                (PROJECT_ROOT / "diets-base" / f"dietas-{suffix}.json").read_text(encoding="utf-8")
            )
            _, removals = prepare_profile_diets(diets, profile, known[profile] | pending[profile])
            incremental = sum(
                row["food_name"] in pending[profile] and row["food_name"] not in known[profile]
                for row in removals
            )
            self.assertEqual(incremental, expected_incremental[profile])

    def test_objective_weight_review_resolves_artifact_workspace(self) -> None:
        run_suffix = "20260924T214525756789Z_c954a88c"
        expected = (
            PROJECT_ROOT / "tests" / "results" / "artifacts"
            / f"ga-objective-weight-sensitivity_{run_suffix}" / "audit"
        )
        self.assertEqual(resolve_source_workspace(run_suffix), expected)
        self.assertEqual(
            resolve_source_workspace(f"ga-objective-weight-sensitivity_{run_suffix}"),
            expected,
        )
        with self.assertRaises(ValueError):
            resolve_source_workspace("../outside")

    def test_mapping_exclusion_review_resolves_sensitivity_workspace(self) -> None:
        run_suffix = "20260924T230320788866Z_177f8754"
        expected = (
            PROJECT_ROOT / "tests" / "results" / "artifacts"
            / f"food-mapping-exclusion-sensitivity_{run_suffix}" / "audit"
        )
        self.assertEqual(resolve_mapping_exclusion_workspace(run_suffix), expected)
        self.assertEqual(
            resolve_mapping_exclusion_workspace(f"food-mapping-exclusion-sensitivity_{run_suffix}"),
            expected,
        )
        with self.assertRaises(ValueError):
            resolve_mapping_exclusion_workspace("../outside")

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
            if experiment in {
                "replication-resource-audit", "ga-objective-weight-review",
                "food-mapping-exclusion-review",
            }:
                self.assertTrue(commands_for(experiment, workspace, 10, 20260323, source_run_id="20260924T000000000000Z_abcdef12"))
            else:
                self.assertTrue(commands_for(experiment, workspace, 10, 20260323))
        self.assertIn("tests.ga_hyperparameter_sensitivity", commands_for("ga-hyperparameter-sensitivity", workspace, 1, 7)[0])
        for experiment in ("ga-smoke", "full-replication"):
            commands = commands_for(experiment, workspace, 10, 20260323)
            self.assertIn("tests.validate_candidate_scope", commands[-1])
        self.assertIn("tests.mapping_review_queue", commands_for("mapping-review-queue", workspace, 10, 20260323)[0])
        self.assertIn("unittest", commands_for("unit-tests", workspace, 10, 20260323)[0])
        self.assertIn("--current-maps", commands_for("mapping-review-queue-current", workspace, 10, 20260323)[0])
        self.assertIn("tests.portion_support_audit", commands_for("portion-support-audit", workspace, 10, 20260323)[0])
        self.assertIn("tests.profile_ingredient_audit", commands_for("profile-ingredient-audit", workspace, 10, 20260323)[0])
        self.assertIn("tests.nutrient_missingness_audit", commands_for("nutrient-missingness-audit", workspace, 10, 20260323)[0])
        self.assertEqual(ENVIRONMENTAL_OBJECTIVES, (
            "carbon_footprint", "water_footprint", "ecological_footprint"
        ))
        self.assertIn(
            "tests.environmental_objective_sensitivity",
            commands_for("environmental-objective-sensitivity", workspace, 1, 7)[0],
        )
        self.assertIn(
            "tests.environmental_source_audit",
            commands_for("environmental-source-audit", workspace, 1, 7)[0],
        )
        self.assertIn(
            "tests.environmental_source_range_sensitivity",
            commands_for("environmental-source-range-sensitivity", workspace, 1, 7)[0],
        )
        self.assertIn(
            "tests.ga_objective_weight_sensitivity",
            commands_for("ga-objective-weight-sensitivity", workspace, 10, 20260935)[0],
        )
        self.assertIn(
            "tests.ga_objective_weight_review",
            commands_for("ga-objective-weight-review", workspace, 1, 7, source_run_id="20260924T000000000000Z_abcdef12")[0],
        )
        self.assertIn(
            "tests.food_mapping_exclusion_sensitivity",
            commands_for("food-mapping-exclusion-sensitivity", workspace, 10, 20260937)[0],
        )
        mapping_review_command = commands_for(
            "food-mapping-exclusion-review", workspace, 1, 7,
            source_run_id="20260924T000000000000Z_abcdef12",
        )[0]
        self.assertIn("tests.food_mapping_exclusion_review", mapping_review_command)
        self.assertEqual(mapping_review_command[-2:], ["--output-dir", str(workspace)])
        self.assertIn(
            "tests.lp_meal_frequency_sensitivity",
            commands_for("lp-meal-frequency-sensitivity", workspace, 1, 7)[0],
        )

    def test_environmental_source_audit_checks_rounding_and_ambiguous_rows(self) -> None:
        report = compare_rounded_values(
            {"rice": {
                "carbon_footprint": 101.0,
                "water_footprint": 55.0,
                "ecological_footprint": 0.4,
            }},
            {"rice": [(100.805, 54.579, 0.391), (102.0, 55.1, 0.4)]},
        )
        self.assertEqual(report["exact_prep_label_matches"], 1)
        for metric in report["metrics"].values():
            self.assertEqual(metric["distributed_value_within_rounding_tolerance_of_any_official_row"], 1)
            self.assertEqual(metric["official_prep_labels_with_multiple_values"], 1)

    def test_environmental_source_range_changes_only_ambiguous_active_metric(self) -> None:
        distributed = {
            "ambiguous": {"carbon_footprint": 5.0, "water_footprint": 6.0, "ecological_footprint": 7.0},
            "stable": {"carbon_footprint": 8.0, "water_footprint": 9.0, "ecological_footprint": 10.0},
        }
        source_values = {
            "ambiguous": [(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)],
            "stable": [(8.0, 9.0, 10.0), (8.0, 9.0, 10.0)],
        }
        variants = source_range_maps(distributed, source_values, "carbon_footprint")
        self.assertEqual(variants["changed_ambiguous_labels"], 1)
        self.assertEqual(variants["source_min"]["ambiguous"]["carbon_footprint"], 1.0)
        self.assertEqual(variants["source_max"]["ambiguous"]["carbon_footprint"], 4.0)
        self.assertEqual(variants["source_min"]["ambiguous"]["water_footprint"], 6.0)
        self.assertEqual(variants["source_max"]["stable"], distributed["stable"])
        self.assertEqual(variants["current"], distributed)

    def test_environmental_source_range_summary_requires_and_compares_three_scenarios(self) -> None:
        rows = []
        for profile in SOURCE_RANGE_PROFILES:
            for method in SOURCE_RANGE_METHODS:
                for objective in ("carbon_footprint", "water_footprint", "ecological_footprint"):
                    for scenario, score, plan, fallback, slacks in (
                        ("current", 5.0, "plan-a", False, 0),
                        ("source_min", 4.0, "plan-a", False, 0),
                        ("source_max", 7.0, "plan-b", True, 2),
                    ):
                        rows.append({
                            "profile": profile,
                            "method": method,
                            "objective": objective,
                            "coefficient_scenario": scenario,
                            "mean_daily_footprints": {objective: score},
                            "final_solution": [plan],
                            "solver": {
                                "fallback_used": fallback,
                                "slack_analysis": {"nonzero_slack_count": slacks},
                            },
                        })
        summary = next(
            row for row in summarize_results(rows)
            if row["profile"] == "regular" and row["method"] == "LP-Meal"
            and row["objective"] == "carbon_footprint"
        )
        self.assertEqual(summary["optimized_endpoint_score_min"], 4.0)
        self.assertEqual(summary["optimized_endpoint_score_max"], 7.0)
        self.assertFalse(summary["selected_plan_unchanged_across_scenarios"])
        self.assertEqual(summary["fallback_scenarios"], ["source_max"])
        self.assertEqual(summary["nonzero_slack_count_by_scenario"]["source_max"], 2)

    def test_ga_sensitivity_variants_are_versioned_and_loadable(self) -> None:
        from tests.ga_hyperparameter_sensitivity import VARIANTS

        self.assertEqual(
            set(VARIANTS),
            {"baseline", "reduced-population", "higher-mutation", "shorter-stagnation", "repair-disabled"},
        )
        for relative_path in VARIANTS.values():
            if relative_path is None:
                continue
            payload = json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))
            self.assertTrue(payload)

    def test_paired_sensitivity_summary_is_deterministic(self) -> None:
        from tests.ga_sensitivity_review import paired_summary

        result = paired_summary([1.0, 2.0, 3.0], seed=17)
        self.assertEqual(result["n_pairs"], 3)
        self.assertEqual(result["mean_difference"], 2.0)
        self.assertEqual(result, paired_summary([1.0, 2.0, 3.0], seed=17))

    def test_sensitivity_review_reads_execution_cost_metrics(self) -> None:
        from tests.ga_sensitivity_review import read_computational_metrics

        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            record = {
                "resolution": "ag-alimentos",
                "candidate_pool_profile": "regular",
                "execution_id": 1,
                "duration_seconds": 2.5,
                "fitness_evaluation_count": 400,
                "stop_generation": 30,
                "process_memory": {"peak_sampled_rss_bytes": 1024},
            }
            (workspace / "execution-001.json").write_text(
                json.dumps(record), encoding="utf-8"
            )
            metrics = read_computational_metrics(workspace)
        self.assertEqual(metrics[("regular", "GA-Food", "runtime_seconds", 1)], 2.5)
        self.assertEqual(metrics[("regular", "GA-Food", "fitness_evaluations", 1)], 400.0)
        self.assertEqual(metrics[("regular", "GA-Food", "stopping_generation", 1)], 30.0)
        self.assertEqual(metrics[("regular", "GA-Food", "sampled_peak_rss_bytes", 1)], 1024.0)

    def test_missingness_complete_case_is_numeric_and_keeps_reported_zero(self) -> None:
        protocol = {
            "core_targets": [{"nutrient": "A", "tbca_field": "A"}],
            "additional_rules": [{"nutrient": "B", "tbca_field": "B", "upper": 10, "model_rule": "hard daily upper bound"}],
        }
        nutrients = required_nutrients(protocol)
        self.assertEqual([row["tbca_field"] for row in nutrients], ["A", "B"])
        plans = [{"1": {"Almoço": [
            {"alimento": "complete", "quantidade": 100},
            {"alimento": "reported-zero", "quantidade": 50},
            {"alimento": "missing", "quantidade": 25},
        ], "Ceia": [
            {"alimento": "complete", "quantidade": 100},
            {"alimento": "reported-zero", "quantidade": 50},
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
        self.assertEqual(summary["strict_complete_case_meal_candidates_by_type"]["Almoço"]["complete_case_meals"], 0)
        self.assertEqual(summary["strict_complete_case_meal_candidates_by_type"]["Ceia"]["complete_case_meals"], 1)
        self.assertEqual(summary["meal_types_without_complete_case_candidates"], ["Almoço"])
        self.assertEqual(summary["required_meal_types_without_complete_case_candidates"], ["Almoço"])

    def test_mapping_review_queue_never_auto_accepts_fuzzy_candidates(self) -> None:
        queue = build_queue()
        self.assertEqual(len(queue), 168)
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

    def test_daily_quantity_support_uses_positive_daily_totals_and_labeled_fallback(self) -> None:
        from tests.lp_daily_quantity_support_sensitivity import cap_map, daily_quantity_support

        plans = [
            {"1": {"Lunch": [
                {"alimento": "rice", "quantidade": "40"},
                {"alimento": "rice", "quantidade": "10"},
            ]}},
            {"1": {"Dinner": [{"alimento": "rice", "quantidade": "80"}]}},
        ]
        rows = daily_quantity_support(plans)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["positive_days"], 2)
        self.assertEqual(rows[0]["minimum_positive_daily_g"], 50.0)
        self.assertEqual(rows[0]["observed_max_daily_g"], 80.0)
        self.assertIsNone(rows[0]["p95_positive_daily_g"])
        self.assertEqual(rows[0]["p95_cap_basis"], "observed_max_fallback_below_20_positive_days")
        self.assertEqual(cap_map(rows, "p95_positive_or_max_fallback"), {"rice": 80.0})

    def test_lp_food_enforces_optional_daily_quantity_caps(self) -> None:
        context = NutritionalContext(
            tbca_map={"preferred": "1", "alternative": "2"},
            tbca_database={
                "1": {"nutrientes": {"Energy": 100.0}},
                "2": {"nutrientes": {"Energy": 100.0}},
            },
            footprint_map={
                "preferred": {"carbon_footprint": 1.0},
                "alternative": {"carbon_footprint": 2.0},
            },
        )
        diagnostics: dict = {}
        solution = optimize_food_level(
            context,
            allowed_food_names={"preferred", "alternative"},
            minimum_goals={"Energy": 100.0},
            maximum_goals={"Energy": {"meta": 200.0, "tolerancia": 1.0}},
            maximum_daily_grams_by_food={"preferred": 40.0, "alternative": 100.0},
            diagnostics=diagnostics,
        )
        self.assertIsNotNone(solution)
        day_items = solution[0]["1"]["Refeição LP"]
        quantities = {item["alimento"]: float(item["quantidade"]) for item in day_items}
        self.assertLessEqual(quantities.get("preferred", 0.0), 40.0)
        self.assertEqual(diagnostics["daily_quantity_capped_food_count"], 2)
        self.assertEqual(diagnostics["daily_quantity_caps_g"]["preferred"], 40.0)
        with self.assertRaisesRegex(ValueError, "outside the eligible LP-Food pool"):
            optimize_food_level(
                context,
                allowed_food_names={"preferred", "alternative"},
                minimum_goals={"Energy": 100.0},
                maximum_goals={"Energy": {"meta": 200.0, "tolerancia": 1.0}},
                maximum_daily_grams_by_food={"not-in-pool": 40.0},
            )

    def test_lp_food_milp_enforces_observed_diversity_floor_and_caps(self) -> None:
        context = NutritionalContext(
            tbca_map={"food_a": "1", "food_b": "2", "food_c": "3"},
            tbca_database={
                "1": {"nutrientes": {"Energy": 100.0}},
                "2": {"nutrientes": {"Energy": 100.0}},
                "3": {"nutrientes": {"Energy": 100.0}},
            },
            footprint_map={
                "food_a": {"carbon_footprint": 1.0},
                "food_b": {"carbon_footprint": 2.0},
                "food_c": {"carbon_footprint": 3.0},
            },
        )
        diagnostics: dict = {}
        solution = optimize_food_level(
            context,
            allowed_food_names={"food_a", "food_b", "food_c"},
            minimum_goals={"Energy": 200.0},
            maximum_goals={"Energy": {"meta": 300.0, "tolerancia": 1.0}},
            maximum_daily_grams_by_food={"food_a": 100.0, "food_b": 100.0, "food_c": 100.0},
            minimum_selected_foods=2,
            diagnostics=diagnostics,
        )
        self.assertIsNotNone(solution)
        quantities = [
            float(item["quantidade"])
            for item in solution[0]["1"]["Refeição LP"]
        ]
        self.assertGreaterEqual(sum(quantity >= 1.0 for quantity in quantities), 2)
        self.assertEqual(diagnostics["method"], "highs-milp")
        self.assertEqual(diagnostics["minimum_selected_foods"], 2)
        with self.assertRaisesRegex(ValueError, "finite daily quantity cap is required"):
            optimize_food_level(
                context,
                allowed_food_names={"food_a", "food_b", "food_c"},
                minimum_goals={"Energy": 100.0},
                maximum_goals={"Energy": {"meta": 300.0, "tolerancia": 1.0}},
                maximum_daily_grams_by_food={"food_a": 100.0},
                minimum_selected_foods=2,
            )

    def test_lp_meal_repetition_cap_deduplicates_recipes_and_survives_fallback(self) -> None:
        from diet_optimization.optimization.linear_optimizer import optimize_meal_level

        context = NutritionalContext(
            tbca_map={"rice": "1"},
            tbca_database={"1": {"nutrientes": {"Energy": 100.0}}},
            footprint_map={"rice": {"carbon_footprint": 1.0}},
        )
        repeated_source_plan = {
            "1": {"Café da Manhã": [{"alimento": "rice", "quantidade": "100"}]},
            "2": {"Café da Manhã": [{"alimento": "rice", "quantidade": "100"}]},
        }
        diagnostics: dict = {}
        solution = optimize_meal_level(
            [repeated_source_plan],
            context,
            days_per_plan=2,
            meal_energy_share_limits={},
            diagnostics=diagnostics,
            minimum_goals={"Energy": 0.0},
            maximum_goals={"Energy": {"meta": 1000.0, "tolerancia": 1.0}},
            maximum_repetitions_per_unique_meal=1,
        )
        self.assertIsNone(solution)
        self.assertEqual(diagnostics["meal_candidate_counts_before_deduplication"]["Café da Manhã"], 2)
        self.assertEqual(diagnostics["meal_candidate_counts"]["Café da Manhã"], 1)
        self.assertTrue(diagnostics["fallback_used"])
        self.assertEqual(diagnostics["fallback_status"], 2)

    def test_source_meal_repetition_support_counts_exact_slot_recipe_repeats(self) -> None:
        plans = [{
            "1": {"Lunch": [{"alimento": "rice", "quantidade": "80"}]},
            "2": {"Lunch": [{"alimento": "rice", "quantidade": "80"}]},
            "3": {"Lunch": [{"alimento": "rice", "quantidade": "60"}]},
        }]
        self.assertEqual(source_max_repetitions_by_plan(plans), [2])

    def test_diversity_floor_uses_observed_lower_order_statistic(self) -> None:
        self.assertEqual(observed_order_statistic([20, 12, 17, 15], 0.25), 12)
        plans = [{"1": {"Lunch": [
            {"alimento": "rice", "quantidade": "80"},
            {"alimento": "beans", "quantidade": "0"},
        ]}}]
        self.assertEqual(source_day_food_counts(plans), [1])

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
        evidenced = [row for row in rows if row["review_status"] == "SOURCE_RECIPE_EVIDENCE_VERIFIED_FOR_TARGET_ONLY"]
        pending = [row for row in rows if row["review_status"] == "PENDING_INGREDIENT_VERIFICATION"]
        self.assertEqual((len(rows), len(evidenced), len(pending)), (364, 9, 353))
        self.assertTrue(all(row["ingredient_evidence"].startswith("configs/profile-exclusions.json") for row in excluded))
        kale = next(row for row in rows if row["food_name"].startswith("Couve, manteiga") and row["profile"] == "vegana")
        self.assertEqual(kale["lexical_risk_hits"], {})
        self.assertEqual(kale["review_status"], "PENDING_INGREDIENT_VERIFICATION")
        for profile in ("vegetariana", "vegana"):
            salad = next(
                row for row in rows
                if row["food_name"] == "Salada, folhas e vegetais, c/ óleo de soja e c/ sal"
                and row["profile"] == profile
            )
            self.assertEqual(salad["review_status"], "SOURCE_RECIPE_EVIDENCE_VERIFIED_FOR_TARGET_ONLY")
            self.assertIn("tbca.net.br", salad["ingredient_evidence"])
        feijoada = next(row for row in rows if row["food_name"] == "Feijoada vegetariana" and row["profile"] == "vegana")
        self.assertEqual(feijoada["review_status"], "SOURCE_RECIPE_EVIDENCE_VERIFIED_FOR_TARGET_ONLY")
        self.assertIn("tbca.net.br", feijoada["ingredient_evidence"])

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
    def test_process_memory_sampler_records_sampled_rss_metadata(self) -> None:
        import time

        sampler = SampledProcessMemory(interval_seconds=0.01)
        sampler.start()
        time.sleep(0.03)
        result = sampler.stop()
        self.assertEqual(result["measurement"], "sampled_process_rss_100ms")
        self.assertGreaterEqual(result["sample_count"], 1)
        if result["baseline_rss_bytes"] is not None:
            self.assertGreaterEqual(result["peak_sampled_rss_bytes"], result["baseline_rss_bytes"])

    def test_ga_counts_exact_fitness_evaluations(self) -> None:
        from unittest.mock import patch

        optimizer = GeneticAlgorithm(
            meal_pool={}, food_pool={}, nutritional_context=None,
            hyperparameters=GeneticAlgorithmHyperparameters(),
        )
        with patch(
            "diet_optimization.optimization.genetic_algorithm.evaluate_diet_fitness",
            return_value=-1.0,
        ):
            self.assertEqual(optimizer.fitness_evaluation_count, 0)
            optimizer._evaluate_chromosome_fitness([])
            optimizer._evaluate_chromosome_fitness([])
        self.assertEqual(optimizer.fitness_evaluation_count, 2)

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
        self.assertEqual(len(adjudication["source_food_names"]), 162)
        self.assertEqual(totals["non_identity_mappings_with_recorded_target_decision"], 162)
        self.assertEqual(totals["non_identity_mappings_without_recorded_target_decision"], 8)
        self.assertEqual(len(mapping_lines), totals["unique_food_names"] + 1)
        self.assertEqual(len(current_queue), 8)
        self.assertTrue(all(row["automatic_acceptance"] is False for row in current_queue))


class RevisedNutritionProtocolTests(unittest.TestCase):
    def test_ga_sensitivity_overrides_are_narrow_and_validated(self) -> None:
        from diet_optimization.experiments.runner import apply_ga_overrides

        parameters = GeneticAlgorithmHyperparameters()
        applied = apply_ga_overrides(
            parameters,
            {
                "population_size": 30,
                "default_local_mutation_rate": 0.3,
                "environmental_criterion_weight": 0.5,
                "enable_crossover_repair": False,
            },
        )
        self.assertEqual(applied["population_size"], 30)
        self.assertEqual(parameters.default_local_mutation_rate, 0.3)
        self.assertEqual(parameters.environmental_criterion_weight, 0.5)
        self.assertFalse(parameters.enable_crossover_repair)
        self.assertTrue(apply_ga_overrides(parameters, {"enable_crossover_repair": True})["enable_crossover_repair"])
        with self.assertRaisesRegex(ValueError, "Unsupported GA override"):
            apply_ga_overrides(parameters, {"nutritional_minimum_goals": {}})
        with self.assertRaisesRegex(ValueError, "Invalid value"):
            apply_ga_overrides(parameters, {"population_size": True})
        with self.assertRaisesRegex(ValueError, "Invalid value"):
            apply_ga_overrides(parameters, {"enable_crossover_repair": 1})
        with self.assertRaisesRegex(ValueError, "at most"):
            apply_ga_overrides(parameters, {"default_local_mutation_rate": 1.1})
        with self.assertRaisesRegex(ValueError, "at most"):
            apply_ga_overrides(parameters, {"environmental_criterion_weight": 10.1})

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
        provenance = manifest["source_provenance"]
        self.assertRegex(provenance["git_commit"], r"^[0-9a-f]{40}$")
        self.assertIsInstance(provenance["git_worktree_dirty"], bool)
        self.assertEqual(
            set(provenance["input_sha256"]),
            {
                "configs/revised-nutrition-protocol.json",
                "configs/profile-exclusions.json",
                "configs/pending-food-mapping-exclusions.json",
                "configs/tbca-unavailable-record-exclusions.json",
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
            },
        )
        self.assertTrue(all(len(value) == 64 for value in provenance["input_sha256"].values()))
        self.assertFalse(manifest["pending_mapping_exclusions_enabled"])
        self.assertFalse(manifest["tbca_unavailable_record_exclusions_enabled"])

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
