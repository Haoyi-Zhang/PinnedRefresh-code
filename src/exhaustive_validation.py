"""Independent bounded oracles for the public-budget theorem and scheduler.

This module deliberately does not import certificate producers/checkers or the
pinned-trace encoder.  It uses local modular rank, a local capacity recurrence,
brute-force interval partitions, and brute-force *actual refresh subsets*.
The checks are finite regression evidence, not a proof of general quantifiers.
"""
from __future__ import annotations

from itertools import product
from typing import Iterable

from .budgets import (
    capacities,
    constant_capacity,
    fixed_pin_capacity,
    largest_safe_constant_horizon,
    minimum_cost_schedule,
    threshold_envelope,
)


def _rank_mod(rows: Iterable[Iterable[int]], q: int) -> int:
    """Return row rank over the prime field F_q using local elimination code."""
    matrix = [[value % q for value in row] for row in rows]
    if not matrix:
        return 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("ragged rank matrix")
    top = 0
    for col in range(width):
        pivot = next((i for i in range(top, len(matrix)) if matrix[i][col]), None)
        if pivot is None:
            continue
        matrix[top], matrix[pivot] = matrix[pivot], matrix[top]
        inverse = pow(matrix[top][col], -1, q)
        matrix[top] = [(value * inverse) % q for value in matrix[top]]
        for i in range(top + 1, len(matrix)):
            factor = matrix[i][col]
            if factor:
                matrix[i] = [
                    (left - factor * right) % q
                    for left, right in zip(matrix[i], matrix[top])
                ]
        top += 1
        if top == len(matrix):
            break
    return top


def _pinned_reveals(
    q: int,
    k: int,
    exposed: list[list[int]],
    pins: list[list[int]],
) -> bool:
    """Independent rank test for whether this concrete trace determines S."""
    epochs = len(exposed)
    width = 1 + epochs * (k - 1)
    rows: list[list[int]] = []

    for epoch, coordinates in enumerate(pins):
        for x in coordinates:
            row = [0] * width
            for degree in range(1, k):
                power = pow(x, degree, q)
                row[1 + epoch * (k - 1) + degree - 1] = (-power) % q
                row[1 + (epoch + 1) * (k - 1) + degree - 1] = power
            rows.append(row)

    for epoch, coordinates in enumerate(exposed):
        for x in coordinates:
            row = [0] * width
            row[0] = 1
            for degree in range(1, k):
                row[1 + epoch * (k - 1) + degree - 1] = pow(x, degree, q)
            rows.append(row)

    secret = [1] + [0] * (width - 1)
    return _rank_mod(rows, q) == _rank_mod(rows + [secret], q)


def _all_subsets(n: int) -> list[list[int]]:
    return [
        [coordinate + 1 for coordinate in range(n) if mask >> coordinate & 1]
        for mask in range(1 << n)
    ]


def _flatten_index(values: tuple[int, ...], base: int) -> int:
    result = 0
    for value in values:
        result = result * base + value
    return result


def _prefix_or(table: bytearray, base: int, dimensions: int) -> None:
    """Convert exact-size flags into component-wise dominated-existence flags."""
    stride = 1
    for _dimension in range(dimensions - 1, -1, -1):
        block = stride * base
        for start in range(0, len(table), block):
            for offset in range(stride):
                for value in range(1, base):
                    index = start + value * stride + offset
                    table[index] |= table[index - stride]
        stride *= base


