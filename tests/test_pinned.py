import copy
import json
import unittest
from pathlib import Path

from src.pinned import validate_pinned, to_trace, increment_coefficients
from src.pinned_producer import produce_pinned
from src.pinned_checker import verify_pinned
from src.budgets import (
    capacities,
    bottleneck_partition,
    minimum_cost_schedule,
    lower_trace,
    verify_transport,
    verify_budget_transport,
    root_certificate,
)
from src.budget_validation import check_budget_corpus


class PinnedContract(unittest.TestCase):
    def test_empty_pin_increment(self):
        self.assertEqual(increment_coefficients([], [2, 3], 3, 5), [0, 2, 3])

    def test_saturated_pins(self):
        self.assertEqual(increment_coefficients([1, 2], [], 3, 5), [0, 0, 0])

    def test_duplicate_pins_rejected(self):
        with self.assertRaises(ValueError):
            validate_pinned(
                {
                    "field": 5,
                    "threshold": 3,
                    "epochs": 2,
                    "pins": [[1, 1]],
                    "exposed": [[], []],
                }
            )

    def test_pin_budget_separate(self):
        case = {
            "field": 29,
            "threshold": 12,
            "epochs": 12,
            "pins": [list(range(1, 25)) for _ in range(11)],
            "exposed": [list(range(1, 6)) for _ in range(12)],
        }
        self.assertEqual(len(to_trace(case)["observations"]), 324)

    def test_balanced_cut(self):
        exposures = [2] * 4
        pins = [3] * 3
        self.assertEqual(capacities(exposures, pins)["capacity"], 7)
        self.assertEqual(bottleneck_partition(exposures, pins)["width"], 7)

    def test_zero_observations(self):
        self.assertEqual(capacities([0, 0, 0], [24, 24])["capacity"], 0)

    def test_transport_mutation(self):
        record = lower_trace([1, 1, 1], [1, 1], 3, 5)
        self.assertTrue(verify_transport(record))
        record["interpolation_weights"][0] = (
            record["interpolation_weights"][0] + 1
        ) % 5
        self.assertFalse(verify_transport(record))

    def test_budget_transport_accepts_original_and_rejects_over_budget_pin(self):
        corpus = json.loads(
            (Path(__file__).resolve().parents[1] / "cases/budgets.json").read_text()
        )
        case = next(
            row for row in corpus["variable_cases"] if row["id"] == "variable-budget-00"
        )
        gamma = capacities(case["exposures"], case["pins"])["capacity"]
        original = case["lower_witness"]
        self.assertTrue(
            verify_budget_transport(
                original,
                case["exposures"],
                case["pins"],
                gamma,
                corpus["coordinate_pool"],
            )
        )
        mutated = copy.deepcopy(original)
        mutated["case"]["pins"][0] = [3, 4]
        self.assertTrue(verify_transport(mutated))
        self.assertFalse(
            verify_budget_transport(
                mutated,
                case["exposures"],
                case["pins"],
                gamma,
                corpus["coordinate_pool"],
            )
        )

    def test_budget_transport_rejects_over_budget_exposure(self):
        corpus = json.loads(
            (Path(__file__).resolve().parents[1] / "cases/budgets.json").read_text()
        )
        case = corpus["variable_cases"][0]
        gamma = capacities(case["exposures"], case["pins"])["capacity"]
        mutated = copy.deepcopy(case["lower_witness"])
        mutated["case"]["exposed"][1] = [4]
        self.assertTrue(verify_transport(mutated))
        self.assertFalse(
            verify_budget_transport(
                mutated,
                case["exposures"],
                case["pins"],
                gamma,
                corpus["coordinate_pool"],
            )
        )

    def test_budget_transport_rejects_threshold_mismatch(self):
        corpus = json.loads(
            (Path(__file__).resolve().parents[1] / "cases/budgets.json").read_text()
        )
        case = corpus["variable_cases"][0]
        gamma = capacities(case["exposures"], case["pins"])["capacity"]
        mutated = copy.deepcopy(case["lower_witness"])
        mutated["case"]["threshold"] = gamma + 1
        self.assertFalse(
            verify_budget_transport(
                mutated,
                case["exposures"],
                case["pins"],
                gamma,
                corpus["coordinate_pool"],
            )
        )

    def test_full_budget_entry_rejects_over_budget_mutation(self):
        corpus = json.loads(
            (Path(__file__).resolve().parents[1] / "cases/budgets.json").read_text()
        )
        mutated = copy.deepcopy(corpus)
        target = next(
            row for row in mutated["variable_cases"] if row["id"] == "variable-budget-00"
        )
        target["lower_witness"]["case"]["pins"][0] = [3, 4]
        with self.assertRaises(AssertionError):
            check_budget_corpus(mutated)

    def test_explicit_offline_schedule(self):
        result = minimum_cost_schedule(
            [1] * 7, [1, 0, 2, 0, 1, 1], 4, [3, 1, 4, 1, 5, 2]
        )
        self.assertEqual((result["cost"], result["refresh_boundaries"]), (2, [2, 4]))

    def test_forbidden_boundaries(self):
        result = minimum_cost_schedule(
            [1, 1, 1], [0, 0], 3, [1, 1], allowed=[False, False]
        )
        self.assertEqual(result["kind"], "impossible")

    def test_false_root_certificate(self):
        case = {
            "field": 5,
            "threshold": 3,
            "epochs": 3,
            "pins": [[1], [3]],
            "exposed": [[1], [2], [3]],
        }
        with self.assertRaises(ValueError):
            root_certificate(case, [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
