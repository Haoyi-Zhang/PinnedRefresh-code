"""Threshold/capacity and explicit-pool regressions for benign budget witnesses."""
import copy
import unittest

from src.budgets import lower_trace, verify_budget_trace, verify_budget_transport


class BudgetTransportContract(unittest.TestCase):
    def test_every_supported_threshold_below_capacity(self):
        for threshold in (2, 3, 4):
            with self.subTest(threshold=threshold):
                witness = lower_trace([2, 2], [2], threshold, 7)
                self.assertEqual(witness["capacity"], 4)
                self.assertTrue(verify_budget_transport(
                    witness, [2, 2], [2], threshold, [1, 2, 3, 4, 5, 6]
                ))

    def test_uncapped_capacity_may_exceed_pool(self):
        witness = lower_trace([2, 2, 2], [4, 4], 4, 7)
        self.assertEqual(witness["capacity"], 6)
        self.assertTrue(verify_budget_transport(
            witness, [2, 2, 2], [4, 4], 4, [1, 2, 3, 4]
        ))

    def test_explicit_pool_obeys_threshold_and_coordinate_cap(self):
        case = {"field": 29, "threshold": 4, "epochs": 1,
                "pins": [], "exposed": [[1]]}
        for pool in ([1, 2], list(range(1, 26))):
            with self.subTest(pool_size=len(pool)):
                self.assertFalse(verify_budget_trace(case, [1], [], 4, pool))

    def test_declared_budgets_fit_explicit_pool(self):
        case = {"field": 5, "threshold": 2, "epochs": 2,
                "pins": [[1]], "exposed": [[1], []]}
        for exposures, pins in (([3, 0], [1]), ([1, 0], [3])):
            with self.subTest(exposures=exposures, pins=pins):
                self.assertFalse(verify_budget_trace(case, exposures, pins, 2, [1, 2]))

    def test_expected_threshold_is_exact_and_integral(self):
        witness = lower_trace([2, 2], [2], 2, 7)
        for expected in (3, 2.0, True, None):
            with self.subTest(expected=expected):
                self.assertFalse(verify_budget_trace(
                    witness["case"], [2, 2], [2], expected, [1, 2, 3, 4, 5, 6]
                ))

    def test_capacity_metadata_remains_bound(self):
        witness = lower_trace([2, 2], [2], 4, 7)
        mutated = copy.deepcopy(witness)
        mutated["capacity"] += 1
        self.assertFalse(verify_budget_transport(
            mutated, [2, 2], [2], 4, [1, 2, 3, 4, 5, 6]
        ))


if __name__ == "__main__":
    unittest.main()