def _exhaustive_universal_case(n: int, k: int, epochs: int, q: int) -> dict:
    """Rank every trace, then prefix-OR to test an existential budget theorem."""
    subsets = _all_subsets(n)
    dimensions = 2 * epochs - 1
    base = n + 1
    revealing_exists = bytearray(base**dimensions)
    concrete_count = 0
    revealing_count = 0

    for parts in product(subsets, repeat=dimensions):
        exposed = [list(parts[i]) for i in range(epochs)]
        pins = [list(parts[epochs + i]) for i in range(epochs - 1)]
        concrete_count += 1
        if _pinned_reveals(q, k, exposed, pins):
            revealing_count += 1
            sizes = tuple(map(len, exposed + pins))
            revealing_exists[_flatten_index(sizes, base)] = 1

    # After prefix OR, entry v means: there exists at least one revealing
    # concrete trace whose component-wise sizes are at most budget vector v.
    _prefix_or(revealing_exists, base, dimensions)

    budget_count = 0
    for values in product(range(base), repeat=dimensions):
        exposures = list(values[:epochs])
        pin_budgets = list(values[epochs:])
        predicted_exists = capacities(exposures, pin_budgets)["capacity"] >= k
        observed_exists = bool(revealing_exists[_flatten_index(values, base)])
        if observed_exists != predicted_exists:
            raise AssertionError(
                "universal frontier mismatch: "
                f"n={n}, k={k}, T={epochs}, b={exposures}, u={pin_budgets}"
            )
        budget_count += 1

    return {
        "parties": n,
        "threshold": k,
        "epochs": epochs,
        "field": q,
        "concrete_set_systems": concrete_count,
        "revealing_set_systems": revealing_count,
        "budget_vectors": budget_count,
        "budget_quantifier": (
            "a revealing concrete trace exists within the component-wise budget "
            "if and only if Gamma is at least the threshold"
        ),
    }


def _exhaustive_fixed_pin_case(n: int, k: int, epochs: int, q: int) -> dict:
    """Independent rank oracle with one identical actual pin set at all boundaries."""
    subsets = _all_subsets(n)
    dimensions = epochs + 1  # exposure sizes followed by the fixed-set size
    base = n + 1
    revealing_exists = bytearray(base**dimensions)
    concrete_count = 0
    revealing_count = 0

    for fixed in subsets:
        pins = [list(fixed) for _ in range(epochs - 1)]
        for exposed_parts in product(subsets, repeat=epochs):
            exposed = [list(values) for values in exposed_parts]
            concrete_count += 1
            if _pinned_reveals(q, k, exposed, pins):
                revealing_count += 1
                sizes = tuple([len(values) for values in exposed] + [len(fixed)])
                revealing_exists[_flatten_index(sizes, base)] = 1

    _prefix_or(revealing_exists, base, dimensions)
    budget_count = 0
    for values in product(range(base), repeat=dimensions):
        exposures = list(values[:epochs])
        pin_budget = values[-1]
        predicted_exists = fixed_pin_capacity(exposures, pin_budget) >= k
        observed_exists = bool(revealing_exists[_flatten_index(values, base)])
        if observed_exists != predicted_exists:
            raise AssertionError(
                "fixed-pin rank frontier mismatch: "
                f"n={n}, k={k}, T={epochs}, b={exposures}, u={pin_budget}"
            )
        budget_count += 1

    return {
        "parties": n,
        "threshold": k,
        "epochs": epochs,
        "field": q,
        "concrete_fixed_pin_systems": concrete_count,
        "revealing_fixed_pin_systems": revealing_count,
        "fixed_pin_budget_vectors": budget_count,
    }


def _interval_weight(exposures: list[int], pins: list[int], start: int, stop: int) -> int:
    value = sum(exposures[start:stop])
    if start:
        value += pins[start - 1]
    if stop < len(exposures):
        value += pins[stop - 1]
    return value


def _brute_partition_width(exposures: list[int], pins: list[int]) -> int:
    epochs = len(exposures)
    best: int | None = None
    for mask in range(1 << (epochs - 1)):
        cuts = [0] + [e + 1 for e in range(epochs - 1) if mask >> e & 1] + [epochs]
        width = max(
            _interval_weight(exposures, pins, start, stop)
            for start, stop in zip(cuts, cuts[1:])
        )
        if best is None or width < best:
            best = width
    assert best is not None
    return best


def _direct_capacity(exposures: list[int], pins: list[int]) -> int:
    """Local recurrence used by actual-subset scheduler validation."""
    epochs = len(exposures)
    left = [0] * epochs
    right = [0] * epochs
    for epoch in range(epochs - 1):
        left[epoch + 1] = min(pins[epoch], left[epoch] + exposures[epoch])
    for epoch in range(epochs - 2, -1, -1):
        right[epoch] = min(pins[epoch], right[epoch + 1] + exposures[epoch + 1])
    return max(
        exposures[epoch] + left[epoch] + right[epoch]
        for epoch in range(epochs)
    )


