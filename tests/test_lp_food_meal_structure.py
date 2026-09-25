from __future__ import annotations

import unittest
from types import SimpleNamespace

from tests.lp_food_meal_structure_sensitivity import (
    collect_source_support,
    empirical_caps,
    has_feasible_incumbent,
    lower_order_statistic,
    validate_structured_plan,
)
from tests.run_experiments import commands_for
from pathlib import Path
import numpy as np
from scipy import sparse


class LPFoodMealStructureTests(unittest.TestCase):
    def test_lower_order_statistic_uses_documented_noninterpolated_index(self) -> None:
        self.assertEqual(lower_order_statistic([1, 2, 3, 4], 0.95), 3.0)
        self.assertEqual(lower_order_statistic([1, 2, 3, 4], 0.25), 1.0)

    def test_source_support_counts_positive_food_days_and_slots(self) -> None:
        plans = [
            {
                "1": {
                    "Café da Manhã": [
                        {"alimento": "A", "quantidade": "40"},
                        {"alimento": "A", "quantidade": "10"},
                    ],
                    "Almoço": [{"alimento": "B", "quantidade": "80"}],
                },
                "2": {"Café da Manhã": [{"alimento": "A", "quantidade": "30"}]},
            },
            {"1": {"Almoço": [{"alimento": "A", "quantidade": "25"}] }},
        ]
        context = SimpleNamespace(
            tbca_map={"A": "a", "B": "b"},
            tbca_database={
                "a": {"nutrientes": {"Energia": 100}},
                "b": {"nutrientes": {"Energia": 200}},
            },
        )
        support = collect_source_support(plans, context)
        self.assertEqual(support["food_slot_daily_positive_g"][("A", "Café da Manhã")], [50.0, 30.0])
        self.assertEqual(support["food_plan_day_counts"]["A"], [2, 1])
        self.assertEqual(support["daily_distinct_food_counts"], [2, 1, 1])
        self.assertEqual(len(support["meal_energy_shares"]["Almoço"]), 3)

    def test_empirical_caps_are_profile_support_based_and_nonzero(self) -> None:
        support = {
            "food_daily_positive_g": {"A": [10.0, 20.0]},
            "food_slot_daily_positive_g": {("A", "Almoço"): [5.0, 15.0]},
            "food_plan_day_counts": {"A": [1, 3, 4]},
            "meal_energy_shares": {"Almoço": [0.0, 0.2, 0.4, 0.6]},
            "daily_distinct_food_counts": [10, 12, 14, 16],
        }
        caps = empirical_caps(support)
        self.assertEqual(caps["food_day_caps_g"]["A"], 20.0)
        self.assertEqual(caps["food_slot_day_caps_g"][("A", "Almoço")], 15.0)
        self.assertEqual(caps["food_repeat_caps_days_per_plan"]["A"], 3)
        self.assertEqual(caps["meal_energy_share_q05_q95"]["Almoço"], (0.0, 0.4))
        self.assertEqual(caps["daily_distinct_food_q25_floor"], 10)

    def test_named_runner_writes_the_structured_food_experiment(self) -> None:
        workspace = Path("temporary-workspace")
        commands = commands_for(
            "lp-food-meal-structure-sensitivity", workspace, 10, 123, "revised"
        )
        self.assertIn("tests.lp_food_meal_structure_sensitivity", commands[0])

    def test_solver_incumbent_must_satisfy_rows_bounds_and_integrality(self) -> None:
        matrix = sparse.csr_matrix([[1.0, 1.0], [-1.0, 0.0]])
        rhs = np.asarray([2.0, -1.0])
        bounds_low = np.asarray([0.0, 0.0])
        bounds_high = np.asarray([1.0, 3.0])
        integrality = np.asarray([1, 0])
        feasible = type("Result", (), {"x": np.asarray([1.0, 1.0])})()
        infeasible = type("Result", (), {"x": np.asarray([0.0, 3.0])})()
        fractional = type("Result", (), {"x": np.asarray([0.5, 2.0])})()
        self.assertTrue(has_feasible_incumbent(
            feasible, matrix, rhs, bounds_low, bounds_high, integrality
        ))
        self.assertFalse(has_feasible_incumbent(
            infeasible, matrix, rhs, bounds_low, bounds_high, integrality
        ))
        self.assertFalse(has_feasible_incumbent(
            fractional, matrix, rhs, bounds_low, bounds_high, integrality
        ))

    def test_exported_plan_validator_checks_profile_slot_and_empirical_constraints(self) -> None:
        context = SimpleNamespace(
            tbca_map={"A": "a", "B": "b"},
            tbca_database={
                "a": {"nutrientes": {"Energia": 100.0}},
                "b": {"nutrientes": {"Energia": 300.0}},
            },
        )
        plan = {
            str(day): {
                "Café da Manhã": [{"alimento": "A", "quantidade": 50.0}],
                "Almoço": [{"alimento": "B", "quantidade": 50.0}],
            }
            for day in range(1, 6)
        }
        support = {"food_names": ["A", "B"]}
        caps = {
            "food_slot_day_caps_g": {("A", "Café da Manhã"): 60.0, ("B", "Almoço"): 60.0},
            "food_day_caps_g": {"A": 60.0, "B": 60.0},
            "food_repeat_caps_days_per_plan": {"A": 5, "B": 5},
            "daily_distinct_food_q25_floor": 2,
            "meal_energy_share_q05_q95": {"Café da Manhã": (0.2, 0.3), "Almoço": (0.7, 0.8)},
        }
        self.assertEqual(validate_structured_plan(plan, context, support, caps)["status"], "passed")
        plan["1"]["Almoço"][0]["alimento"] = "A"
        self.assertEqual(validate_structured_plan(plan, context, support, caps)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
