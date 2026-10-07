"""Literal finite reference and complete current budget records; no timers."""
import copy
import itertools
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src import budgets as b
from src.budget_validation import check_budget_corpus


def literal_weight(exposures, pins, start, stop):
    return sum(exposures[i] for i in range(start, stop)) + (pins[start - 1] if start else 0) + (pins[stop - 1] if stop < len(exposures) else 0)


def partitions(exposures, pins):
    n = len(exposures)
    for size in range(n):
        for internal in itertools.combinations(range(1, n), size):
            cuts = [0, *internal, n]
            yield cuts, [literal_weight(exposures, pins, a, z) for a, z in zip(cuts, cuts[1:])]


def reference_schedule(fixture):
    exposures, pins, threshold, charges = [fixture[k] for k in ("exposures", "pins", "threshold", "charges")]
    n = len(exposures)
    allowed = fixture.get("allowed", [True] * (n - 1))
    mandatory = fixture.get("mandatory", [False] * (n - 1))
    best = None
    for size in range(n):
        for refreshes in itertools.combinations(range(1, n), size):
            if any(not allowed[x - 1] for x in refreshes):
                continue
            if any(flag and i + 1 not in refreshes for i, flag in enumerate(mandatory)):
                continue
            if fixture.get("max_refreshes") is not None and size > fixture["max_refreshes"]:
                continue
            effective = [pin if i + 1 in refreshes else fixture.get("pool_size", 24) for i, pin in enumerate(pins)]
            # All partitions of the effective instance; no production recurrence.
            if min(max(weights) for _, weights in partitions(exposures, effective)) >= threshold:
                continue
            value = (sum(charges[x - 1] for x in refreshes), size)
            best = value if best is None else min(best, value)
    return best


def fixtures():
    yield {"exposures": [2, 1], "pins": [2], "threshold": 4, "charges": [1], "allowed": [True], "mandatory": [True], "max_refreshes": 1, "pool_size": 5}
    for case in range(31):
        n = 1 + case % 4
        allowed = [(case + i) % 3 != 0 for i in range(n - 1)]
        mandatory = [v and (case + i) % 4 == 0 for i, v in enumerate(allowed)]
        yield {"exposures": [(case + 2 * i) % 3 for i in range(n)],
               "pins": [(case + i) % 3 for i in range(n - 1)], "threshold": 2 + case % 4,
               "charges": [(case + i) % 3 for i in range(n - 1)], "allowed": allowed,
               "mandatory": mandatory, "max_refreshes": case % n, "pool_size": 6}


def checked(fixture, tiny=True):
    exposures, pins = fixture["exposures"], fixture["pins"]
    partition = b.bottleneck_partition(exposures, pins)
    for a in range(len(exposures)):
        for z in range(a + 1, len(exposures) + 1):
            assert b.interval_cost(exposures, pins, a, z) == literal_weight(exposures, pins, a, z)
    assert partition["interval_costs"] == [literal_weight(exposures, pins, a, z) for a, z in zip(partition["cuts"], partition["cuts"][1:])]
    schedule = b.minimum_cost_schedule(**fixture)
    if tiny:
        assert partition["width"] == min(max(weights) for _, weights in partitions(exposures, pins))
        expected = reference_schedule(fixture)
        assert (schedule["kind"] == "impossible") == (expected is None)
        if expected is not None:
            assert (schedule["cost"], schedule["actual_refresh_count"]) == expected
    if schedule["kind"] == "schedule":
        assert schedule["interval_costs"] == [literal_weight(exposures, pins, a, z) for a, z in zip(schedule["cuts"], schedule["cuts"][1:])]
    return {"input": fixture, "partition": partition, "schedule": schedule}


def error_records():
    records = []
    for field, value in (("exposures", [True]), ("exposures", []), ("pins", [True]),
                         ("threshold", True), ("charges", [True]), ("allowed", [1]),
                         ("mandatory", [1]), ("max_refreshes", True), ("pool_size", True)):
        fixture = {"exposures": [2, 1], "pins": [2], "threshold": 4, "charges": [1], "pool_size": 5}
        fixture[field] = value
        try:
            b.minimum_cost_schedule(**fixture)
        except ValueError as error:
            records.append([field, value, type(error).__name__, str(error)])
        else:
            raise AssertionError("invalid fixture accepted")
    return records


def snapshot():
    corpus = json.loads((ROOT / "cases/budgets.json").read_text())
    retained = json.loads((ROOT / "results/pinned/budgets.json").read_text())
    budget = check_budget_corpus(corpus)
    assert budget == retained
    maximum = [checked({"exposures": [5] * 12, "pins": [pin] * 11,
                        "threshold": 12, "charges": [0] * 11}, tiny=False) for pin in (0, 24)]
    return {"tiny": [checked(f) for f in fixtures()], "maximum": maximum,
            "retained_budget": budget, "errors": error_records()}


class PrefixIntervalTests(unittest.TestCase):
    def test_literal_tiny_schedules_full_retained_records_and_maximum_shapes(self):
        value = snapshot()
        self.assertEqual((len(value["tiny"]), len(value["maximum"])), (32, 2))
        self.assertEqual(value["tiny"][0]["schedule"]["certificate_boundaries"], [])

    def test_prefix_prepared_once_only_after_validation(self):
        for function, args in ((b.bottleneck_partition, ([2, 1], [2])),
                               (b.minimum_cost_schedule, ([2, 1], [2], 4, [1]))):
            with patch.object(b, "_exposure_prefix", wraps=b._exposure_prefix) as prepared:
                with patch.object(b, "interval_cost", side_effect=AssertionError("unexpected repeated direct sum")):
                    function(*args)
                self.assertEqual(prepared.call_count, 1)
        with patch.object(b, "_exposure_prefix", side_effect=AssertionError("validation must precede preparation")):
            with self.assertRaises(ValueError):
                b.bottleneck_partition([True], [])
            with self.assertRaises(ValueError):
                b.minimum_cost_schedule([1], [], True, [])

    def test_bound_mutations_remain_rejected(self):
        corpus = json.loads((ROOT / "cases/budgets.json").read_text())
        for field in ("partition", "lower_witness"):
            bad = copy.deepcopy(corpus)
            if field == "partition":
                bad["variable_cases"][0][field]["width"] += 1
            else:
                bad["variable_cases"][0][field]["capacity"] += 1
            with self.assertRaises(AssertionError):
                check_budget_corpus(bad)


if __name__ == "__main__":
    unittest.main()
