from __future__ import annotations

import unittest

from tests.ga_objective_trace_audit import validate_trace


class GaObjectiveTraceAuditTests(unittest.TestCase):
    def test_valid_trace_reconstructs_generation_scores(self) -> None:
        trace = []
        history = []
        for index, (nutrition, environment) in enumerate(((8.0, 2.0), (3.0, 2.5))):
            fitness = -(nutrition + environment)
            history.append(fitness)
            trace.append({
                "generation": index,
                "cumulative_fitness_evaluations": 20 + index * 10,
                "fitness": fitness,
                "weighted_nutritional_penalty": nutrition,
                "weighted_environmental_penalty": environment,
                "weighted_meal_energy_share_penalty": 0.0,
            })
        result = validate_trace({"objective_by_generation": history,
                                 "objective_components_by_generation": trace})
        self.assertEqual(result["generations"], 2)
        self.assertEqual(result["final_fitness"], -5.5)

    def test_trace_rejects_scalar_decomposition_mismatch(self) -> None:
        row = {"generation": 0, "cumulative_fitness_evaluations": 1, "fitness": -4.0,
               "weighted_nutritional_penalty": 2.0,
               "weighted_environmental_penalty": 2.0,
               "weighted_meal_energy_share_penalty": 0.0}
        with self.assertRaisesRegex(ValueError, "mismatch"):
            validate_trace({"objective_by_generation": [-3.0],
                            "objective_components_by_generation": [row]})

    def test_trace_rejects_non_monotonic_evaluation_counter(self) -> None:
        rows = []
        for index, count in enumerate((10, 9)):
            rows.append({"generation": index, "cumulative_fitness_evaluations": count,
                         "fitness": -1.0, "weighted_nutritional_penalty": 1.0,
                         "weighted_environmental_penalty": 0.0,
                         "weighted_meal_energy_share_penalty": 0.0})
        with self.assertRaisesRegex(ValueError, "evaluation count"):
            validate_trace({"objective_by_generation": [-1.0, -1.0],
                            "objective_components_by_generation": rows})


if __name__ == "__main__":
    unittest.main()
