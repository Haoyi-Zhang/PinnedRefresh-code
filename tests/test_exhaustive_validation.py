"""Fast contract tests for the independent bounded-oracle implementation."""
import unittest

from src.adaptive import exact_policy
from src.budgets import (
    capacities,
    constant_capacity,
    fixed_pin_capacity,
    largest_safe_constant_horizon,
    minimum_cost_schedule,
    threshold_envelope,
)
from src.exhaustive_validation import (
    _brute_partition_width,
    _brute_schedule,
    _pinned_reveals,
)


class ExhaustiveOracleContract(unittest.TestCase):
    def test_adaptive_assignment_count_has_no_unused_randomness(self):
        result = exact_policy()
        self.assertEqual(result["assignment_count"], 25)
        self.assertEqual(result["randomness_dimension"], 1)

    def test_independent_rank_hiding(self):
        self.assertFalse(_pinned_reveals(5, 3, [[1], [2], [3]], [[1], [1]]))

    def test_independent_rank_revealing(self):
        self.assertTrue(_pinned_reveals(5, 3, [[1], [2], [3]], [[1], [3]]))

    def test_unsafe_budget_can_contain_a_hiding_concrete_trace(self):
        self.assertEqual(capacities([1, 1], [1])["capacity"], 2)
        self.assertFalse(_pinned_reveals(5, 2, [[1], [1]], [[1]]))

    def test_brute_partition(self):
        self.assertEqual(_brute_partition_width([2, 2, 2, 2], [3, 3, 3]), 7)

    def test_brute_schedule_with_forbidden_boundary(self):
        self.assertIsNone(
            _brute_schedule([1, 1, 1], [0, 0], 3, [1, 1], [False, False])
        )

    def test_mandatory_refresh_need_not_be_a_certificate_cut(self):
        expected = _brute_schedule(
            [2, 1],
            [2],
            4,
            [1],
            [True],
            mandatory=[True],
            max_refreshes=1,
            pool_size=5,
        )
        result = minimum_cost_schedule(
            [2, 1],
            [2],
            4,
            [1],
            allowed=[True],
            mandatory=[True],
            max_refreshes=1,
            pool_size=5,
        )
        self.assertEqual(expected, (1, [1]))
        self.assertEqual(result["refresh_boundaries"], [1])
        self.assertEqual(result["certificate_boundaries"], [])
        self.assertEqual(result["capacity"]["capacity"], 3)
        self.assertEqual(result["actual_refresh_count"], 1)

    def test_refresh_limit_counts_actual_union(self):
        impossible = minimum_cost_schedule(
            [1, 1, 1],
            [0, 0],
            3,
            [1, 1],
            mandatory=[True, True],
            max_refreshes=1,
            pool_size=3,
        )
        self.assertEqual(impossible["kind"], "impossible")
        self.assertEqual(impossible["reason"], "mandatory_refresh_count_exceeds_limit")

    def test_threshold_envelope_keeps_zero_exposure_and_k_at_least_two(self):
        result = threshold_envelope([0, 0, 0], [2, 2], 5, 0)
        self.assertEqual(result["capacity"], 0)
        self.assertEqual(result["minimum_threshold"], 2)
        self.assertEqual(result["thresholds"], [2, 3, 4, 5])

    def test_threshold_envelope_can_be_empty(self):
        result = threshold_envelope([0], [], 1, 0)
        self.assertEqual(result["capacity"], 0)
        self.assertFalse(result["feasible"])
        self.assertEqual(result["thresholds"], [])

    def test_closed_form_helpers(self):
        self.assertEqual(constant_capacity(4, 2, 3), 7)
        self.assertEqual(fixed_pin_capacity([1, 3, 0, 2, 1], 2), 5)
        self.assertEqual(largest_safe_constant_horizon(2, 3, 8), 4)
        self.assertIsNone(largest_safe_constant_horizon(1, 1, 4))


if __name__ == "__main__":
    unittest.main()
