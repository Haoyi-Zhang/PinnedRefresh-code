"""Bounded exact comparisons for capacity, certificates, and scheduling."""
from __future__ import annotations

import copy
import random

from .budgets import (
    bottleneck_partition,
    capacities,
    enumerate_actual_schedules,
    enumerate_partitions,
    interval_cost,
    lower_trace,
    minimum_cost_schedule,
    root_certificate,
    verify_budget_trace,
    verify_budget_transport,
    verify_transport,
)
from .pinned_checker import verify_pinned
from .pinned_producer import produce_pinned


def _budget_binding_negative_controls(case: dict, coordinate_pool: list[int]) -> int:
    """Reject over-budget pin/exposure and wrong-threshold witness mutations."""
    exposures = case["exposures"]
    pins = case["pins"]
    gamma = capacities(exposures, pins)["capacity"]
    original = case["lower_witness"]
    if not verify_budget_transport(original, exposures, pins, gamma, coordinate_pool):
        raise AssertionError("original budget-bound transport witness rejected")

    controls = []

    # Preserve the algebraic path while exceeding u_0 by one coordinate.
    over_pin = copy.deepcopy(original)
    spare = next(x for x in coordinate_pool if x not in over_pin["case"]["pins"][0])
    over_pin["case"]["pins"][0].append(spare)
    over_pin["case"]["pins"][0].sort()
    if not verify_transport(over_pin):
        raise AssertionError("pin-budget control no longer isolates the budget layer")
    controls.append(over_pin)

    # Add an unused exposure in a zero-budget slot.  The interpolation path is
    # unchanged, so only the instance-level budget check should reject it.
    over_exposure = copy.deepcopy(original)
    zero_slot = next(index for index, budget in enumerate(exposures) if budget == 0)
    spare = next(x for x in coordinate_pool if x not in over_exposure["case"]["exposed"][zero_slot])
    over_exposure["case"]["exposed"][zero_slot].append(spare)
    over_exposure["case"]["exposed"][zero_slot].sort()
    if not verify_transport(over_exposure):
        raise AssertionError("exposure-budget control no longer isolates the budget layer")
    controls.append(over_exposure)

    wrong_threshold = copy.deepcopy(original)
    wrong_threshold["case"]["threshold"] = gamma + 1
    controls.append(wrong_threshold)

    for mutated in controls:
        if verify_budget_transport(mutated, exposures, pins, gamma, coordinate_pool):
            raise AssertionError("budget-level verifier accepted a controlled invalid witness")
    return len(controls)