def _check_duality(max_epochs: int = 4, maximum_budget: int = 2) -> int:
    checked = 0
    for epochs in range(1, max_epochs + 1):
        for values in product(range(maximum_budget + 1), repeat=2 * epochs - 1):
            exposures = list(values[:epochs])
            pins = list(values[epochs:])
            recurrence = capacities(exposures, pins)["capacity"]
            brute = _brute_partition_width(exposures, pins)
            if recurrence != brute:
                raise AssertionError(
                    f"capacity/partition mismatch: b={exposures}, u={pins}, "
                    f"recurrence={recurrence}, brute={brute}"
                )
            checked += 1
    return checked


def _brute_schedule(
    exposures: list[int],
    pins: list[int],
    threshold: int,
    charges: list[int],
    allowed: list[bool],
    mandatory: list[bool] | None = None,
    max_refreshes: int | None = None,
    pool_size: int = 24,
) -> tuple[int, list[int]] | None:
    """Enumerate actual R and test Gamma(b,u^R), never an exact-cut surrogate."""
    epochs = len(exposures)
    mandatory = mandatory or [False] * (epochs - 1)
    mandatory_set = {i + 1 for i, flag in enumerate(mandatory) if flag}
    if any(boundary not in {i + 1 for i, flag in enumerate(allowed) if flag} for boundary in mandatory_set):
        raise ValueError("mandatory boundary is not allowed")
    optional = [
        boundary
        for boundary in range(1, epochs)
        if allowed[boundary - 1] and boundary not in mandatory_set
    ]
    best: tuple[int, int, list[int]] | None = None
    for mask in range(1 << len(optional)):
        refreshes = mandatory_set | {
            boundary for index, boundary in enumerate(optional) if mask >> index & 1
        }
        if max_refreshes is not None and len(refreshes) > max_refreshes:
            continue
        effective = [
            pin if boundary in refreshes else pool_size
            for boundary, pin in enumerate(pins, start=1)
        ]
        if _direct_capacity(exposures, effective) >= threshold:
            continue
        candidate = (
            sum(charges[boundary - 1] for boundary in refreshes),
            len(refreshes),
            sorted(refreshes),
        )
        if best is None or candidate < best:
            best = candidate
    return None if best is None else (best[0], best[2])


