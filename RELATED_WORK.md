# Research lineage and the question this study can answer

Ajish Pradeep · literature audit, revised 29 October 2026

This study asks whether structural consistency and image agreement predict reconstruction accuracy when observations or body geometry are imperfect. It is a focused diagnostic, not a reproduction of the systems below or a general validation of monocular biomechanics.

## Small residuals do not settle an inverse problem

Uchida and Seth's [*Conclusion or Illusion*](https://doi.org/10.3389/fbioe.2022.874725) varies marker registration and model scaling in OpenSim and finds materially different kinematics and kinetics despite low tracking errors. That is the closest conceptual precedent for separating fit from truth. The present study asks a narrower version of the question with monocular pixels, a two-link chain and cached upper-limb predictions.

Hicks et al.'s [verification and validation guidance](https://doi.org/10.1115/1.4029304) also matters here. Exact geometry tests verify the implementation; a synthetic generator that shares the solver's geometry checks a mechanism; comparison with a fitted-skeleton reference tests a limited real-data condition. Those are different forms of evidence.

## Published estimators use more information than this diagnostic

[D3KE](https://arxiv.org/abs/2301.05435) predicts biomechanical coordinates and segment scales from monocular images and uses a differentiable skeletal layer for positional supervision. [Lin et al. (2024)](https://arxiv.org/html/2402.13172v4) use calibrated two-view image features, temporal refinement, synthetic anatomical supervision and forward-kinematic positions. Neither is the detector-keypoint refinement evaluated here, so their reported errors cannot be compared directly with this study's wrist errors.

[OpenCap Monocular](https://arxiv.org/html/2603.24733v1) begins from a temporal image model, refines with confidence-weighted reprojection and other objectives, constructs virtual markers and then runs OpenSim inverse kinematics. Known height, camera assumptions and contact information contribute to the estimate. It is a useful comparator only after those inputs and outputs are matched.

## Correspondence is part of the measurement

[BODIESReg](https://arxiv.org/html/2607.15463v1) distinguishes body-surface registration, model-regressed joint centres and anatomically defined segment measurements. [OpenCapBench and SynthPose](https://openaccess.thecvf.com/content/WACV2025/html/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.html) make denser anatomy-oriented landmarks and downstream biomechanical evaluation concrete.

These works motivate a direct next test: hold the downstream model fixed while comparing detected joints, anatomy-oriented landmarks and reference projections. Dense landmarks are not automatically independent or correct; their definition, correlation and anatomical correspondence still need measurement.

## What should be tested next

1. Rerun the detector and lifter under real image occlusions, including matched non-occluded controls. The current dropout conditions only change a post-hoc objective.
2. Match information before comparing systems: camera calibration, height, temporal context, contact assumptions, anatomy inputs and target outputs.
3. Perturb camera parameters, landmark correspondence and joint-centre geometry separately and jointly. Report their effects on a prespecified movement measure as well as wrist position.
4. Fix participant splits and evaluation measures before comparison, then report participant-level effects. Three evaluation participants support an exploratory diagnostic, not a population claim.

The current result supports one operational rule: report the constraints a reconstruction satisfies, the observations it agrees with and its error against an independent reference as separate quantities.
