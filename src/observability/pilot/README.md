# Decision pilot

The pilot decides what the recordings can support before any study outcome is scored. It
inventories the recordings, checks that video, calibration and motion-capture files belong
together, measures timing and projection conventions on small samples, audits which joints
have a usable reference, and closes a set of evidence gates. Its output is the input to the
[wrist study](../study/README.md). The findings are summarised in Section 2 of the
[report](../../../reports/few-camera-wrist/README.md#2-deciding-what-to-measure).

Everything the pilot writes goes under ignored `local/pilot/`. Files whose names end in
`-private.json` keep source paths and stay local; `*-summary.json` files hold name-free
counts. Takes and sessions are referred to by salted opaque identifiers (`TAKE-…`), and the
salt (`id-salt.bin`) is created once and never leaves `local/`.

## Inputs

- A root folder of optical motion-capture exports: per take, the body CSV with a fitted
  skeleton and labelled markers, the session calibration file, and two synchronised RGB
  videos. `inventory.py` and `video.py` describe the naming they expect.
- Optionally, a folder of SAM 3D Body pseudo-label shards (`.npz`), used only by the
  repeatability audit.
- The package installed with `pip install -e '.[inference,dev]'` (Python 3.8 or newer). The
  `inference` extra brings the stock detector; `dev` brings OpenCV for frame decoding. The
  force audit also needs `pip install c3d`.

## Stages

The stages are library functions. Each reads the JSON written by an earlier stage and writes
its own file. Run them in this order.

| Step | Module and function | Reads | Writes under `local/pilot/` |
|---:|---|---|---|
| 1 | `bootstrap.bootstrap(root)` | the recordings root | `optitrack-census.json`, `manifest-private.json`, `manifest-summary.json`, `input-validation-private.json`, `input-validation-summary.json`, `state.json`, `id-salt.bin` |
| 2 | `alignment.prepare_alignment_sample(manifest, validation)` | step 1 | `alignment/sample-private.json`, `alignment/images/`, `alignment/references/` |
| 3 | `detector.run_alignment_detector(sample)` | step 2 | `alignment/yolo26n/manifest.json` and detection arrays |
| 4 | `score_alignment.score_alignment(sample, detections)` | steps 2–3 | `alignment/score.json` |
| 5 | steps 2–4 again with `excluded_take_ids` set to the discovery takes | step 1 | `confirmation/` with the same files |
| 6 | `reference_audit.audit_references(manifest, sample)` | steps 1–2 | `reference-audit.json` |
| 7 | `triangulation.evaluate_triangulation(sample, detections)` | discovery and confirmation | `triangulation.json`, `confirmation/triangulation.json` |
| 8 | `force_audit.audit_force_sources(manifest)` | step 1 | `force-validation.json` |
| 9 | `sam_audit.audit_sam_rows(sam_root)` | pseudo-label shards | `sam-repeatability.json` |
| 10 | `provenance.record_pilot_provenance(manifest, samples)` | steps 1, 2, 5 | `source-provenance.json` |
| 11 | `synthesis.synthesize_pilot(...)`, then `finalize.finalize_pilot(state, synthesis)` | steps 6–9 | `synthesis.json`, final `state.json` |

The discovery sample (step 2) fixes the projection convention and the frame offset. The
confirmation sample (step 5) uses different takes and must pass the same frozen gates before
the result counts. Step 11 ranks the candidate studies and records the selected one, which
the study design then reads.

## Running it

From the repository root, with the package installed:

```python
import json
from pathlib import Path

from observability.pilot import (
    alignment, bootstrap, detector, finalize, force_audit, provenance,
    reference_audit, sam_audit, score_alignment, synthesis, triangulation,
)

load = lambda path: json.loads(Path(path).read_text())
pilot = Path("local/pilot")

bootstrap.bootstrap("/path/to/recordings")
manifest = load(pilot / "manifest-private.json")
validation = load(pilot / "input-validation-private.json")

def sample_and_score(name, excluded=()):
    folder = pilot / name
    alignment.prepare_alignment_sample(manifest, validation, folder, excluded_take_ids=excluded)
    sample = load(folder / "sample-private.json")
    detector.run_alignment_detector(sample, folder / "yolo26n", device="cpu")
    detections = load(folder / "yolo26n" / "manifest.json")
    score_alignment.score_alignment(sample, detections, folder / "score.json")
    return sample, detections

discovery, discovery_detections = sample_and_score("alignment")
confirmation, confirmation_detections = sample_and_score(
    "confirmation", excluded=[record["take_id"] for record in discovery["records"]]
)

reference_audit.audit_references(manifest, discovery)
triangulation.evaluate_triangulation(discovery, discovery_detections)
triangulation.evaluate_triangulation(
    confirmation, confirmation_detections, pilot / "confirmation" / "triangulation.json"
)
force_audit.audit_force_sources(manifest)
sam_audit.audit_sam_rows("/path/to/sam-shards")
provenance.record_pilot_provenance(
    manifest, {"discovery": discovery, "confirmation": confirmation}
)

synthesis.synthesize_pilot(
    load(pilot / "triangulation.json"),
    load(pilot / "confirmation" / "triangulation.json"),
    load(pilot / "reference-audit.json"),
    load(pilot / "sam-repeatability.json"),
    load(pilot / "force-validation.json"),
)
finalize.finalize_pilot(load(pilot / "state.json"), load(pilot / "synthesis.json"))
```

The original run went stage by stage, with the output of each gate read before the next
stage started. Running the sequence in one go gives the same files, but read `score.json`
and `state.json` before trusting what follows them. Every function refuses to write outside
`local/`.

## Supporting modules

| Module | What it does |
|---|---|
| `inventory.py` | Read-only census of the recordings root: counts, file kinds, completeness. |
| `manifest.py` | Pairs body CSV, calibration and videos per take; writes the private map and the name-free summary. |
| `video.py` | Video naming rules and container metadata. |
| `validate_inputs.py` | Checks camera count, calibration, container, frame rate and frame count for each candidate pair. Nominal timing is recorded, not assumed to be alignment. |
| `motive.py` | Parses the motion-capture CSV with explicit frame indices and missing values. |
| `calibration.py` | Parses the calibration file and states the projection convention explicitly. |
| `references.py` | Builds marker references (for example the styloid midpoint) and records how each was made and when it is missing. |
| `metrics.py` | Error, change, ranking and risk–coverage metrics shared with the study. |
| `state.py` | The machine-readable evidence gates and claim register. |

## Tests

`tests/test_pilot.py` checks the parsers, projection, triangulation, opaque identifiers,
reference construction, metrics and evidence gates on synthetic inputs. It needs no
recordings:

```sh
python -m unittest tests.test_pilot -v
```
