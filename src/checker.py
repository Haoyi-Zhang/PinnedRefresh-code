"""Certificate verification without importing producer, matrix, or elimination.

Hiding certificates are evaluated as polynomials. Revealing certificates are
checked on the constant-secret assignment and every coefficient basis assignment.
Only parsing/parameter validation is shared with the producer.
"""
from __future__ import annotations
from .model import validate, integer


def evaluate(coefficients: list[int], x: int, q: int) -> int:
    value = 0
    for c in reversed(coefficients):
        value = (value * x + c) % q
    return value


def observations(trace: dict, polys: list[list[int]]) -> list[int]:
    q = trace["field"]
    values = []
    for ob in trace["observations"]:
        if ob["kind"] == "snapshot":
            values.append(evaluate(polys[ob["epoch"]], ob["x"], q))
        else:
            values.append((evaluate(polys[ob["after"]], ob["x"], q) - evaluate(polys[ob["before"]], ob["x"], q)) % q)
    return values


def verify(trace: dict, cert: dict) -> bool:
    validate(trace)
    return _verify_validated(trace, cert)


def _verify_validated(trace: dict, cert: dict) -> bool:
    """Internal checker; caller has validated its own observation/constraint budgets."""
    if not isinstance(cert, dict):
        return False
    q, k, t = (trace[z] for z in ("field", "threshold", "epochs"))
    if cert.get("kind") == "hiding":
        if set(cert) != {"kind", "polynomials"}:
            return False
        ps = cert["polynomials"]
        if not isinstance(ps, list) or len(ps) != t:
            return False
        if any(not isinstance(p, list) or len(p) != k or any(not integer(c) or not 0 <= c < q for c in p) or p[0] != 1 for p in ps):
            return False
        return all(y == 0 for y in observations(trace, ps))
    if cert.get("kind") == "revealing":
        if set(cert) != {"kind", "weights"}:
            return False
        ws = cert["weights"]
        if not isinstance(ws, list) or len(ws) != len(trace["observations"]):
            return False
        if any(not integer(w) or not 0 <= w < q for w in ws):
            return False
        base = [[1] + [0] * (k - 1) for _ in range(t)]
        if sum(w * y for w, y in zip(ws, observations(trace, base))) % q != 1:
            return False
        for e in range(t):
            for j in range(1, k):
                ps = [[0] * k for _ in range(t)]
                ps[e][j] = 1
                if sum(w * y for w, y in zip(ws, observations(trace, ps))) % q:
                    return False
        return True
    return False