def check_budget_corpus(corpus: dict) -> dict:
    coordinate_pool = corpus.get("coordinate_pool")
    if not isinstance(coordinate_pool, list) or not coordinate_pool:
        raise ValueError("budget corpus requires an explicit coordinate_pool")

    mathematical = []
    partition_visits = 0
    certificates = 0
    transport_checks = 0
    case_records = []

    for case in corpus["mathematical_cases"]:
        exposures, pins = case["exposures"], case["pins"]
        capacity = capacities(exposures, pins)
        partition = bottleneck_partition(exposures, pins)
        enumerated = enumerate_partitions(exposures, pins, 2, [1] * len(pins))
        partition_visits += len(enumerated)
        exact = min(row["width"] for row in enumerated)
        if not capacity["capacity"] == partition["width"] == exact:
            raise AssertionError("capacity/partition duality failed")
        mathematical.append(
            {
                "exposures": exposures,
                "pins": pins,
                "capacity": capacity,
                "partition": partition,
                "exhaustive_partitions": enumerated,
            }
        )

    for case in corpus["variable_cases"]:
        exposures, pins = case["exposures"], case["pins"]
        capacity = capacities(exposures, pins)
        gamma = capacity["capacity"]
        partition = bottleneck_partition(exposures, pins)
        if capacity["capacity"] != partition["width"] or partition != case["partition"]:
            raise AssertionError("variable partition mismatch")

        upper = case["upper_case"]
        upper_threshold = max(2, gamma + 1)
        if not verify_budget_trace(
            upper, exposures, pins, upper_threshold, coordinate_pool
        ):
            raise AssertionError("upper trace is not bound to its public instance")
        root = root_certificate(upper, partition["cuts"])
        produced_upper = produce_pinned(upper)
        if (
            produced_upper["kind"] != "hiding"
            or not verify_pinned(upper, root)
            or not verify_pinned(upper, produced_upper)
        ):
            raise AssertionError("upper-bound certificate failed")
        certificates += 2

        lower = case["lower_witness"]
        lower_case = lower["case"]
        produced_lower = produce_pinned(lower_case)
        if (
            not verify_budget_transport(
                lower, exposures, pins, gamma, coordinate_pool
            )
            or produced_lower["kind"] != "revealing"
            or not verify_pinned(lower_case, produced_lower)
        ):
            raise AssertionError("matching budget-bound lower witness failed")
        certificates += 1
        transport_checks += 1
        case_records.append(
            {
                "id": case["id"],
                "capacity": capacity,
                "partition": partition,
                "upper_certificate": root,
                "lower_certificate": produced_lower,
            }
        )

    negative_controls = _budget_binding_negative_controls(
        corpus["variable_cases"][0], coordinate_pool
    )

    schedule_case = corpus["schedule_case"]
    exposures = schedule_case["exposures"]
    pins = schedule_case["pins"]
    threshold = schedule_case["threshold"]
    charges = schedule_case["charges"]
    pool_size = len(coordinate_pool)
    schedule = minimum_cost_schedule(
        exposures, pins, threshold, charges, pool_size=pool_size
    )
    actual_subsets = enumerate_actual_schedules(
        exposures, pins, threshold, charges, pool_size=pool_size
    )
    safe_subsets = [row for row in actual_subsets if row["safe"]]
    best = min((row["cost"], row["refresh_boundaries"]) for row in safe_subsets)
    if (
        schedule["kind"] != "schedule"
        or (schedule["cost"], schedule["refresh_boundaries"]) != best
    ):
        raise AssertionError("minimum-cost actual refresh schedule failed")

    schedules = []
    rng = random.Random(20260914)
    for index, row in enumerate(actual_subsets):
        refreshes = set(row["refresh_boundaries"])
        effective = row["effective_pin_budgets"]
        capacity = row["capacity"]
        safe = row["safe"]
        if safe:
            concrete = {
                "field": 29,
                "threshold": threshold,
                "epochs": len(exposures),
                "pins": [
                    sorted(rng.sample(coordinate_pool, value))
                    if boundary in refreshes
                    else coordinate_pool[:]
                    for boundary, value in enumerate(pins, start=1)
                ],
                "exposed": [
                    sorted(rng.sample(coordinate_pool, value))
                    for value in exposures
                ],
            }
            if not verify_budget_trace(
                concrete, exposures, effective, threshold, coordinate_pool
            ):
                raise AssertionError("safe schedule trace violates its effective instance")
            certificate = produce_pinned(concrete)
            if certificate["kind"] != "hiding" or not verify_pinned(concrete, certificate):
                raise AssertionError("safe schedule certificate failed")
        else:
            witness = lower_trace(exposures, effective, threshold)
            concrete = witness["case"]
            for boundary in range(len(pins)):
                if boundary + 1 not in refreshes:
                    concrete["pins"][boundary] = coordinate_pool[:]
            if not verify_budget_trace(
                concrete, exposures, effective, threshold, coordinate_pool
            ):
                raise AssertionError("unsafe schedule trace violates its effective instance")
            if not verify_transport(witness):
                raise AssertionError("strengthened skipped-boundary witness failed")
            transport_checks += 1
            certificate = produce_pinned(concrete)
            if certificate["kind"] != "revealing" or not verify_pinned(concrete, certificate):
                raise AssertionError("unsafe schedule witness failed")
        certificates += 1
        schedules.append(
            {
                "id": f"schedule-{index:02d}",
                "refresh_boundaries": sorted(refreshes),
                "cost": row["cost"],
                "universally_safe": safe,
                "capacity": capacity,
                "case": concrete,
                "certificate": certificate,
            }
        )

    if min(row["cost"] for row in schedules if row["universally_safe"]) != schedule["cost"]:
        raise AssertionError("all-subset actual-schedule optimality failed")

    mandatory_case = corpus["mandatory_schedule_case"]
    mandatory_schedule = minimum_cost_schedule(
        mandatory_case["exposures"],
        mandatory_case["pins"],
        mandatory_case["threshold"],
        mandatory_case["charges"],
        allowed=mandatory_case["allowed"],
        mandatory=mandatory_case["mandatory"],
        max_refreshes=mandatory_case["max_refreshes"],
        pool_size=mandatory_case["pool_size"],
    )
    mandatory_subsets = enumerate_actual_schedules(
        mandatory_case["exposures"],
        mandatory_case["pins"],
        mandatory_case["threshold"],
        mandatory_case["charges"],
        allowed=mandatory_case["allowed"],
        mandatory=mandatory_case["mandatory"],
        max_refreshes=mandatory_case["max_refreshes"],
        pool_size=mandatory_case["pool_size"],
    )
    mandatory_safe = [row for row in mandatory_subsets if row["safe"]]
    mandatory_best = min(
        (row["cost"], row["refresh_boundaries"]) for row in mandatory_safe
    )
    forced_cut_width = max(
        interval_cost(
            mandatory_case["exposures"], mandatory_case["pins"], start, stop
        )
        for start, stop in [(0, 1), (1, 2)]
    )
    if (
        mandatory_schedule["kind"] != "schedule"
        or (mandatory_schedule["cost"], mandatory_schedule["refresh_boundaries"])
        != mandatory_best
        or mandatory_schedule["certificate_boundaries"] != []
        or mandatory_schedule["capacity"]["capacity"] != 3
        or forced_cut_width != 4
    ):
        raise AssertionError("mandatory-refresh/certificate-cut separation failed")

    # Maximal refresh cannot help an all-zero-refresh-space trace.
    impossible = minimum_cost_schedule(
        [1, 1, 1], [2, 2], 3, [1, 1], pool_size=24
    )
    if impossible["kind"] != "impossible":
        raise AssertionError("impossible scheduling control failed")

    return {
        "coordinate_pool": coordinate_pool,
        "mathematical_cases": mathematical,
        "variable_cases": case_records,
        "schedule_result": schedule,
        "schedules": schedules,
        "mandatory_schedule_result": mandatory_schedule,
        "mandatory_schedule_forced_cut_width": forced_cut_width,
        "impossible_control": impossible,
        "counts": {
            "mathematical_budget_cases": len(mathematical),
            "exhaustive_partitions": partition_visits,
            "variable_budget_cases": len(case_records),
            "variable_concrete_traces": 2 * len(case_records),
            "schedule_subsets": len(schedules),
            "safe_schedule_subsets": len(safe_subsets),
            "mandatory_schedule_subsets": len(mandatory_subsets),
            "certificate_checks": certificates,
            "transport_checks": transport_checks,
            "budget_binding_negative_controls": negative_controls,
        },
    }
