"""Fail on deterministic replay drift; do not compare historical host timings."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    output = Path(sys.argv[1]).resolve()
    comparisons = 0
    for family, names in (
        ("linear", ("certificates", "adaptive", "summary")),
        ("pinned", ("certificates", "simulation", "budgets", "exhaustive", "summary")),
    ):
        for name in names:
            actual = read(output / family / (name + ".json"))
            retained = read(ROOT / "results" / family / (name + ".json"))
            if family == "linear" and name == "summary":
                # The retained Unix run had 41 tests. Current tests include
                # the threshold/pool regressions; no other summary drift is allowed.
                suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
                assert actual.pop("unit_test_count") == suite.countTestCases()
                assert retained.pop("unit_test_count") == 41
            assert actual == retained, (family, name, "deterministic replay drift")
            comparisons += 1
    for name, retained_name in (("traces", "traces"), ("pinned", "pinned"), ("budgets", "budgets")):
        assert read(output / ("generated-" + name + ".json")) == read(ROOT / "cases" / (retained_name + ".json"))
        comparisons += 1
    assert (output / "pinned/cadence.csv").read_text() == (ROOT / "results/pinned/cadence.csv").read_text()
    print(json.dumps({"deterministic_json_comparisons": comparisons, "cadence_rows_match": True,
                      "scope": "Finite semantic replay only; host timings and general proof quantifiers are not verified."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
