"""Public input validation for prime-field polynomial observation traces.

A delta is an explicit difference-only leakage channel, not a reduced model of
full-state corruption. No protocol, device, or erasure implementation is modeled.
"""
from __future__ import annotations
from typing import Any


def integer(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate(trace: Any) -> None:
    if not isinstance(trace, dict) or set(trace) != {"field", "threshold", "epochs", "observations"}:
        raise ValueError("trace must contain exactly field, threshold, epochs, observations")
    q, k, t = (trace[z] for z in ("field", "threshold", "epochs"))
    if not all(integer(x) for x in (q, k, t)):
        raise ValueError("integer parameters required")
    if not (3 <= q <= 257) or any(q % d == 0 for d in range(2, int(q ** 0.5) + 1)):
        raise ValueError("field must be a prime between 3 and 257")
    if not 2 <= k <= min(12, q - 1) or not 1 <= t <= 12:
        raise ValueError("unsupported threshold or epoch count")
    observations = trace["observations"]
    if not isinstance(observations, list) or len(observations) > 64:
        raise ValueError("at most 64 observations are permitted")
    coords = set()
    for ob in observations:
        if not isinstance(ob, dict):
            raise ValueError("observation must be an object")
        kind = ob.get("kind")
        expected = {"kind", "epoch", "x"} if kind == "snapshot" else {"kind", "before", "after", "x"}
        if kind not in {"snapshot", "delta"} or set(ob) != expected:
            raise ValueError("invalid observation fields or kind")
        x = ob["x"]
        if not integer(x) or not 1 <= x < q:
            raise ValueError("coordinates must be nonzero canonical field elements")
        coords.add(x)
        if kind == "snapshot":
            if not integer(ob["epoch"]) or not 0 <= ob["epoch"] < t:
                raise ValueError("invalid snapshot epoch")
        else:
            u, v = ob["before"], ob["after"]
            if not integer(u) or not integer(v) or not 0 <= u < v < t:
                raise ValueError("delta requires before < after in epoch range")
    if len(coords) > 24:
        raise ValueError("at most 24 distinct party coordinates are permitted")
