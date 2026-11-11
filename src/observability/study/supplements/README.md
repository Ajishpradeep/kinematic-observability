# Study supplements

Two analyses that run after the main [study pipeline](../README.md) and reuse its frozen
design, observations and policy. They differ in status, and the report keeps that
difference visible.

| Module | Status | Command | Writes |
|---|---|---|---|
| `proxy.py` | Planned before the held-out groups were scored | `python -m observability.study.supplements.proxy` | `local/study/proxy/policy.json`, `development.json`, `confirmation.json` |
| `movement.py` | Post hoc, added after the planned results were complete | `python -m observability.study.supplements.movement` | `local/study/movement/development.json`, `confirmation.json` |

## `proxy.py`: two-view supervision of a one-view rule

A single-camera deployment can only use one view's detector confidence. This supplement asks
whether the second camera can teach that rule during development. For each single view and
each outcome, it treats the distance between the one-view estimate and the two-view estimate
as a stand-in loss, fits a confidence cutoff on development groups with the same
`fit_policy` settings as the main analysis, and then scores the accepted estimates against
the marker reference in held-out groups. It checks that the main policy belongs to the same
design before it starts.

Its rows appear in `reports/few-camera-wrist/tables/proxy-policy.csv` and in Section 4.5 of
the report: three of four fits found no feasible cutoff, and the fourth exceeded the
failure target in confirmation.

## `movement.py`: error by the size of the true movement

This module answers a question raised only after the planned results: how much of the
displacement error depends on how far the wrist actually moved? It reads the same frozen
rows and introduces no score or cutoff. Its parts:

| Function | What it computes |
|---|---|
| `window_pairs` | The two six-frame displacement pairs of each scheduled window, matched exactly to the main analysis. |
| `offset_decomposition` | For endpoint errors e₁ and e₂, the shared part s = (e₁ + e₂)/2 and the changing part h = (e₂ − e₁)/2, which satisfy ‖e₁‖² + ‖e₂‖² = 2‖s‖² + 2‖h‖². Displacement error is 2‖h‖. |
| `in_bin`, `_bin_rows` | Bands of true displacement: below 10, 10–25, 25–50, 50–100, 100–200 and 200 mm and above. |
| `frozen_cutoffs` | Reads the accept cutoffs from the frozen `policy.json`, so the acceptance breakdown uses exactly the rules of the main analysis. |
| `summarize` | Per split and condition: medians and 90th percentiles by band, the zero-movement baseline (whose error equals the true displacement), accepted failures by band, the error decomposition and image-space detector statistics. |

`python -m observability.study.publication` turns these outputs into the supplementary tables
`displacement-by-movement.csv`, `zero-movement-baseline.csv`, `acceptance-by-movement.csv`,
`error-structure.csv` and `image-observations.csv`, and into Figures 5 and 7b of the report.

## Tests

`tests/test_study.py` checks that `window_pairs` matches the main analysis's endpoints, that
the decomposition identity holds, that the bands and frozen cutoffs behave as described, and
that published group labels are anonymous.
