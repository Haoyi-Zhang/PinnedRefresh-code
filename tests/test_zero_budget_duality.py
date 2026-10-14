"""Literal partition checks at zero and asymmetric nonnegative budget boundaries."""
from itertools import product
import unittest

from src.budgets import capacities, bottleneck_partition, constant_capacity


def partition_width(exposures, pins, mask):
    n = len(exposures)
    cuts = [0] + [i + 1 for i in range(n - 1) if mask & (1 << i)] + [n]
    return max(sum(exposures[a:z]) + (pins[a-1] if a else 0)
               + (pins[z-1] if z < n else 0) for a, z in zip(cuts, cuts[1:]))


class ZeroBudgetDualityTests(unittest.TestCase):
    def test_all_small_asymmetric_sequences_including_zero(self):
        checked = 0
        for n in range(1, 5):
            for values in product(range(3), repeat=2*n-1):
                exposures, pins = list(values[:n]), list(values[n:])
                expected = min(partition_width(exposures, pins, mask)
                               for mask in range(1 << (n-1)))
                self.assertEqual(capacities(exposures, pins)['capacity'], expected)
                actual = bottleneck_partition(exposures, pins)
                self.assertEqual(actual['width'], expected)
                self.assertEqual(max(actual['interval_costs']), expected)
                checked += 1
        self.assertEqual(checked, 2460)

    def test_constant_formula_agrees_with_transport_at_zero_boundaries(self):
        for n, exposure, pin in product(range(1, 13), range(5), range(5)):
            self.assertEqual(constant_capacity(n, exposure, pin),
                             capacities([exposure]*n, [pin]*(n-1))['capacity'])


if __name__ == '__main__':
    unittest.main()
