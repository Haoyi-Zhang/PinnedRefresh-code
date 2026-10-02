"""Direct exhaustive output-distribution oracle; no elimination or rank calls."""
from __future__ import annotations
from collections import Counter
from itertools import product
from .model import validate


def exact_distributions(trace: dict, assignment_limit: int = 20000) -> dict:
    validate(trace)
    q, k, t = (trace[z] for z in ("field", "threshold", "epochs"))
    count = q ** (1 + t * (k - 1))
    if count > assignment_limit:
        raise ValueError("direct oracle assignment cap exceeded")
    hist = []
    for secret in range(q):
        counts = Counter()
        for randomness in product(range(q), repeat=t * (k - 1)):
            # Direct power sum, deliberately separate from checker Horner evaluation.
            def share(e: int, x: int) -> int:
                return (secret + sum(randomness[e * (k - 1) + j - 1] * x ** j for j in range(1, k))) % q
            outputs = []
            for ob in trace["observations"]:
                if ob["kind"] == "snapshot":
                    outputs.append(share(ob["epoch"], ob["x"]))
                else:
                    outputs.append((share(ob["after"], ob["x"]) - share(ob["before"], ob["x"])) % q)
            counts[tuple(outputs)] += 1
        hist.append(counts)
    equal = all(h == hist[0] for h in hist[1:])
    support = [set(h) for h in hist]
    disjoint = all(support[i].isdisjoint(support[j]) for i in range(q) for j in range(i + 1, q))
    multiplicities = sorted({n for h in hist for n in h.values()})
    return {"assignment_count": count, "conditional_support_sizes": [len(h) for h in hist],
            "multiplicities": multiplicities, "all_conditional_histograms_equal": equal,
            "all_secret_supports_pairwise_disjoint": disjoint,
            "verdict": "hiding" if equal else "revealing" if disjoint else "partial"}
