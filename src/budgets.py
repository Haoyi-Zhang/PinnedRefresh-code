"""Exact public-budget frontier and offline robust refresh scheduling.

The shortest-path scheduler distinguishes the actual refresh set ``R`` from a
partition certificate's internal cut set ``Q``.  A safe schedule may contain
refreshes that the secrecy certificate does not use, so only ``Q subseteq R``
is required.  This distinction matters for mandatory operational refreshes.
No online prediction, deployed corruption rate, or malicious-party model is
used.
"""
from __future__ import annotations

from .model import integer
from .pinned import validate_pinned, multiply


def validate_budget(exposures: list[int], pins: list[int]) -> None:
    if (
        not isinstance(exposures, list)
        or not 1 <= len(exposures) <= 12
        or not isinstance(pins, list)
        or len(pins) != len(exposures) - 1
    ):
        raise ValueError("one exposure budget per slot and one pin budget per boundary required")
    if any(not integer(v) or not 0 <= v <= 24 for v in exposures + pins):
        raise ValueError("budgets must be integers between 0 and 24")
    if sum(exposures) > 64:
        raise ValueError("the sum of exposure budgets must not exceed 64")


def constant_capacity(epochs: int, exposure: int, pin: int) -> int:
    """Closed-form capacity for constant public budgets."""
    if not integer(epochs) or not 1 <= epochs <= 12:
        raise ValueError("epochs must be an integer between 1 and 12")
    if not integer(exposure) or not 0 <= exposure <= 24:
        raise ValueError("exposure must be an integer between 0 and 24")
    if not integer(pin) or not 0 <= pin <= 24:
        raise ValueError("pin must be an integer between 0 and 24")
    return min(
        epochs * exposure,
        ((epochs + 1) // 2) * exposure + pin,
        exposure + 2 * pin,
    )


def fixed_pin_capacity(exposures: list[int], pin: int) -> int:
    """Worst-case capacity when one fixed identity set is pinned throughout."""
    if not isinstance(exposures, list) or not exposures:
        raise ValueError("at least one exposure budget is required")
    if any(not integer(value) or not 0 <= value <= 24 for value in exposures):
        raise ValueError("exposures must be integers between 0 and 24")
    if not integer(pin) or not 0 <= pin <= 24:
        raise ValueError("pin must be an integer between 0 and 24")
    return min(sum(exposures), pin + max(exposures))


def largest_safe_constant_horizon(exposure: int, pin: int, threshold: int) -> int | None:
    """Return the largest positive safe horizon, or ``None`` if unbounded.

    Zero means that no positive horizon is safe.  The helper accepts the
    bounded artifact contract below.  The retained independent regression is
    deliberately narrower: ``b=1..4``, ``u=0..4``, and ``k=2..12`` (220
    tuples), as reported in the evidence ledger.
    """
    if not integer(exposure) or not 1 <= exposure <= 24:
        raise ValueError("positive exposure must be an integer at most 24")
    if not integer(pin) or not 0 <= pin <= 24:
        raise ValueError("pin must be an integer between 0 and 24")
    if not integer(threshold) or not 2 <= threshold <= 24:
        raise ValueError("threshold must be an integer between 2 and 24")
    if exposure + 2 * pin < threshold:
        return None
    horizon_one = (threshold - 1) // exposure
    horizon_two = 2 * max(0, (threshold - 1 - pin) // exposure)
    return max(horizon_one, horizon_two)


def capacities(exposures: list[int], pins: list[int]) -> dict:
    validate_budget(exposures, pins)
    epochs = len(exposures)
    left = [0] * epochs
    right = [0] * epochs
    for epoch in range(epochs - 1):
        left[epoch + 1] = min(pins[epoch], left[epoch] + exposures[epoch])
    for epoch in range(epochs - 2, -1, -1):
        right[epoch] = min(pins[epoch], right[epoch + 1] + exposures[epoch + 1])
    local = [a + b + c for a, b, c in zip(exposures, left, right)]
    maximum = max(local)
    return {
        "left": left,
        "right": right,
        "local": local,
        "capacity": maximum,
        "pivot": local.index(maximum),
    }


def threshold_envelope(
    exposures: list[int],
    pins: list[int],
    parties: int,
    recovery_unavailable: int,
) -> dict:
    """Return the legal integer thresholds under secrecy and recovery.

    The standing model requires a nontrivial threshold ``k >= 2``.  Therefore
    the lower endpoint is ``max(2, Gamma + 1)``; in particular, zero exposure
    does not recommend ``k=1``.
    """
    validate_budget(exposures, pins)
    if not integer(parties) or not 1 <= parties <= 24:
        raise ValueError("parties must be an integer between 1 and 24")
    if not integer(recovery_unavailable) or not 0 <= recovery_unavailable <= parties:
        raise ValueError("recovery_unavailable must be between 0 and parties")
    gamma = capacities(exposures, pins)["capacity"]
    lower = max(2, gamma + 1)
    upper = parties - recovery_unavailable
    legal = list(range(lower, upper + 1)) if lower <= upper else []
    return {
        "capacity": gamma,
        "minimum_threshold": lower,
        "maximum_threshold": upper,
        "thresholds": legal,
        "feasible": bool(legal),
    }


def interval_cost(exposures: list[int], pins: list[int], a: int, z: int) -> int:
    """Weight of half-open interval ``[a,z)`` in a partition certificate."""
    epochs = len(exposures)
    if not 0 <= a < z <= epochs:
        raise ValueError("empty or invalid interval")
    return (
        sum(exposures[a:z])
        + (pins[a - 1] if a else 0)
        + (pins[z - 1] if z < epochs else 0)
    )


def bottleneck_partition(exposures: list[int], pins: list[int]) -> dict:
    validate_budget(exposures, pins)
    epochs = len(exposures)
    value: list[int | None] = [None] * (epochs + 1)
    paths: list[list[int] | None] = [None] * (epochs + 1)
    value[0] = 0
    paths[0] = [0]
    for stop in range(1, epochs + 1):
        candidates = [
            (
                max(value[start], interval_cost(exposures, pins, start, stop)),
                paths[start] + [stop],
            )
            for start in range(stop)
            if value[start] is not None and paths[start] is not None
        ]
        value[stop], paths[stop] = min(candidates)
    assert value[epochs] is not None and paths[epochs] is not None
    return {
        "width": value[epochs],
        "cuts": paths[epochs],
        "interval_costs": [
            interval_cost(exposures, pins, start, stop)
            for start, stop in zip(paths[epochs], paths[epochs][1:])
        ],
    }


def _validate_schedule_constraints(
    exposures: list[int],
    pins: list[int],
    threshold: int,
    charges: list[int],
    allowed: list[bool] | None,
    mandatory: list[bool] | None,
    max_refreshes: int | None,
    pool_size: int,
) -> tuple[list[bool], list[bool], set[int]]:
    validate_budget(exposures, pins)
    epochs = len(exposures)
    if not integer(threshold) or not 2 <= threshold <= 12:
        raise ValueError("threshold must be between 2 and 12")
    if not integer(pool_size) or not threshold <= pool_size <= 24:
        raise ValueError("pool_size must be an integer between threshold and 24")
    if any(pin > pool_size for pin in pins):
        raise ValueError("a pin budget cannot exceed the coordinate-pool size")
    if (
        not isinstance(charges, list)
        or len(charges) != epochs - 1
        or any(not integer(charge) or charge < 0 for charge in charges)
    ):
        raise ValueError("nonnegative integer charges required")
    if allowed is None:
        allowed = [True] * (epochs - 1)
    if (
        not isinstance(allowed, list)
        or len(allowed) != epochs - 1
        or any(type(value) is not bool for value in allowed)
    ):
        raise ValueError("one boolean refresh-availability flag per boundary required")
    if mandatory is None:
        mandatory = [False] * (epochs - 1)
    if (
        not isinstance(mandatory, list)
        or len(mandatory) != epochs - 1
        or any(type(value) is not bool for value in mandatory)
    ):
        raise ValueError("one boolean mandatory-refresh flag per boundary required")
    if any(required and not permitted for required, permitted in zip(mandatory, allowed)):
        raise ValueError("a mandatory refresh boundary must also be allowed")
    if max_refreshes is not None and (
        not integer(max_refreshes) or not 0 <= max_refreshes <= epochs - 1
    ):
        raise ValueError("max_refreshes must be between zero and the number of boundaries")
    mandatory_set = {index + 1 for index, required in enumerate(mandatory) if required}
    return allowed, mandatory, mandatory_set


def minimum_cost_schedule(
    exposures: list[int],
    pins: list[int],
    threshold: int,
    charges: list[int],
    allowed: list[bool] | None = None,
    mandatory: list[bool] | None = None,
    max_refreshes: int | None = None,
    pool_size: int = 24,
) -> dict:
    """Return a minimum-cost safe actual refresh schedule.

    ``R`` is the actual refresh set.  ``Q`` is the internal cut set of a
    partition certificate and only needs to satisfy ``Q subseteq R``.  Every
    mandatory boundary belongs to ``R`` whether or not it belongs to ``Q``.
    Mandatory charges are an unavoidable prepaid constant; the path therefore
    charges only newly selected nonmandatory cuts.  A refresh-count limit is
    applied to ``|R| = |M union Q|``, not to ``|Q|``.
    """
    allowed, mandatory, mandatory_set = _validate_schedule_constraints(
        exposures,
        pins,
        threshold,
        charges,
        allowed,
        mandatory,
        max_refreshes,
        pool_size,
    )
    epochs = len(exposures)
    mandatory_cost = sum(charges[boundary - 1] for boundary in mandatory_set)

    if max_refreshes is not None and len(mandatory_set) > max_refreshes:
        return {
            "kind": "impossible",
            "reason": "mandatory_refresh_count_exceeds_limit",
            "mandatory_refresh_boundaries": sorted(mandatory_set),
            "max_refreshes": max_refreshes,
        }

    # states[z][r] = (additional nonmandatory cost, certificate cut path),
    # where r is the number of nonmandatory actual refreshes introduced by Q.
    states: list[dict[int, tuple[int, list[int]]]] = [dict() for _ in range(epochs + 1)]
    states[0][0] = (0, [0])
    maximum_added = (
        epochs - 1 - len(mandatory_set)
        if max_refreshes is None
        else max_refreshes - len(mandatory_set)
    )

    for stop in range(1, epochs + 1):
        if stop < epochs and not allowed[stop - 1]:
            continue
        add_count = int(stop < epochs and stop not in mandatory_set)
        add_cost = charges[stop - 1] if add_count else 0
        for start in range(stop):
            if interval_cost(exposures, pins, start, stop) >= threshold:
                continue
            for used, (cost, path) in states[start].items():
                next_used = used + add_count
                if next_used > maximum_added:
                    continue
                candidate = (cost + add_cost, path + [stop])
                incumbent = states[stop].get(next_used)
                if incumbent is None or candidate < incumbent:
                    states[stop][next_used] = candidate

    if not states[epochs]:
        maximal_refresh_set = {
            boundary
            for boundary in range(1, epochs)
            if allowed[boundary - 1]
        }
        effective = [
            pin if boundary in maximal_refresh_set else pool_size
            for boundary, pin in enumerate(pins, start=1)
        ]
        witness = capacities(exposures, effective)
        reason = (
            "refresh_limit"
            if max_refreshes is not None and witness["capacity"] < threshold
            else "no_safe_schedule"
        )
        result = {
            "kind": "impossible",
            "reason": reason,
            "mandatory_refresh_boundaries": sorted(mandatory_set),
            "max_refreshes": max_refreshes,
            "maximally_refreshed_boundaries": sorted(maximal_refresh_set),
            "effective_pin_budgets": effective,
        }
        if witness["capacity"] >= threshold:
            result["capacity_witness"] = witness
        return result

    additional_cost, _actual_count_key, certificate_path, used = min(
        (cost, len(mandatory_set) + used, path, used)
        for used, (cost, path) in states[epochs].items()
    )
    certificate_boundaries = set(certificate_path[1:-1])
    actual_refresh_set = mandatory_set | certificate_boundaries
    if max_refreshes is not None and len(actual_refresh_set) > max_refreshes:
        raise AssertionError("refresh-count state did not count the actual union")
    effective = [
        pin if boundary in actual_refresh_set else pool_size
        for boundary, pin in enumerate(pins, start=1)
    ]
    capacity = capacities(exposures, effective)
    if capacity["capacity"] >= threshold:
        raise AssertionError("partition certificate did not define a safe actual schedule")
    total_cost = sum(charges[boundary - 1] for boundary in actual_refresh_set)
    if total_cost != mandatory_cost + additional_cost:
        raise AssertionError("mandatory and additional schedule costs do not add up")
    return {
        "kind": "schedule",
        "cost": total_cost,
        "mandatory_cost": mandatory_cost,
        "added_cost": additional_cost,
        "cuts": certificate_path,
        "certificate_cuts": certificate_path,
        "certificate_boundaries": sorted(certificate_boundaries),
        "refresh_boundaries": sorted(actual_refresh_set),
        "mandatory_refresh_boundaries": sorted(mandatory_set),
        "actual_refresh_count": len(actual_refresh_set),
        "max_refreshes": max_refreshes,
        "interval_costs": [
            interval_cost(exposures, pins, start, stop)
            for start, stop in zip(certificate_path, certificate_path[1:])
        ],
        "effective_pin_budgets": effective,
        "capacity": capacity,
    }


def enumerate_partitions(
    exposures: list[int],
    pins: list[int],
    threshold: int,
    charges: list[int],
) -> list[dict]:
    """Enumerate interval partitions, not actual operational schedules."""
    validate_budget(exposures, pins)
    epochs = len(exposures)
    if epochs > 7:
        raise ValueError("exhaustive partition check is capped at six boundaries")
    result = []
    for mask in range(1 << (epochs - 1)):
        cuts = [0] + [epoch + 1 for epoch in range(epochs - 1) if mask >> epoch & 1] + [epochs]
        costs = [
            interval_cost(exposures, pins, start, stop)
            for start, stop in zip(cuts, cuts[1:])
        ]
        result.append(
            {
                "cuts": cuts,
                "width": max(costs),
                "safe": max(costs) < threshold,
                "cost": sum(charges[cut - 1] for cut in cuts[1:-1]),
            }
        )
    return result


# Compatibility name retained for callers that use this routine only for the
# partition duality.  Scheduling validation uses enumerate_actual_schedules.
enumerate_schedules = enumerate_partitions


def enumerate_actual_schedules(
    exposures: list[int],
    pins: list[int],
    threshold: int,
    charges: list[int],
    allowed: list[bool] | None = None,
    mandatory: list[bool] | None = None,
    max_refreshes: int | None = None,
    pool_size: int = 24,
) -> list[dict]:
    """Exhaust actual refresh subsets and test ``Gamma(b,u^R) < k`` directly."""
    allowed, mandatory, mandatory_set = _validate_schedule_constraints(
        exposures,
        pins,
        threshold,
        charges,
        allowed,
        mandatory,
        max_refreshes,
        pool_size,
    )
    epochs = len(exposures)
    if epochs > 7:
        raise ValueError("exhaustive schedule check is capped at six boundaries")
    optional = [
        boundary
        for boundary in range(1, epochs)
        if allowed[boundary - 1] and boundary not in mandatory_set
    ]
    result = []
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
        capacity = capacities(exposures, effective)
        result.append(
            {
                "refresh_boundaries": sorted(refreshes),
                "actual_refresh_count": len(refreshes),
                "cost": sum(charges[boundary - 1] for boundary in refreshes),
                "effective_pin_budgets": effective,
                "capacity": capacity,
                "safe": capacity["capacity"] < threshold,
            }
        )
    return result


def lower_trace(exposures: list[int], pins: list[int], threshold: int, field: int = 29) -> dict:
    """Concrete share-capture witness for any ``k <= Gamma``."""
    witness = capacities(exposures, pins)
    epochs = len(exposures)
    pivot = witness["pivot"]
    k = threshold
    if not integer(k) or not 2 <= k <= min(12, field - 1) or k > witness["capacity"]:
        raise ValueError("no supported lower-bound witness at this threshold")
    at = min(exposures[pivot], k)
    before = min(witness["left"][pivot], k - at)
    after = k - at - before
    if after > witness["right"][pivot]:
        raise AssertionError("capacity split failed")
    left_labels = list(range(1, before + 1))
    center_labels = list(range(before + 1, before + at + 1))
    right_labels = list(range(before + at + 1, k + 1))
    actual_exposed = [[] for _ in range(epochs)]
    actual_pins = [[] for _ in range(epochs - 1)]
    actual_exposed[pivot] = center_labels
    needed = left_labels[:]
    for epoch in range(pivot - 1, -1, -1):
        actual_pins[epoch] = needed[:]
        take = min(exposures[epoch], len(needed))
        actual_exposed[epoch] = needed[:take]
        needed = needed[take:]
    if needed:
        raise AssertionError("left transport failed")
    needed = right_labels[:]
    for epoch in range(pivot + 1, epochs):
        actual_pins[epoch - 1] = needed[:]
        take = min(exposures[epoch], len(needed))
        actual_exposed[epoch] = needed[:take]
        needed = needed[take:]
    if needed:
        raise AssertionError("right transport failed")
    case = {
        "field": field,
        "threshold": k,
        "epochs": epochs,
        "pins": actual_pins,
        "exposed": actual_exposed,
    }
    validate_pinned(case)
    if any(len(values) > budget for values, budget in zip(actual_exposed, exposures)) or any(
        len(values) > budget for values, budget in zip(actual_pins, pins)
    ):
        raise AssertionError("budget violation")
    sources = [
        {"x": x, "epoch": epoch}
        for epoch, coordinates in enumerate(actual_exposed)
        for x in coordinates
    ]
    weights = []
    for row in sources:
        x = row["x"]
        weight = 1
        for other in sources:
            y = other["x"]
            if y != x:
                weight = weight * (-y) * pow(x - y, -1, field) % field
        weights.append(weight)
    return {
        "case": case,
        "pivot": pivot,
        "sources": sources,
        "interpolation_weights": weights,
        "capacity": witness["capacity"],
    }


def verify_transport(record: dict) -> bool:
    """Check one algebraic trace witness, deliberately without public budgets.

    This trace-level helper verifies equality paths and interpolation only.  It
    must not be used as a substitute for :func:`verify_budget_transport`, which
    binds the witness to the claimed exposure/pin budgets and coordinate pool.
    """
    try:
        case = record["case"]
        validate_pinned(case)
        q = case["field"]
        k = case["threshold"]
        pivot = record["pivot"]
        if not integer(pivot) or not 0 <= pivot < case["epochs"]:
            return False
        sources = record["sources"]
        weights = record["interpolation_weights"]
        if len(sources) != k or len(weights) != k or len({source["x"] for source in sources}) != k:
            return False
        for source in sources:
            x, epoch = source["x"], source["epoch"]
            if not integer(epoch) or not 0 <= epoch < case["epochs"] or x not in case["exposed"][epoch]:
                return False
            if any(
                x not in case["pins"][boundary]
                for boundary in range(min(pivot, epoch), max(pivot, epoch))
            ):
                return False
        if any(not integer(weight) or not 0 <= weight < q for weight in weights):
            return False
        return all(
            sum(
                weight * pow(source["x"], degree, q)
                for source, weight in zip(sources, weights)
            )
            % q
            == int(degree == 0)
            for degree in range(k)
        )
    except (KeyError, TypeError, ValueError):
        return False


def verify_budget_trace(
    case: dict,
    exposures: list[int],
    pins: list[int],
    expected_threshold: int,
    coordinate_pool: list[int],
) -> bool:
    """Bind one concrete pinned trace to public budgets and a coordinate pool."""
    try:
        validate_budget(exposures, pins)
        validate_pinned(case)
        if (
            not integer(expected_threshold)
            or case["epochs"] != len(exposures)
            or case["threshold"] != expected_threshold
        ):
            return False
        q = case["field"]
        if (
            not isinstance(coordinate_pool, list)
            or not expected_threshold <= len(coordinate_pool) <= 24
            or len(coordinate_pool) != len(set(coordinate_pool))
            or any(not integer(x) or not 1 <= x < q for x in coordinate_pool)
        ):
            return False
        pool = set(coordinate_pool)
        if any(budget > len(pool) for budget in exposures + pins):
            return False
        if any(len(values) > budget for values, budget in zip(case["exposed"], exposures)):
            return False
        if any(len(values) > budget for values, budget in zip(case["pins"], pins)):
            return False
        if any(x not in pool for values in case["exposed"] + case["pins"] for x in values):
            return False
        return True
    except (KeyError, TypeError, ValueError):
        return False


def verify_budget_transport(
    record: dict,
    exposures: list[int],
    pins: list[int],
    expected_threshold: int,
    coordinate_pool: list[int],
) -> bool:
    """Bind a transport to ``b``, ``u``, ``Gamma``, ``k`` and ``X`` for any k <= Gamma.

    Capacity is uncapped and can exceed the coordinate-pool size; the actual
    threshold and the witness's distinct labels must still fit that pool.
    """
    try:
        gamma = capacities(exposures, pins)["capacity"]
        if (
            not integer(expected_threshold)
            or expected_threshold > gamma
            or not integer(record.get("capacity"))
            or record.get("capacity") != gamma
        ):
            return False
        if not verify_budget_trace(
            record["case"], exposures, pins, expected_threshold, coordinate_pool
        ):
            return False
        return verify_transport(record)
    except (KeyError, TypeError, ValueError):
        return False


def root_certificate(case: dict, cuts: list[int]) -> dict:
    validate_pinned(case)
    q = case["field"]
    k = case["threshold"]
    epochs = case["epochs"]
    if (
        not isinstance(cuts, list)
        or len(cuts) < 2
        or cuts[0] != 0
        or cuts[-1] != epochs
        or any(not integer(cut) for cut in cuts)
        or any(start >= stop for start, stop in zip(cuts, cuts[1:]))
    ):
        raise ValueError("invalid partition")
    polynomials = [None] * epochs
    for start, stop in zip(cuts, cuts[1:]):
        roots = set().union(*(set(values) for values in case["exposed"][start:stop]))
        if start:
            roots.update(case["pins"][start - 1])
        if stop < epochs:
            roots.update(case["pins"][stop - 1])
        if len(roots) >= k:
            raise ValueError("root certificate would exceed degree bound")
        polynomial = [1]
        for x in sorted(roots):
            polynomial = multiply(polynomial, [1, -pow(x, -1, q) % q], q)
        polynomial += [0] * (k - len(polynomial))
        for epoch in range(start, stop):
            polynomials[epoch] = polynomial[:]
    return {"kind": "hiding", "polynomials": polynomials}
