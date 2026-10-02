"""Exact finite adaptive-policy check with rational total variation."""
from collections import Counter
from fractions import Fraction


def exact_policy() -> dict:
    """Enumerate one threshold-two policy over F_5.

    For F(X)=S+aX, the policy reads F(1) and reads F(2) exactly when
    F(1)=0.  The second read then determines S, while every one-read leaf
    leaves S uniform.  There is one random coefficient; the complete
    enumeration therefore contains 5 secrets times 5 coefficients = 25
    assignments.
    """
    q = 5
    hist = []
    for secret in range(q):
        counts = Counter()
        for coefficient in range(q):
            first = (secret + coefficient) % q
            leaf = (
                ("two", first, (secret + 2 * coefficient) % q)
                if first == 0
                else ("one", first)
            )
            counts[leaf] += 1
        hist.append(counts)

    leaves = set().union(*(set(h) for h in hist))
    posterior_types = {}
    for leaf in leaves:
        counts = [h[leaf] for h in hist]
        if all(count == counts[0] for count in counts):
            posterior_types[str(leaf)] = "uniform"
        elif sum(count > 0 for count in counts) == 1:
            posterior_types[str(leaf)] = "point"
        else:
            raise AssertionError("posterior dichotomy failed")

    reveal = [
        Fraction(sum(n for leaf, n in h.items() if leaf[0] == "two"), q)
        for h in hist
    ]
    total_variation = {}
    for first_secret in range(q):
        for second_secret in range(first_secret + 1, q):
            total_variation[f"{first_secret},{second_secret}"] = str(
                sum(
                    (
                        Fraction(
                            abs(hist[first_secret][leaf] - hist[second_secret][leaf]),
                            2 * q,
                        )
                        for leaf in leaves
                    ),
                    Fraction(0),
                )
            )

    assert set(total_variation.values()) == {"1/5"}
    assert set(reveal) == {Fraction(1, 5)}
    return {
        "field": q,
        "threshold": 2,
        "randomness_dimension": 1,
        "assignment_count": q**2,
        "policy": "observe F(1); observe F(2) iff the first value is zero",
        "reveal_probabilities": [str(probability) for probability in reveal],
        "pairwise_total_variation": total_variation,
        "posterior_types": posterior_types,
        "conditional_histograms": [
            {str(leaf): count for leaf, count in sorted(h.items())} for h in hist
        ],
    }
