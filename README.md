# Kinematic observability under imperfect constraints

**Ajish Pradeep — independent research study.** A reproducible PyTorch diagnostic of the difference between structural consistency, image agreement and 3D accuracy.

This project asks when fixed segment lengths and angle bounds help an articulated estimate, and when they conceal a wrong reconstruction. It combines an exact perspective-ambiguity counterexample, seeded synthetic experiments, and a retrospective audit of cached monocular predictions against an OptiTrack fitted-skeleton reference.

This is a sensitivity study, not a new trained pose estimator, an OpenSim implementation, or evidence of clinical performance. The real-data arm concerns shoulder–elbow–wrist chains during sports motion. It does not validate neurological gait or smartphone home monitoring.

## Read the evidence

- [Protocol and implementation amendments](PROTOCOL.md)
- [Research lineage, source-specific connections and next experiments](RELATED_WORK.md)
- [Generated result tables](results/RESULTS.md)
- [Published research note](https://ajishpradeep.com/blog/a-valid-reconstruction-can-still-be-the-wrong-one/) · [Markdown source](NOTE.md)
- [Numerical checks](test_geometry.py)
- [Synthetic aggregates](results/synthetic/aggregates.csv)
- [OptiTrack aggregates](results/optitrack/aggregates.csv)

## Reproduce

Python 3.10+; CPU is sufficient. Exact versions used are recorded in each result manifest.

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest -v test_geometry.py
.venv/bin/python run.py --out results/synthetic --synthetic-n 512
```

The synthetic experiments and geometry checks are independently reproducible from this repository. The OptiTrack recordings, trajectories, original model weights and cached frame-level predictions are not distributed. Real-data aggregates are provided for scrutiny but cannot be independently regenerated without authorized access to those inputs. No claim of fully open real-data replication is made.

For authorized local reproduction:

```sh
python prepare_local.py --cohort-root /path/to/cohort_eval --out local/cohort_corrected.npz --stride 5
python run.py --data local/cohort_corrected.npz --out results/optitrack
python run.py --data local/cohort_corrected.npz --out results/optitrack_400 --steps 400
python oracle_control.py --data local/cohort_corrected.npz
python report.py
python verify_release.py
```

The adapter checks frame correspondence, root-relative conventions and undistorted projection before fitting. `local/` is ignored, and the runner exports only aggregates. The public results use arbitrary participant identifiers; no images, videos, identity map or joint trajectories are included.

The primary 200-step real-data result uses 7,082 chain observations: 1,668 from four development participants and 5,414 from three evaluation participants. Only evaluation participants contribute to the note's real-data headline table. Oracle-control and 400-step results are [post-pilot diagnostics](ADDENDUM.md). The release verifier checks equal denominators, finite metrics, hard-constraint compliance and the hashes of source files used by each run.

## Method

The two-link FK state has a free 3D root, two angles for the first segment, a bending-plane angle, and a bend angle. Segment lengths are fixed per chain. It therefore imposes length consistency but does not recover segment twist or define anatomical coordinate systems.

Refinement minimizes a 3D tether to the original prediction plus a weighted pixel residual. A soft geometric bend cap or sigmoid hard cap can be added. The units are metres internally, pixels for projection and radians for angles; reports use millimetres and degrees. The weights are engineering settings, not calibrated probabilities.

The real-data analysis gives every method the same known calibration and reference pelvis translation. Oracle lengths use target-participant reference data and are explicitly an upper-information diagnostic, not a deployable method. Generic lengths come from four development participants. No new network is trained or selected using the three evaluation participants. The cohort has been examined before, so this is exploratory rather than a pristine held-out study.

## Relation to prior work

This study explicitly engages with the research of **Eline van der Kruk, Ajay Seth and Xucong Zhang**, and the wider literature connecting visual estimation, anatomical correspondence and model uncertainty. The strongest precedent is Uchida and Seth's *Conclusion or Illusion* (2022), not a claim that constraints failing to identify truth is a new discovery. D3KE already estimates monocular biomechanical coordinates; Lin et al. use direct two-view image features, not the detector-keypoint refinement tested here. OpenCap Monocular already provides a substantially richer refinement-and-OpenSim pipeline.

The contribution here is a reproducible, bounded diagnostic and a documented reversal between synthetic and real-data rankings. [RELATED_WORK.md](RELATED_WORK.md) explains the relevant personalization, visual inference and uncertainty studies, their upstream methods, and the resulting experimental priorities. It separates actual methodological dependencies from our proposed connections. No cited system was reproduced or outperformed.

This project has no affiliation with or endorsement from the cited researchers or TU Delft. Zhang's current affiliation is Turku / ELLIS Institute Finland; the joint papers retain their historical Delft affiliations.

- Lin et al. (2024), [3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data](https://arxiv.org/abs/2402.13172).
- Uchida and Seth (2022), [Conclusion or Illusion](https://doi.org/10.3389/fbioe.2022.874725).
- Bittner et al. (2023), [Towards Single Camera Human 3D-Kinematics](https://arxiv.org/abs/2301.05435).
- Li et al. (2026), [Calibration-free IMU-based Relative Orientation Estimation under Dynamic Human Motion](https://arxiv.org/abs/2610.31156).
- Gozlan et al. (2025), [OpenCapBench](https://openaccess.thecvf.com/content/WACV2025/papers/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.pdf).
- [BODIES research programmes](https://bodieslab.com/projects/).
- Full source map, including BODIESReg, What the PCSA?, MuPPet, validation methodology and OpenCap Monocular: [research lineage](RELATED_WORK.md).

## Next validation

Real image occlusions with a rerun detector and lifter; public licensed video/reference data; camera and root estimation; independent marker-based segment frames; broader movements and participant morphology; patient-relevant endpoints; uncertainty and rejection policies. These are open tasks, not claims supported by the current tables.
