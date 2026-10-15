# Pinned-share refresh

Exact finite-field validation for *Secrecy and Cadence for Proactive Refresh
with Pinned Shares*. This standalone artifact supplies synthetic trace and
budget inputs, certificate producers and checkers, exact distribution oracles,
an offline refresh scheduler, mathematical arguments, and retained results.

The model uses a fixed coordinate pool. An unavailable holder's scalar must
remain a current share, so refresh pins that evaluation coordinate.
The public-budget criterion is `Gamma < k`; cooperative recovery also requires
`k <= n - u_rec`. The actual refresh set and a partition certificate's cuts
are distinct, including when some refreshes are mandatory.

## Requirements and full reproduction

Use Python 3.10+ on Linux or a compatible Unix with the standard-library
`resource` module. Scientific validation uses no third-party packages,
network, solver, credentials, manuscript directory, or hidden cache.
The executable contract supports prime fields and uses exact integers;
the written argument permits arbitrary finite fields.

Run from this repository root, with empty or absent output directories:

```sh
python reproduce.py --output replay-linear
python reproduce_pinned.py --output replay-pinned
python -B -m unittest discover -s tests -v
python -B tests/regression_prefix_intervals.py -v
```

Each main runner is sequential, uses one worker and no child processes,
and applies 110/115-second CPU limits and a 2-GiB address-space limit.
The scientific Actions workflow runs both campaigns, the discovery tests,
the separate prefix-interval regression, generators, and deterministic-output
gates on Ubuntu 24.04 within a 300-second whole-replay deadline.
Raw outputs are uploaded on success or failure.

The two main runner entry points require Unix. The unit tests, separate
regression, certificate commands, scheduler, and generators also run on Windows;
these focused commands do not reproduce Unix resource measurements.

## Individual certificates and schedules

```sh
python certify.py cases/trace-example.json --output trace-certificate.json
python certify.py cases/trace-example.json --certificate trace-certificate.json
python certify_pinned.py cases/pinned-example.json --output pinned-certificate.json
python certify_pinned.py cases/pinned-example.json --certificate pinned-certificate.json
python plan_refresh.py cases/schedule-example.json --output schedule.json
python plan_refresh.py cases/mandatory-schedule-example.json --output mandatory-schedule.json
```

Create output parent directories first for `certify_pinned.py` and
`plan_refresh.py`. The seven-slot example has total cost 2 and actual refresh
boundaries 2 and 4. The mandatory example has actual refresh set `{1}`,
no certificate cut, and total/prepaid/added charge `1/1/0`.

## Inputs, results, and code

`cases/traces.json`, `cases/pinned.json`, and `cases/budgets.json` contain
the literal synthetic inputs. Regenerate them into separate paths with:

```sh
python make_cases.py --output generated-traces.json
python make_pinned_cases.py --output generated-pinned.json
python make_budget_cases.py --output generated-budgets.json
```

Compare parsed JSON with the corresponding retained inputs; formatting is
not part of that comparison. The sixteen concrete safe-schedule examples use
`random.Random(20260914)` on the stored budgets as part of replay.

`results/linear/` and `results/pinned/` retain certificates, exact distribution
summaries, case-level CSVs, budgets, exhaustive checks, and measurements.
The retained main runs cover 850 concrete traces (427 hiding, 423 revealing),
44,111 field assignments, and 770 rejected false certificate mutations.
`results/campaign-accounting.json` records the counting convention and
distinguishes distinct finite evidence from repeated execution.
Historical test counts and timings describe those runs, not current discovery.

`src/producer.py` uses Gaussian elimination; `src/checker.py` instead verifies
normalized hiding polynomials or revealing linear identities without importing
the producer. Pinned producers/checkers and distribution enumerators are
separate paths. `src/budgets.py` implements capacities, partitions, scheduling,
and transport witnesses; its budget-bound verifier additionally binds the
threshold, budgets, capacity, and explicit coordinate pool.
`src/exhaustive_validation.py` supplies separate bounded rank, partition,
and actual-refresh-subset checks. Its public-budget statement tests existence
of a revealing trace, not revelation by every trace within a budget.
The input horizon is capped at 12. Complete-path copying can cost
`O(T^3)` in partitioning and `O(T^4)` in count-layered scheduling;
the mathematical recurrence's `O(T^2)` implementation is not claimed here.

`proofs/argument.md` contains the written arguments.
`claim_evidence_ledger.csv` maps claims to checks and raw evidence.
The reference-audit, literature-calibration, and external-resources files retain
source identities, access depths, and limits; they are not independent review.

## Optional vector figure

```sh
python -m pip install -r requirements-figures.txt
python -B scripts/plot_figures.py
```

This reads `results/pinned/cadence.csv`, checks the retained integer formulas,
and writes vector `figures/cadence.pdf` without rerunning experiments.
An existing sibling paper's `figures/` directory receives identical bytes;
use `--out` and `--paper-dir` to choose destinations.
Windows Times New Roman is used when available. Elsewhere, `FIGURE_FONT_DIR`
can identify legally available `times.ttf` and `timesi.ttf`; Matplotlib's
Times-compatible STIX serif is the fallback. Proprietary fonts are not bundled.

## Conditions, provenance, and license

The passive realization assumes private authenticated channels, atomic refresh,
a fixed corrupt set within a refresh, actual erasure, and an honest online dealer
when the constrained refresh space has positive dimension. There are no
malicious-party, guaranteed-erasure, network-liveness, changing-membership,
online-scheduling, or deployment-performance claims. Finite enumerations are
computational cross-checks, not a machine-checked general proof or independent
human review. Chorus full-text access remains unresolved at the depth recorded
in the source ledgers; no protocol-equivalence or global-priority claim follows.

`PROVENANCE.md` records provenance and external-use restrictions. Accountable human review,
authorship approval, permissions, and truthful publisher-policy disclosures
remain prerequisites for external use. Code and synthetic fixtures use
`LICENSE`; referenced papers and proprietary fonts are not redistributed.
