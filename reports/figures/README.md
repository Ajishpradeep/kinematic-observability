# Figure catalog

Every published figure lives in this folder; the repository check refuses figures anywhere
else. Each figure is drawn from aggregate results in this repository, and none shows a
recording or a person.

## Two-link study

Used in the [two-link report](../README.md). Regenerate with
`python -m observability report --results results --out local/report`.

| File | What it shows | Data |
|---|---|---|
| `synthetic.svg`, `synthetic.png` | Image residual against wrist 3D error for each refinement on matched synthetic chains. | `results/synthetic/aggregates.csv` |
| `optitrack.svg`, `optitrack.png` | The same comparison on recorded chains: refinement lowers the image residual without lowering wrist error. | `results/optitrack/aggregates.csv` |

## Wrist study

Used in [What two cameras preserve about wrist motion](../few-camera-wrist/README.md).
Regenerate with `python -m observability.study.publication` (see the
[study guide](../../src/observability/study/README.md)). Tables are in the
[table catalog](../few-camera-wrist/tables/README.md).

| File | Report figure | What it shows | Data |
|---|---|---|---|
| [`measurement-chain.svg`](few-camera-wrist/measurement-chain.svg) | Figure 1 | The chain from pixels to an outcome, and the part each experiment examined. | Diagram, no data |
| [`two-link.svg`](few-camera-wrist/two-link.svg) | Figure 2 | Two depths with the same pixel and segment length; image residual and wrist error before and after refinement, per participant. | `results/optitrack/aggregates.csv` and the exact two-depth example |
| [`setup-and-targets.svg`](few-camera-wrist/setup-and-targets.svg) | Figure 3 | Camera layout (not to scale) and median distances between the four wrist definitions (to scale). | `reference-transfer.csv` |
| [`position-and-displacement.svg`](few-camera-wrist/position-and-displacement.svg) | Figure 4 | Median position and displacement error per capture group and condition. | `group-summary.csv` |
| [`displacement-by-movement.svg`](few-camera-wrist/displacement-by-movement.svg) | Figure 5 | *Post hoc.* Displacement error by size of the true movement, with the zero-movement baseline. | `displacement-by-movement.csv` |
| [`risk-coverage.svg`](few-camera-wrist/risk-coverage.svg) | Figure 6 | Mean error of the two-view estimates kept by ray gap and by confidence, against the share kept. | Analysis output; areas in `risk-and-policy.csv` |
| [`acceptance-failures.svg`](few-camera-wrist/acceptance-failures.svg) | Figure 7 | Failure among accepted estimates by held-out group (a), and by true movement (b, *post hoc*). | `risk-and-policy.csv`, `acceptance-by-movement.csv` |
| [`reference-failures.svg`](few-camera-wrist/reference-failures.svg) | Figure 8 | Failure of one set of accepted estimates under four wrist definitions. | `reference-transfer.csv` |
