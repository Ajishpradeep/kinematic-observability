# Wrist study

This package runs the held-out experiment reported in
[What two cameras preserve about wrist motion](../../../reports/few-camera-wrist/README.md)
and in the note [From position error to motion error](https://ajishpradeep.com/blog/from-position-error-to-motion-error/).
It takes the files written by the [decision pilot](../pilot/README.md), schedules wrist
measurements in every eligible recording, estimates the wrist from one and two calibrated
views, scores the estimates against several wrist definitions, fits accept/repeat/withhold
rules on development groups only, and checks them on held-out groups.

All outputs go under ignored `local/study/`. Only the aggregate tables and figures that the
last two stages write are meant for publication.

## Before you start

- Run the [pilot](../pilot/README.md) first; the design reads `local/pilot/`.
- Install the package with `pip install -e '.[inference,dev]'` (Python 3.8 or newer). The
  observation stage needs the `inference` extra (stock YOLO26 pose) and OpenCV.
- Run every command from the repository root. The stages hash source files by their path
  relative to the root and refuse to run if a hash changes after a freeze.

## Pipeline

| Step | Command | Reads | Writes | What it does |
|---:|---|---|---|---|
| 1 | `python -m observability.study.design` | `local/pilot/` | `local/study/design.json` | Freezes the split, the schedule and the decision policy before any outcome is scored. |
| 2 | `python -m observability.study.observe --shards 8 --shard N` | design | `local/study/observations/TAKE-*.json`, `.npz` | Decodes the scheduled frames from both videos and runs the stock detector. Run once per shard, N = 0–7; shards can run in parallel. |
| 3 | `python -m observability.study.analyze` | design, observations | `local/study/analysis/policy.json`, `development.json`, `confirmation.json` | Measures every condition, fits the rules on development groups, then applies them unchanged to held-out groups. |
| 4 | `python -m observability.study.supplements.proxy` | design, observations, policy | `local/study/proxy/` | Uses two-view disagreement during development to fit a one-view confidence rule, then checks it in confirmation. |
| 5 | `python -m observability.study.report` | analysis, proxy | `local/study/release/` | Writes the release tables (`*.csv`), a technical summary and draft figures. |
| 6 | `python -m observability.study.supplements.movement` | design, observations, analysis | `local/study/movement/development.json`, `confirmation.json` | Post hoc: error by size of the true movement, the zero-movement baseline and the error decomposition. Fits nothing. |
| 7 | `python -m observability.study.publication --font-dir /path/to/fonts` | analysis, movement, release | `local/study/publication/figures/*.svg`, `tables/*.csv` | Draws the report's eight figures and writes its six supplementary tables. |

Each command takes `--help`, and every path above is a default that can be changed with an
option. Step 2 is the slow one: it decodes 5,940 images and runs the detector on each. The
other steps take seconds to minutes on a CPU.

## What the design freezes

`design.py` writes, once:

- **Split.** The three capture groups used for marker alignment in the pilot are ordered by a
  versioned SHA-256 of their identifiers and become the development groups. Every other
  group is held out for confirmation.
- **Eligibility.** Recordings without direct frame pairing and the 14 pilot recordings are
  excluded and counted. The design checks that the pilot used exactly 14 distinct takes; a
  different dataset needs that check changed.
- **Schedule.** Three windows per recording at 20%, 50% and 80% of its length, each with
  frames at −6, 0 and +6 around the centre, so every window gives two six-frame
  displacements.
- **Policy settings.** Tolerances of 100 mm for position and 50 mm for displacement, a 20%
  failure target and at least 10% coverage for the accept cutoff, a repeat cutoff at the 80th
  percentile of development scores (estimates between the two cutoffs are repeated, the rest
  withheld), a 10 mm floor for direction measures and at least 50 direction pairs per group.
- **Hashes** of every pilot file it read.

If `design.json` exists, the stage only checks that a fresh freeze would be identical.

## Guarantees built into the stages

- `observe.py` checks the downloaded detector weights against a pinned SHA-256 before it
  runs, and records the hashes of its own source files and of each observation.
- `analyze.py` writes `policy.json` from development groups only. On every later run it
  recomputes the policy and stops if the policy or any source hash differs, so cutoffs
  cannot drift after the held-out groups have been scored.
- The supplements read the frozen policy; neither fits a new score or cutoff.
- A second, independent run of `analyze` reproduced the policy and both split summaries
  byte for byte.

To start a fresh run, use a new output directory for each stage. Outputs from an earlier run
with different sources make the freeze checks fail on purpose.

## Modules

| Module | Role |
|---|---|
| `design.py` | Freezes split, schedule and policy settings (step 1). |
| `observe.py` | Frame decoding and detection for scheduled windows (step 2). |
| `measure.py` | Builds the wrist references (styloid midpoint, fitted hand origin, radial and ulnar markers) and the estimates: fixed-depth one-view rays through a plane 1 m above the capture origin, and two-view midpoint triangulation with its ray gap. |
| `metrics.py` | Direction cosine, vector gain, risk–coverage curves, `fit_policy` (the accept and repeat cutoffs) and `decisions` (accept, repeat or withhold). |
| `analyze.py` | Builds position and displacement rows per condition, fits one policy per condition and score on development groups, and evaluates held-out groups, including the reference-transfer and sensitivity checks (step 3). |
| `report.py` | Release tables and summaries from the analysis (step 5). |
| `publication.py` | Report figures and supplementary tables (step 7). |
| `supplements/` | The proxy rule and the post hoc movement analysis; see [supplements/README.md](supplements/README.md). |

## From local outputs to the published report

After review, the published files were copied from `local/` into `reports/`:

| From | To |
|---|---|
| `local/study/release/*.csv` (seven tables) | `reports/few-camera-wrist/tables/` |
| `local/study/publication/tables/*.csv` (six tables) | `reports/few-camera-wrist/tables/` |
| `local/study/publication/figures/*.svg` | `reports/figures/few-camera-wrist/` |

The [table catalog](../../../reports/few-camera-wrist/tables/README.md) says what each table
holds and where the report uses it. The release folder also holds draft PNG figures and
Markdown summaries that were not published. The report's PDF was rendered from its Markdown
with WeasyPrint; that renderer is not part of this package.

Figures were drawn with Source Sans 3, passed as `--font-dir` pointing to a folder that holds only its `.ttf` files (the last font file read sets the family). Without it, Matplotlib's
default font is used and only the typography changes.

## Tests

`tests/test_study.py` checks the windows, the depth-plane and two-ray estimates, the
projected-pixel control, the gain and risk metrics, the movement analysis (including the
identity behind the shared-offset result) and the anonymous group labels on synthetic data:

```sh
python -m unittest tests.test_study -v
```
