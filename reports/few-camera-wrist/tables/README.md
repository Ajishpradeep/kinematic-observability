# Table catalog: wrist study

Aggregate results behind [What two cameras preserve about wrist motion](../README.md). Every
row summarises a split, a capture group or a band of movement; no table contains a
recording, a frame or a trajectory. The [study guide](../../../src/observability/study/README.md)
explains how to regenerate them.

## Conventions

| Column value | Meaning |
|---|---|
| `split` | `development` (three capture groups, used for fitting) or `confirmation` (four held-out groups). |
| `group` | Anonymous capture-group label: D1–D3 for development, C1–C4 for confirmation. |
| `method` | `view_a`, `view_b`: one camera with a fixed-depth plane. `two_view`: midpoint triangulation from both cameras. |
| `outcome` | `absolute`: wrist position. `change`: wrist displacement over six frames (50 ms at 120 Hz, 25 ms at 240 Hz). |
| `reference` / `alternative` | `midpoint` of the radial and ulnar styloid markers (primary), `fitted` hand origin of the optical skeleton, single `radial` or `ulnar` marker. |
| `score` | `ray_gap`: distance between the two camera rays. `confidence`: lowest detector wrist confidence across views. For displacement, the worse of the two endpoints. |
| Units | Distances in millimetres, pixels where the column says `pixel`; fractions are between 0 and 1. |
| Tolerances | 100 mm for position and 50 mm for displacement. A failure is a loss above tolerance. |

## Tables

Tables marked *post hoc* come from the movement analysis added after the planned results;
they use the same frozen rows and introduce no new score or cutoff.

| File | Rows | What it holds | Used in the report | Written by |
|---|---:|---|---|---|
| [denominators.csv](denominators.csv) | 56 | Counts per split: groups, recordings, decoded images, images with no or several people, scheduled and scored positions and displacements. | Table 2 | `study/report.py` |
| [reference-metrics.csv](reference-metrics.csv) | 48 | Per split, method, outcome and reference: medians and 90th percentiles of loss, failures, direction cosine, vector gain, magnitude regression, and group-level ranges with leave-one-group-out bounds. | Table 3, §4.1 | `study/report.py` |
| [group-summary.csv](group-summary.csv) | 42 | Per capture group, method and outcome: scored count, median and 90th-percentile error against the midpoint. | Figure 4, §4.1–4.2 | `study/publication.py` |
| [displacement-by-movement.csv](displacement-by-movement.csv) | 36 | *Post hoc.* Displacement error by band of true displacement (below 10, 10–25, 25–50, 50–100, 100–200, 200 mm and above): pairs, true and estimated medians, error median and 90th percentile, error relative to true movement, median cosine. | Figure 5, §4.2 | `study/publication.py` |
| [zero-movement-baseline.csv](zero-movement-baseline.csv) | 32 | *Post hoc.* The rule that always reports no movement, against each camera condition, overall and in three movement bands: median error, failures, and the fraction of pairs where a camera beats the zero rule. | §4.2 | `study/publication.py` |
| [geometry-control.csv](geometry-control.csv) | 12 | Errors with detector pixels against pixels projected from the marker midpoint, on matched observations. | Table 4, §4.3 | `study/report.py` |
| [error-structure.csv](error-structure.csv) | 6 | *Post hoc.* The share of squared position error common to both endpoints of a pair, the median shared offset and its change, the rank correlation of position and displacement error, and errors with one or several person boxes. | §4.4 | `study/publication.py` |
| [image-observations.csv](image-observations.csv) | 2 | *Post hoc.* Detector behaviour in the images: pixel distance to the projected midpoint, frame-to-frame pixel error against true pixel motion, opposite-wrist and far-off detections, and the errors of pairs touched by them. | §4.4 | `study/publication.py` |
| [risk-and-policy.csv](risk-and-policy.csv) | 16 | Per score: rank correlation with loss, area under the risk–coverage curve relative to no ranking, fitted accept and repeat cutoffs, and the outcome of the frozen rule (accepted, repeated, withheld, failures, worst-group failure rate). | Figures 6–7a, §4.5 | `study/report.py` |
| [acceptance-by-movement.csv](acceptance-by-movement.csv) | 12 | *Post hoc.* Accepted two-view displacements and their failures in three movement bands, for both scores. | Figure 7b, §4.5 | `study/publication.py` |
| [proxy-policy.csv](proxy-policy.csv) | 24 | A one-view confidence rule fitted with two-view disagreement as the loss, and its held-out outcome against the marker reference. | §4.5 | `study/report.py` |
| [reference-transfer.csv](reference-transfer.csv) | 48 | The same estimates and decisions scored against an alternative wrist: median separation of the references, pass/fail labels that switch, and failures among the frozen accepted set under each reference. | Figure 8, §4.6 | `study/report.py` |
| [sensitivity.csv](sensitivity.csv) | 60 | Variants of the main analysis: reference shifted by ±1 frame, doubled interval (`outer_window`), wrist confidence of at least 0.25, and 120 Hz or 240 Hz recordings only, with medians on common support. | §4.7 | `study/report.py` |

Two report elements have no table here. Table 1, reference availability across 349
recordings, comes from the pilot's reference audit, which stays private because it is
organised per recording. The risk–coverage curves of Figure 6 are drawn from the analysis
output; this folder gives their summary areas in `risk-and-policy.csv`.

The report's figures are listed in the [figure catalog](../../figures/README.md).
