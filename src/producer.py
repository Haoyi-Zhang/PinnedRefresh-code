"""Exact Gaussian-elimination certificate producer. No numerical dependencies."""
from __future__ import annotations
from .model import validate


def rows(trace: dict) -> list[list[int]]:
    validate(trace)
    return _rows_validated(trace)


def _rows_validated(trace: dict) -> list[list[int]]:
    """Internal row encoding; caller has validated its own observation/constraint budgets."""
    q, k, t = (trace[z] for z in ("field", "threshold", "epochs"))
    result = []
    for ob in trace["observations"]:
        r = [0] * (1 + t * (k - 1))
        x = ob["x"]
        if ob["kind"] == "snapshot":
            r[0] = 1
            blocks = [(ob["epoch"], 1)]
        else:
            blocks = [(ob["before"], -1), (ob["after"], 1)]
        for e, sign in blocks:
            for j in range(1, k):
                r[1 + e * (k - 1) + j - 1] = sign * pow(x, j, q) % q
        result.append(r)
    return result


def solve(matrix: list[list[int]], rhs: list[int], width: int, q: int) -> list[int] | None:
    """A particular solution (free variables zero), or None if inconsistent."""
    if len(matrix) != len(rhs) or any(len(r) != width for r in matrix):
        raise ValueError("inconsistent linear-system shape")
    a = [[v % q for v in r] + [b % q] for r, b in zip(matrix, rhs)]
    pivots = []
    top = 0
    for col in range(width):
        pos = next((i for i in range(top, len(a)) if a[i][col]), None)
        if pos is None:
            continue
        a[top], a[pos] = a[pos], a[top]
        inv = pow(a[top][col], -1, q)
        a[top] = [v * inv % q for v in a[top]]
        for i in range(len(a)):
            if i != top and a[i][col]:
                f = a[i][col]
                a[i] = [(u - f * v) % q for u, v in zip(a[i], a[top])]
        pivots.append(col)
        top += 1
        if top == len(a):
            break
    if any(not any(r[:width]) and r[-1] for r in a):
        return None
    result = [0] * width
    for i, col in enumerate(pivots):
        result[col] = a[i][-1]
    return result


def produce(trace: dict) -> dict:
    validate(trace)
    return _produce_validated(trace)


def _produce_validated(trace: dict) -> dict:
    m = _rows_validated(trace)
    q, k, t = (trace[z] for z in ("field", "threshold", "epochs"))
    width = t * (k - 1)
    h = solve([r[1:] for r in m], [-r[0] for r in m], width, q)
    if h is not None:
        return {"kind": "hiding", "polynomials": [[1] + h[e * (k - 1):(e + 1) * (k - 1)] for e in range(t)]}
    transposed = [[r[j] for r in m] for j in range(width + 1)]
    weights = solve(transposed, [1] + [0] * width, len(m), q)
    if weights is None:
        raise AssertionError("linear alternative violated")
    return {"kind": "revealing", "weights": weights}
