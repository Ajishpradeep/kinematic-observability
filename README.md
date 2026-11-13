# Kinematic observability

**When does a 3D reconstruction of human movement measure what it appears to measure?**
This repository holds two linked studies of that question, with the code that produced every
number, the aggregate results and the reports. The first asks whether satisfying geometric
constraints makes a reconstructed limb more accurate. The second asks whether a more
accurate position also gives a more accurate measure of movement, and how much the answer
depends on what "the wrist" is taken to be.

| Study | Report | Research note | Code |
|---|---|---|---|
| Two-link reconstruction: constraints, image fit and 3D accuracy | [reports/README.md](reports/README.md) | [A valid reconstruction can still be the wrong one](https://ajishpradeep.com/blog/a-valid-reconstruction-can-still-be-the-wrong-one/) | [src/observability/](src/observability/README.md) |
| Wrist study: position, short displacement and the definition of the target | [reports/few-camera-wrist/](reports/few-camera-wrist/README.md) ([PDF](reports/few-camera-wrist/what-two-cameras-preserve-about-wrist-motion.pdf)) | [From position error to motion error](https://ajishpradeep.com/blog/from-position-error-to-motion-error/) | [pilot/](src/observability/pilot/README.md), [study/](src/observability/study/README.md) |

## Versions

Each study is preserved as a release, so it can be cited or shared as it was published.

| Version | Contents | Snapshot |
|---|---|---|
| [v1.0.0](https://github.com/Ajishpradeep/kinematic-observability/releases/tag/v1.0.0) | Study 1, the two-link reconstruction study | [browse](https://github.com/Ajishpradeep/kinematic-observability/tree/v1.0.0) |
| [v2.0.0](https://github.com/Ajishpradeep/kinematic-observability/releases/tag/v2.0.0) | Study 1 and Study 2, the wrist study, with its pilot, code and report | [browse](https://github.com/Ajishpradeep/kinematic-observability/tree/v2.0.0) |

`main` always holds the latest version.

## Study 1: a valid reconstruction can still be the wrong one

A shoulder–elbow–wrist chain seen by one camera can keep its segment lengths exactly, fit
its image closely and still place the wrist in the wrong 3D position: a single pixel fixes a
ray, and a fixed length can leave two depths on that ray. On matched synthetic geometry,
fixed-length refinement helped. On recorded data it reduced the image residual from
**17.91 to 1.36 px** while mean wrist error rose from **78.3 to 80.3 mm**.

| Wrist error, mm | Initial prediction | Cartesian refinement | Fixed-length refinement |
|---|---:|---:|---:|
| Synthetic: 1,536 chains, mean across three seeds | 101.5 | 53.1 | 43.5 |
| Real: 5,414 chains, mean across three participants | 78.3 | 76.2 | 80.3 |

Replacing detected keypoints with projections of the reference skeleton lowered wrist error
from 80.4 to 39.3 mm, which moved attention from the constraint to the observation. The real
reference is a fitted skeleton from optical motion capture, and calibration, reference pelvis
translation and reference-derived lengths are privileged inputs. This is an exploratory
refinement audit, with no clinical validation or end-to-end comparison of pose estimators.

## Study 2: from position error to motion error

The follow-on uses two calibrated RGB cameras and an optical marker reference (eight
infrared cameras, up to 57 markers) on 330 laboratory recordings of fast whole-body
movement. A pilot on separate recordings chose the wrist as the endpoint, because only the
paired styloid markers gave a direct, continuously visible reference. The design, split and
decision rules were frozen before any outcome was scored: three capture groups for
development and four, 181 recordings, held out for confirmation.

| Held-out groups, against the styloid midpoint | Position median, mm | Displacement median (25–50 ms), mm |
|---|---:|---:|
| One camera, fixed-depth control A | 324.1 | 29.0 |
| One camera, fixed-depth control B | 388.2 | 33.5 |
| Two calibrated cameras | 73.2 | 29.6 |
| Report no movement at all | – | 13.9 |

- **Position improved, the displacement median did not.** A position error shared by both
  frames of a pair cancels in a displacement: with two views, 92.7% of squared position
  error was common to both endpoints. What remains is frame-to-frame detector jitter.
- **The sample decides the statistic.** Median true displacement was 13.9 mm, so reporting
  no movement scored better than any camera. Split by real movement, two views were clearly
  better once the wrist moved at least 50 mm: 52.5 mm against about 71 mm for one view.
  This breakdown was added after the planned analysis and is descriptive.
- **Ranking is easier than deciding.** Ray gap and detector confidence ranked errors, but no
  fixed acceptance rule met its 20% failure target in every held-out group, and about a third
  of accepted displacements failed when the wrist moved at least 50 mm.
- **The target matters.** Holding estimates and decisions fixed, switching from the marker
  midpoint to the fitted hand origin or a single marker moved the same accepted set from
  19.8% to between 21.1% and 27.5% failure.

The one-view conditions are geometric controls, not a trained monocular estimator, and the
cameras are one fixed pair in one laboratory. The report covers the pilot, methods,
limitations and the open questions it leaves.

## Reproduce

Install from a checkout (Python 3.8 or newer; CI uses Python 3.12):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
python -m unittest discover -s tests -v
python -m observability verify
```

**Study 1.** The synthetic experiment and the tables regenerate from code alone:

```sh
python -m observability run --out local/synthetic --synthetic-n 512 --steps 200
python -m observability report --results results --out local/report
```

The recorded-data runs need the original private inputs; their format is in the
[report's reproducibility section](reports/README.md#reproducibility).

**Study 2.** With comparable recordings (motion-capture exports with a fitted skeleton and
labelled markers, the session calibration, and two synchronised RGB videos per take), install
the inference extra and run the pilot, then the study:

```sh
python -m pip install -e '.[inference,dev]'
# pilot: library stages, see src/observability/pilot/README.md
python -m observability.study.design
python -m observability.study.observe --shards 8 --shard 0   # repeat for shards 0-7
python -m observability.study.analyze
python -m observability.study.supplements.proxy
python -m observability.study.report
python -m observability.study.supplements.movement
python -m observability.study.publication --font-dir /path/to/fonts
```

Every stage writes under ignored `local/`, and the frozen design and policy make a stage
stop if its inputs or sources change. The [pilot guide](src/observability/pilot/README.md)
and the [study guide](src/observability/study/README.md) say what each stage reads, writes
and guarantees.

## Repository map

| Location | Contents | Guide |
|---|---|---|
| `src/observability/` | Two-link geometry, experiments, reporting, verification and model adapters | [README](src/observability/README.md) |
| `src/observability/pilot/` | Decision pilot: inventory, pairing, alignment, reference and force audits, evidence gates | [README](src/observability/pilot/README.md) |
| `src/observability/study/` | Wrist study: frozen design, observation, analysis, report and figures | [README](src/observability/study/README.md) |
| `src/observability/study/supplements/` | Planned proxy-rule check and post hoc movement analysis | [README](src/observability/study/supplements/README.md) |
| `reports/` | Two-link report; wrist-study report and PDF | [two-link](reports/README.md), [wrist study](reports/few-camera-wrist/README.md) |
| `reports/few-camera-wrist/tables/` | 13 aggregate tables behind the wrist study | [Table catalog](reports/few-camera-wrist/tables/README.md) |
| `reports/figures/` | Every published figure | [Figure catalog](reports/figures/README.md) |
| `results/` | Two-link aggregates, run manifests, generated tables and the historical source archive | [Results catalog](results/README.md) |
| `tests/` | Geometry, metric, privacy and workflow checks on synthetic inputs | [README](tests/README.md) |

Repository checks and their optional local hooks are managed by
`python .github/check_repository.py --install-hooks`. Add a numerical invariant with any
geometry or metric change; new runs belong under `local/` until reviewed, and recorded
evidence is immutable.

## Data

The recordings were collected in an industrial research laboratory for experiments and
publication. They show identifiable people, so recordings, per-frame trajectories and
the first study's predictor weights stay confidential; only aggregate results are
released, with capture groups labelled generically. The wrist study uses only the stock
public YOLO26n-pose checkpoint.

MIT licensed. [CITATION.cff](CITATION.cff) gives the citation for the wrist study, the two
research notes and the software version. Contributions must use distributable code and data and exclude participant
recordings, trajectories, weights, identifying information and credentials.