def _check_scheduler() -> int:
    checked = 0
    for epochs in range(1, 7):
        dimensions = 2 * epochs - 1
        tuple_count = 3**dimensions
        stride = max(1, tuple_count // 150)
        for index, values in enumerate(product(range(3), repeat=dimensions)):
            if index % stride:
                continue
            exposures = list(values[:epochs])
            pins = list(values[epochs:])
            if not any(exposures):
                continue
            charges = [(3 * i + sum(values)) % 5 for i in range(epochs - 1)]
            allowed = [((i + sum(values)) % 3) != 0 for i in range(epochs - 1)]
            for threshold in range(2, 5):
                expected = _brute_schedule(
                    exposures, pins, threshold, charges, allowed
                )
                actual = minimum_cost_schedule(
                    exposures,
                    pins,
                    threshold,
                    charges,
                    allowed=allowed,
                    pool_size=24,
                )
                if expected is None:
                    if actual["kind"] != "impossible":
                        raise AssertionError("scheduler accepted a brute-force impossible case")
                elif actual["kind"] != "schedule" or (
                    actual["cost"], actual["refresh_boundaries"]
                ) != expected:
                    raise AssertionError(
                        "actual-subset scheduler optimum mismatch: "
                        f"b={exposures}, u={pins}, k={threshold}, charges={charges}, "
                        f"allowed={allowed}, actual={actual}, expected={expected}"
                    )
                checked += 1
    return checked


def _check_mandatory_scheduler() -> tuple[int, dict]:
    # The explicit regression from the manuscript: R={1} is mandatory and safe,
    # while forcing Q={1} would give interval weights 4 and 3 and reject it.
    counterexample = minimum_cost_schedule(
        [2, 1],
        [2],
        4,
        [1],
        allowed=[True],
        mandatory=[True],
        max_refreshes=1,
        pool_size=5,
    )
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
    if (
        expected != (1, [1])
        or counterexample["kind"] != "schedule"
        or (counterexample["cost"], counterexample["refresh_boundaries"]) != expected
        or counterexample["certificate_boundaries"] != []
        or counterexample["capacity"]["capacity"] != 3
    ):
        raise AssertionError("mandatory refresh regression failed")

    checked = 1
    for epochs in range(2, 6):
        dimensions = 2 * epochs - 1
        tuple_count = 2**dimensions
        stride = max(1, tuple_count // 60)
        for index, values in enumerate(product(range(2), repeat=dimensions)):
            if index % stride:
                continue
            exposures = list(values[:epochs])
            pins = list(values[epochs:])
            charges = [(index + 2 * boundary) % 4 for boundary in range(epochs - 1)]
            allowed = [((index + boundary) % 4) != 0 for boundary in range(epochs - 1)]
            mandatory = [
                allowed[boundary] and ((index + 2 * boundary) % 5 == 0)
                for boundary in range(epochs - 1)
            ]
            mandatory_count = sum(mandatory)
            cap = min(epochs - 1, mandatory_count + (index % 3))
            for threshold in range(2, 5):
                expected = _brute_schedule(
                    exposures,
                    pins,
                    threshold,
                    charges,
                    allowed,
                    mandatory=mandatory,
                    max_refreshes=cap,
                    pool_size=4,
                )
                actual = minimum_cost_schedule(
                    exposures,
                    pins,
                    threshold,
                    charges,
                    allowed=allowed,
                    mandatory=mandatory,
                    max_refreshes=cap,
                    pool_size=4,
                )
                if expected is None:
                    if actual["kind"] != "impossible":
                        raise AssertionError("mandatory/count scheduler accepted an impossible case")
                elif actual["kind"] != "schedule" or (
                    actual["cost"], actual["refresh_boundaries"]
                ) != expected:
                    raise AssertionError(
                        "mandatory/count actual-subset mismatch: "
                        f"b={exposures}, u={pins}, k={threshold}, allowed={allowed}, "
                        f"mandatory={mandatory}, cap={cap}, actual={actual}, expected={expected}"
                    )
                if actual["kind"] == "schedule" and actual["actual_refresh_count"] > cap:
                    raise AssertionError("refresh limit counted certificate cuts instead of actual R")
                checked += 1
    return checked, counterexample


def _threshold_envelope_regressions() -> list[dict]:
    cases = [
        ([0, 0, 0], [2, 2], 5, 0),
        ([0], [], 1, 0),
        ([1, 1], [1], 3, 1),
        ([2, 1], [2], 5, 1),
    ]
    results = []
    for exposures, pins, parties, unavailable in cases:
        result = threshold_envelope(exposures, pins, parties, unavailable)
        if result["thresholds"] and min(result["thresholds"]) < 2:
            raise AssertionError("threshold envelope recommended k=1")
        if exposures == [0, 0, 0] and result["minimum_threshold"] != 2:
            raise AssertionError("zero-exposure lower threshold must be two")
        results.append(
            {
                "exposures": exposures,
                "pins": pins,
                "parties": parties,
                "recovery_unavailable": unavailable,
                "result": result,
            }
        )
    return results


def run_exhaustive_validation() -> dict:
    universal = [
        _exhaustive_universal_case(2, 2, 4, 5),
        _exhaustive_universal_case(3, 2, 2, 5),
        _exhaustive_universal_case(3, 3, 2, 5),
        _exhaustive_universal_case(4, 3, 2, 5),
        _exhaustive_universal_case(4, 4, 2, 5),
    ]

    # Lightweight regression for the trace/budget quantifier distinction.
    separation = {
        "field": 5,
        "parties": 3,
        "threshold": 2,
        "epochs": 2,
        "exposed": [[1], [1]],
        "pins": [[1]],
        "budget_capacity": capacities([1, 1], [1])["capacity"],
        "concrete_trace_reveals": _pinned_reveals(5, 2, [[1], [1]], [[1]]),
        "hiding_path": [[1, 4], [1, 4]],
    }
    if separation["budget_capacity"] != 2 or separation["concrete_trace_reveals"]:
        raise AssertionError("single-trace/budget separation regression failed")

    fixed_rank = [
        _exhaustive_fixed_pin_case(3, 2, 2, 5),
        _exhaustive_fixed_pin_case(3, 3, 2, 5),
        _exhaustive_fixed_pin_case(4, 3, 2, 5),
    ]

    closed_form_checks = 0
    for epochs in range(1, 13):
        for exposure in range(5):
            for pin in range(5):
                expected = capacities(
                    [exposure] * epochs, [pin] * (epochs - 1)
                )["capacity"]
                if constant_capacity(epochs, exposure, pin) != expected:
                    raise AssertionError("constant-capacity closed form mismatch")
                closed_form_checks += 1

    # This loop checks only that the helper implements the displayed formula;
    # the independent rank oracle above supplies the separate secrecy check.
    fixed_pin_formula_checks = 0
    for epochs in range(1, 6):
        for exposures in product(range(4), repeat=epochs):
            for pin in range(5):
                expected = min(sum(exposures), pin + max(exposures))
                if fixed_pin_capacity(list(exposures), pin) != expected:
                    raise AssertionError("fixed-pin formula implementation mismatch")
                fixed_pin_formula_checks += 1

    horizon_checks = 0
    for exposure in range(1, 5):
        for pin in range(5):
            for threshold in range(2, 13):
                claimed = largest_safe_constant_horizon(exposure, pin, threshold)
                safe = [
                    epochs
                    for epochs in range(1, 13)
                    if constant_capacity(epochs, exposure, pin) < threshold
                ]
                if claimed is None:
                    if len(safe) != 12:
                        raise AssertionError("unbounded-horizon formula mismatch")
                else:
                    observed = max(safe, default=0)
                    if min(claimed, 12) != observed:
                        raise AssertionError("largest-safe-horizon formula mismatch")
                horizon_checks += 1

    mandatory_checks, mandatory_counterexample = _check_mandatory_scheduler()
    threshold_regressions = _threshold_envelope_regressions()

    return {
        "method": (
            "local modular rank over concrete set systems; prefix OR for the "
            "existential budget quantifier; brute-force interval partitions; "
            "brute-force actual refresh subsets evaluated by a local Gamma recurrence"
        ),
        "capacity_partition_vectors": _check_duality(),
        "universal_frontier_families": universal,
        "concrete_set_systems": sum(row["concrete_set_systems"] for row in universal),
        "revealing_set_systems": sum(row["revealing_set_systems"] for row in universal),
        "dominating_budget_vectors": sum(row["budget_vectors"] for row in universal),
        "single_trace_budget_separation": separation,
        "scheduler_instances": _check_scheduler(),
        "mandatory_and_count_scheduler_instances": mandatory_checks,
        "mandatory_counterexample": mandatory_counterexample,
        "constant_closed_form_checks": closed_form_checks,
        "fixed_pin_formula_consistency_checks": fixed_pin_formula_checks,
        "fixed_pin_rank_oracle_families": fixed_rank,
        "fixed_pin_rank_concrete_systems": sum(
            row["concrete_fixed_pin_systems"] for row in fixed_rank
        ),
        "fixed_pin_rank_revealing_systems": sum(
            row["revealing_fixed_pin_systems"] for row in fixed_rank
        ),
        "fixed_pin_rank_budget_vectors": sum(
            row["fixed_pin_budget_vectors"] for row in fixed_rank
        ),
        "horizon_inversion_checks": horizon_checks,
        "horizon_checked_domain": {
            "exposure": "1..4",
            "pin": "0..4",
            "threshold": "2..12",
            "bounded_scan_horizon": "1..12",
        },
        "threshold_envelope_regressions": threshold_regressions,
    }
