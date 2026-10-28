# Constraint validity versus reconstruction accuracy

Protocol written 2026-10-28 before executing the new ablation. Exploratory study: the historical cohort results and weaknesses were already inspected. This is not a preregistered independent test of a new trained network.

## Question

When does a constant-length articulated representation improve distal reconstruction, and when do incorrect lengths, angle bounds or observations produce plausible but incorrect results?

## Scope

Two-segment chains, initially shoulder–elbow–wrist. Three-dimensional positions and geometric bend angle only: the bend angle is not an ISB anatomical elbow rotation, and segment axial rotation cannot be recovered from three joint centres. This is a differentiable geometric model, not an OpenSim reproduction, musculoskeletal dynamics model, or clinical validation.

The real-data arm uses existing cached predictions and calibrated cameras. Removing proximal 2D observations does not occlude the original network input. Call this observation dropout, not image-occlusion robustness. A separate fully synthetic experiment controls both the initial pose error and observation corruption. Neither proves performance on home video or neurological patients.

## Samples and reference

Historical cohort: four development subjects, three subjects excluded from student-v2 training. Their results have already been inspected. Use both arms and both cameras, keep participant-level results, never count frames/cameras/arms as independent participants. Subsample every fifth cached row of each capture for optimization (approximately 6 Hz from the 30 Hz cache); do not make event-timing claims. Keep complete-case finite input/reference rows; report denominators and exclusions. No new training and no checkpoint selection.

The reference is the Motive fitted skeleton, not bone-pin truth. Lower limbs are excluded from this first study because a documented missing ankle marker compromises one subject's reference. An arm-only study does not establish lower-limb performance. Local source adapters remain separate from public code and data.

## Factors

Baselines: unchanged 3D prediction; root-outward length projection; differentiable fixed-length FK with no observation term; Cartesian refinement with a reprojection term; FK refinement with reprojection and no angle bounds; FK refinement with soft bounds; FK refinement with hard bounds.

All refinements share the same initial 3D prediction, pixel observations, camera, 3D tether strength, optimization steps and frames. Report results at 200 steps and a convergence sensitivity at 400 where necessary. A fixed optimization budget does not guarantee equal convergence.

Lengths: development-subject mean lengths (equal weight per person); oracle target-subject median reference lengths (diagnostic, unavailable to a deployed system); ±10% changes to oracle lengths. Bounds: 150° geometric bend cap as a declared illustrative setting, 90° deliberately mismatched stress test; neither is claimed to be a patient-specific physiological ROM. Soft penalty scale 10°; hard bound via sigmoid parameterization. No test-driven parameter tuning.

Pixel standard deviation 5 px; 3D tether standard deviation 80 mm; Adam 0.02, 200 iterations, float64 CPU. The tether is a regularizer, not a calibrated posterior. Detector confidence weighting is a heuristic, not an inverse-variance estimate. Both uniform and heuristic confidence weighting are compared. Known camera intrinsics/extrinsics and reference pelvis translation are privileged inputs; the study isolates articulated shape refinement and does not solve global monocular localization.

Synthetic arm: seeded random spatial orientations, translations, lengths and bend angles; no sinusoidal gait. Three seeds. Correlated proximal perturbation; visible distal 2D noise; proximal dropout; confidently wrong distal anchor; incorrect lengths; mismatched angle bounds. Control models share all random draws. Include an exact perspective depth-ambiguity counterexample.

## Metrics and reporting

Mean joint-position error, wrist-position error, wrist camera-depth error, geometric bend-angle error, visible-keypoint reprojection error, segment length error relative to reference, and deviation from the imposed segment lengths. Keep consistency and reference accuracy separate. Report differences versus baseline, participant-level paired values and macro means. With three evaluation participants, confidence intervals are fragile: publish each participant and range, not frame-bootstrap precision.

Numerical checks: FK/inverse parameterization round-trip; finite-difference/autograd Jacobian agreement; fixed-length invariance; perspective-ray ambiguity; hard-cap compliance; finite optimization and row correspondence. Hash protocol, inputs and source code. Save exact environment, configuration and machine-readable output. Fail loudly on nonfinite values. Figures come from saved outputs.

## Decision

Publish negative and positive results. Do not claim a new state-of-the-art estimator, improvement to Lin et al., calibrated uncertainty, clinical utility, or mobile performance from these experiments. A public-data/video benchmark and patient-diverse assessment remain subsequent validation, not completed work.

## Implementation audit

During the initial smoke run, a projection cross-check found that the cached detector inputs were already undistorted. The adapter now uses zero distortion and verifies all selected reference projections against cached pixel coordinates before fitting. The initial real-data run with double-applied distortion is invalid and is superseded by the corrected run. The no-ROM FK+reprojection control and explicit bound-compliance metrics were added after the first synthetic pilot to complete the factor isolation. All released tables are rerun with these corrections. This amendment is disclosed rather than claiming the protocol was unchanged.
