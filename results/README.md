# Results catalog: two-link study

Recorded aggregate results of the [two-link study](../reports/README.md). These files are
immutable evidence: `python -m observability verify` checks every one of them against the
hashes in `artifacts.json`. New runs go under ignored `local/` until reviewed.

The wrist study's results live with its report, in
[`reports/few-camera-wrist/tables/`](../reports/few-camera-wrist/tables/README.md).

| Path | What it holds |
|---|---|
| `synthetic/aggregates.csv` | 1,536 seeded synthetic chains (512 per seed, three seeds): error, depth error, bend, image residual and length deviation for every refinement and condition. |
| `optitrack/aggregates.csv` | Recorded chains, 200 optimisation steps: the same measures per participant, view, length source, observation setting, bend cap and method. The report's real-data results use the three participants held out from the predictor's training (P01, P05, P07; 5,414 chains). |
| `optitrack_400/aggregates.csv` | The recorded chains again with 400 optimisation steps, to rule out an unconverged solver. |
| `oracle_pixels/aggregates.csv` | The control that replaces detected keypoints with projections of the reference skeleton. |
| `*/manifest.json` | Execution record per run: settings, step count and input and source hashes. The synthetic and recorded runs also record library versions, device, threads, seeds and conditions. |
| `tables.md` | The report's tables, generated from the aggregates by `python -m observability report`. CI regenerates it and compares. |
| `artifacts.json` | SHA-256 of every recorded artifact, including the two-link figures in `reports/figures/`. |
| `baseline-source.zip` | The six original Python files and protocol that produced the recorded runs, kept so the historical evidence can be traced to its code. |

In the CSVs, `subject` is a participant code (P01–P07) or a synthetic seed, distances
are in millimetres, angles in degrees and image residuals in pixels. Real-data means in the
report weight each participant equally.

## Reproduce

```sh
python -m observability run --out local/synthetic --synthetic-n 512 --steps 200
python -m observability report --results results --out local/report
cmp results/tables.md local/report/tables.md
python -m observability verify
```

The synthetic run regenerates the synthetic aggregates from code. The recorded-data
aggregates need the original private inputs; their format is described in the
[report's reproducibility section](../reports/README.md#reproducibility).
