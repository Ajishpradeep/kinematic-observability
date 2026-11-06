# Implementation and model inference

This package supports the [kinematic observability study](../../README.md): how geometric
constraints, image observations and anatomical correspondence affect reconstruction.
It contains the completed two-link diagnostic and the observation adapters being developed
for the expansion. The [research report](../../reports/README.md) contains the measured
findings; this page explains what the code runs and what its outputs mean.

## Modules and commands

Run commands from an installed checkout with `python -m observability <command>` or
`kinematic-observability <command>`. Each command has `--help`.

| Module | Command | Scope |
|---|---|---|
| [geometry.py](geometry.py) | Library | Two-link state encoding, forward kinematics, camera projection, refinement and per-chain metrics. Positions in metres, angles in radians. |
| [experiment.py](experiment.py) | `run`, `oracle` | Generate seeded synthetic inputs or compare refinements on prepared chain data; `oracle` replaces detected pixels with reference projections as a privileged diagnostic. |
| [data.py](data.py) | `prepare` | Adapt the historical authorized cohort cache to the baseline NPZ format. This is not a raw Motive importer or a converter for new model predictions. |
| [reporting.py](reporting.py) | `report` | Generate tables and figures from saved aggregates; it does not execute a model. |
| [verification.py](verification.py) | `verify` | Check recorded artifacts and archived source hashes, aggregate consistency and numerical guarantees; record maintained source hashes for new runs. |
| [assets.py](assets.py) | `audit` | Inspect configured local asset roots, optionally count files by extension, and save a metadata inventory without recording filenames. |
| [models.py](models.py) | `infer` | Run public pretrained models on one or more images, preserving native landmarks and model provenance. |
| [__main__.py](__main__.py) | Entry point | Dispatch commands to the modules above. |

The completed diagnostic consumes three-joint chains and compares fixed-input refinement
methods. The expansion's inference adapters produce image observations and native body
estimates. These are distinct stages: inference output must be matched to a declared
reference and joint definition before it becomes an accuracy experiment.

## Expansion models

| Model | Role in this implementation | Output convention |
|---|---|---|
| Stock [YOLO26 pose](https://github.com/ultralytics/ultralytics) | Person boxes and 2D keypoints; also supplies the boxes passed to Fast SAM | COCO17 pixels, keypoint scores and box confidence |
| Public [Fast SAM 3D Body](https://github.com/yangtiming/Fast-SAM-3D-Body) | Image-based 3D body estimation using the original public SAM 3D Body checkpoint | Native MHR70 2D/3D landmarks and separate camera translation |

The default detector is `yolo26n-pose`; s/m/l/x variants can be selected explicitly with
`--yolo`. Fast SAM uses the original `facebook/sam-3d-body-dinov3` weights. Public checkpoint
revisions are pinned in `models.py`, and downloaded files are hashed in each run manifest.
The adapter checks that the selected Fast SAM checkout has the public upstream origin
and an unchanged package, then records its commit. Fine-tuned/custom checkpoint paths
are not accepted by the inference command.

Both models receive images. YOLO's 2D keypoints are saved, but only its **boxes** are passed
to Fast SAM; this is not a 2D-keypoint-to-3D lifting model. Fast SAM runs body-only inference
without hand refinement. No mask prompt or field-of-view estimator is supplied. Optional
`--intrinsics` provides a calibrated 3×3 K matrix as JSON and applies to every input image;
otherwise the upstream default camera assumption is used. These choices are recorded.

For the current expansion, data preparation is scoped to OptiTrack recordings and
SAM/Fast SAM pseudo-labelled 2D/3D data with their traceable source images. OptiTrack's
fitted skeleton and marker-derived constructions must be qualified separately.
SAM-generated targets can support consistency analyses but cannot independently validate
the model that generated them. Synthetic chains remain useful for numerical verification.

## Run the adapters

Install the package from the repository root:

```sh
python -m pip install -e '.[inference]'
python -m observability infer --model yolo26 --images /path/to/frame.png \
  --device cpu --out local/observations-2d
python -m observability infer --model fast-sam3d --images /path/to/frame.png \
  --fast-sam-root /path/to/Fast-SAM-3D-Body \
  --device cuda:0 --out local/observations-3d
```

Fast SAM additionally requires its upstream dependencies in a compatible CUDA environment
and access to the original checkpoint. Installing this package's inference extra alone
does not install that upstream runtime. Use a fresh output directory for each run.

For asset discovery, provide a local JSON array of `id`, `path` and `role` records:

```sh
python -m observability audit --config /path/to/assets.json \
  --scan optitrack sam_cache --out local/asset-audit.json
```

The ids after `--scan` must exist in that config. Unselected roots receive existence checks
only. A root inventory does not establish per-recording synchronization, usable reference
landmarks, dataset independence or publication rights.

`audit` and `infer` require outputs under `local/` in the working directory. Model caches
stay outside the repository; the default is `/tmp/observability-public-models`, with an
explicit `--cache` option for a persistent external location. No model weights or raw data
are bundled. Input formats for baseline `prepare`/`run` are in the
[report's reproduction section](../../reports/README.md#reproducibility).

## Prediction files and interpretation

Each input image gets a numbered `frame-000000.npz` file. Array names describe the native
schema rather than implying anatomical equivalence:

| Arrays | Meaning |
|---|---|
| `image_size_hw` | Original image height and width |
| `boxes_xyxy`, `box_confidence` | Detected boxes and scores |
| `coco17_xy_px`, `coco17_confidence` | Native detector landmarks and scores |
| `mhr70_xy_px`, `mhr70_xyz_m` | Fast SAM's native projected and 3D landmarks, when selected |
| `camera_translation_m` | Translation kept separate from the native MHR coordinates |

The run manifest records input/output hashes, checkpoint hashes and revisions, runtime
versions, detector threshold, camera inputs, source hashes and completion status. A frame
with no detections produces empty person arrays; detections are indexed per image and are
not tracked identities.

Native MHR coordinates plus the recorded translation are intended to give camera-space
metres; verify projection and camera conventions before reference scoring. COCO17, MHR70,
IL24 derivatives and Motive bone origins are not interchangeable. No automatic anatomical
remapping, temporal tracking, video synchronization, reference construction or uncertainty
calibration is performed. Inference files are not directly compatible with the baseline
chain NPZ format, and detector confidence is not an accuracy guarantee.

## Verification status

The numerical and adapter tests are in [tests/](../../tests/). Run
`python -m unittest discover -s tests -v` and `python -m observability verify` from the
checkout. The latter verifies the historical evidence, not the accuracy of a new predictor.

Stock YOLO26 inference has passed a generated blank-image execution check. Fast SAM's
adapter has interface-level tests with controlled outputs; its live CUDA inference remains
unverified. No expansion accuracy benchmark or inference speed comparison has been
completed. The models are observation tools for investigating the research question;
any performance claim requires a separately specified evaluation.
