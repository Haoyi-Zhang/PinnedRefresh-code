#!/usr/bin/env python3
"""Compute a minimum-cost offline robust refresh schedule from public budgets."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.budgets import (
    lower_trace,
    minimum_cost_schedule,
    verify_budget_trace,
    verify_transport,
)

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

try:
    document = json.loads(args.input.read_text())
    required = {"exposures", "pins", "threshold", "charges"}
    optional = {"allowed", "mandatory", "max_refreshes", "pool_size"}
    if not required <= set(document) or set(document) - required - optional:
        raise ValueError(
            "input requires exposures, pins, threshold, charges and permits "
            "allowed, mandatory, max_refreshes, pool_size"
        )
    pool_size = document.get("pool_size", 24)
    result = minimum_cost_schedule(
        document["exposures"],
        document["pins"],
        document["threshold"],
        document["charges"],
        allowed=document.get("allowed"),
        mandatory=document.get("mandatory"),
        max_refreshes=document.get("max_refreshes"),
        pool_size=pool_size,
    )
    if result["kind"] == "impossible" and "capacity_witness" in result:
        witness = lower_trace(
            document["exposures"],
            result["effective_pin_budgets"],
            document["threshold"],
        )
        coordinate_pool = list(range(1, pool_size + 1))
        if not verify_transport(witness) or not verify_budget_trace(
            witness["case"],
            document["exposures"],
            result["effective_pin_budgets"],
            document["threshold"],
            coordinate_pool,
        ):
            raise AssertionError("transport witness rejected")
        result["interpolation_witness"] = witness
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(result["kind"])
except (OSError, ValueError, AssertionError) as exc:
    print("FAILED: " + str(exc), file=sys.stderr)
    raise SystemExit(1)
