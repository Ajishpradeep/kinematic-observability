<!-- note: category=evaluation -->
# A valid reconstruction can still be the wrong one

```claim
In 5,414 real upper-limb observations, fixed-length forward kinematics reduced the image residual to 1.36 px yet increased mean wrist error from 78.3 mm to 80.3 mm. Constraint satisfaction, image agreement and 3D accuracy are different measurements.
```

A reconstructed arm can keep its prescribed lengths and land on the observed pixels while still placing the wrist at the wrong depth. I tested that failure mode twice: first as a controlled synthetic mechanism check, then against 5,414 shoulder–elbow–wrist observations from high-speed sports motion with synchronized OptiTrack Motive references.

The result is deliberately mixed. Fixed-length refinement helped the synthetic cases and one real participant, hurt another, and changed little for the third. The useful finding is not that constraints are good or bad. It is that anatomical validity and image agreement do not identify 3D accuracy on their own.

## Three questions that should not share one score

For a two-segment chain with root position $r$, segment lengths $l_1,l_2$, and unit directions $d_1,d_2$,

$$
p_1=r+l_1d_1,\qquad p_2=r+l_1d_1+l_2d_2.
$$

Forward kinematics answers a structural question: does this configuration obey the selected model? A reprojection residual answers an observational question: does it agree with the image? A reference error answers an accuracy question: is it near an independently estimated 3D target?

Those questions can correlate, but they are not interchangeable. Uchida and Seth (2022) demonstrated the analogous warning for marker-based inverse analyses: low marker-tracking error can coexist with uncertainty introduced by marker registration and model scaling. Hicks et al. (2015) separate code verification, experimental validation and sensitivity analysis for the same reason. In this study, exact geometric tests are verification; the shared-generator simulation is a mechanism check; and the OptiTrack comparison is a small, model-dependent validation exercise.

## One pixel can admit two exact depths

Under perspective projection, $(X,Y,Z)$ maps to $(f_xX/Z+c_x,f_yY/Z+c_y)$. Depth along a camera ray is therefore unobserved unless another measurement or prior constrains it (Hartley and Zisserman, 2004).

Take a known root at $(0,0,3.0)$ m, a segment of length $0.5$ m, and a distal point on the ray $(0.1z,0,z)$. The length equation becomes

$$
1.01z^2-6z+8.75=0.
$$

Its two positive roots are $z_1=2.571$ m and $z_2=3.369$ m. Both give 0.0 mm length violation and 0.0 px image residual, yet the resulting 3D points are 798 mm apart. The repository test evaluates both roots numerically.

A proximal angle error has a second, related consequence. For revolute coordinate $q_k$, axis $a_k$ and origin $o_k$,

$$
\frac{\partial p_2}{\partial q_k}=a_k\times(p_2-o_k).
$$

The perpendicular distance from the axis to the downstream point sets the first-order displacement. Bittner et al. (2023) use this positional sensitivity in a monocular biomechanical estimator; it is the reason that their differentiable skeleton receives positional as well as coordinate supervision. The interactive lever-arm view below sweeps an illustrative proximal perturbation from $-12^\circ$ to $+12^\circ$. It shows sensitivity, not an empirical error distribution.

```figure
{
  "type": "kinematic-ambiguity",
  "title": "One pixel, two valid 3D reconstructions",
  "caption": "The depth view is an exact counterexample. The lever-arm view isolates how proximal angular error moves a distal point.",
  "rootDepth": "3.0 m",
  "segmentLength": "0.5 m",
  "raySlope": "0.1",
  "roots": ["2.571 m", "3.369 m"],
  "separation": "798 mm",
  "angleRange": ["-12°", "+12°"]
}
```

## What I compared

The diagnostic model has a free root, two angles for the first segment, a bending-plane angle and a bend angle. Every refinement starts from the same 3D prediction and receives the same observation weights and optimization budget.

I compare four core conditions:

1. **Initial prediction:** the cached 3D pose without refinement.
2. **Root-outward length projection:** each segment is rescaled along its predicted direction.
3. **Cartesian pixel refinement:** joint coordinates move directly under a 3D tether and reprojection objective.
4. **Fixed-length FK with pixels:** joint coordinates are generated from the articulated parameters and fixed lengths.

The refinement objective is

$$
\mathcal L=\sum_j\frac{\|p_j-p_j^0\|^2}{(0.08\,\mathrm m)^2}
+\sum_j w_j\frac{\|\pi_K(p_j)-u_j\|^2}{(5\,\mathrm{px})^2}
+\mathcal L_{\mathrm{bound}}.
$$

Here $p_j^0$ is the initial prediction, $u_j$ an observed pixel, $K$ the known camera calibration, and $w_j$ a heuristic confidence weight. The 0.08 m and 5 px scales are engineering settings, not fitted uncertainties. Soft and hard bend caps are additional sensitivity conditions; the core comparison below uses the no-cap FK result unless stated otherwise.

## The synthetic mechanism works

The synthetic experiment samples random chain orientations, translations, lengths and bends. It contains 1,536 cases: 512 samples for each of three seeds. The initial predictions receive correlated angular perturbations and coordinate noise, while image observations receive pixel noise.

With oracle lengths and weighted observations, mean distal error changes from 101.5 mm initially to 102.5 mm after length projection, 53.1 mm after Cartesian pixel refinement, and 43.5 mm after fixed-length FK refinement. A deliberately restrictive $90^\circ$ hard bend cap raises the FK result to 68.8 mm. That stress condition demonstrates sensitivity to a wrong bound; it is not a physiological claim.

The important limitation is built into the experiment: the generator and solver share the same chain geometry. This establishes that the implementation can recover from its injected perturbations under matched assumptions. It does not establish transfer to real anatomy or images.

## Real data reverses the ranking

The real-data audit uses synchronized monocular predictions and Motive fitted-skeleton references. Four people provide generic segment lengths; P01, P05 and P07 are held out from the 3D predictor's training and provide 5,414 evaluation chains across both arms and both cameras. The participant counts are 2,586 for P01, 1,480 for P05 and 1,348 for P07.

The primary table uses participant-specific reference-derived lengths, known camera calibration, reference pelvis translation, confidence-weighted detected pixels and 200 optimization steps. These are privileged diagnostic inputs. Values are means of the three participant means, so a participant with more retained chains does not dominate the aggregate.

| Method | Wrist 3D error, mm | Wrist depth error, mm | Image residual, px | Length deviation, mm |
|---|---:|---:|---:|---:|
| Initial prediction | 78.3 | 49.6 | 17.91 | 18.83 |
| Root-outward length projection | 83.2 | 47.1 | 19.10 | 0.00 |
| Cartesian pixel refinement | 76.2 | 48.3 | 0.37 | 24.73 |
| Fixed-length FK with pixels | 80.3 | 53.1 | 1.36 | 0.00 |

The coordinate refinement obtains the smallest image residual and slightly improves wrist error, but violates the selected lengths. FK satisfies those lengths to numerical precision and reaches a 1.36 px residual, but its 80.3 mm wrist error is worse than the 78.3 mm starting point. The result is not a paradox: the optimized quantities are not independent 3D truth measurements.

## The mean hides three different outcomes

The participant-level wrist results expose the instability of any universal conclusion.

| Cohort | Initial, mm | Length projection, mm | Cartesian pixels, mm | Fixed-length FK, mm |
|---|---:|---:|---:|---:|
| Synthetic, 1,536 chains | 101.5 | 102.5 | 53.1 | 43.5 |
| Real macro mean, 5,414 chains | 78.3 | 83.2 | 76.2 | 80.3 |
| P01, 2,586 chains | 78.3 | 77.7 | 65.2 | 71.7 |
| P05, 1,480 chains | 77.8 | 87.8 | 83.7 | 92.5 |
| P07, 1,348 chains | 78.9 | 84.0 | 79.6 | 76.8 |

```figure
{
  "type": "result-explorer",
  "title": "The aggregate result is not the participant result",
  "caption": "Switch cohorts to compare the same four methods. Bars encode wrist 3D error; lower is better.",
  "methods": ["Initial", "Length projection", "Cartesian pixels", "Fixed-length FK"],
  "cohorts": [
    {"label": "Synthetic", "sample": "1,536 chains", "note": "Matched generator and solver assumptions favour the articulated model.", "values": ["101.5 mm", "102.5 mm", "53.1 mm", "43.5 mm"]},
    {"label": "Real mean", "sample": "5,414 chains; macro mean", "note": "The synthetic ranking does not survive the move to real observations and references.", "values": ["78.3 mm", "83.2 mm", "76.2 mm", "80.3 mm"]},
    {"label": "P01", "sample": "2,586 chains", "note": "Both pixel-based refinements improve on the initial wrist estimate.", "values": ["78.3 mm", "77.7 mm", "65.2 mm", "71.7 mm"]},
    {"label": "P05", "sample": "1,480 chains", "note": "Every structural correction shown here increases wrist error.", "values": ["77.8 mm", "87.8 mm", "83.7 mm", "92.5 mm"]},
    {"label": "P07", "sample": "1,348 chains", "note": "Fixed-length FK helps slightly while Cartesian refinement does not.", "values": ["78.9 mm", "84.0 mm", "79.6 mm", "76.8 mm"]}
  ]
}
```

The participant switcher is not a significance analysis. Each row summarizes repeated chains from one person, and the three people are the independent evaluation units. It is a guard against letting one macro average imply consistent behaviour.

## Better correspondences change the answer

I added one post-pilot diagnostic control: replace detected pixels with projections of the reference skeleton itself. This uses information unavailable to a deployed estimator, but it separates the effect of the downstream optimizer from some of the upstream correspondence error.

At 400 steps, no-cap FK produces 80.4 mm mean wrist error with detected pixels and 39.3 mm with reference-projected pixels. Depth error changes from 53.2 mm to 38.5 mm. Better correspondence therefore changes the result materially, although it still does not eliminate monocular depth error.

This control changes both detector localization and the definition of the observed landmark. It cannot attribute the gap to either one alone. Lin et al. (2024) avoid an explicit sparse-keypoint bottleneck by regressing biomechanical coordinates and scales from two-view image features with synthetic anatomical supervision. OpenCapBench and SynthPose (Gozlan et al., 2025) instead make denser, anatomically motivated landmarks available for downstream biomechanics. These are different strategies for adding information; neither result licenses treating a low reprojection residual as ground truth.

OpenCap Monocular (Gilon et al., 2026) is an especially relevant comparator because it combines monocular initialization, confidence-weighted reprojection, additional motion and contact objectives, virtual markers and OpenSim inverse kinematics. This audit does not evaluate that complete system. It isolates a smaller question: when a fixed-length chain agrees with selected pixels, what has actually been established?

## What the next experiment must identify

The next experiment should vary information, not merely add a stronger penalty.

- Rerun the image estimator under controlled, visible occlusions instead of dropping observations after inference.
- Compare detected joints, anatomy-aware virtual landmarks and reference projections under the same downstream estimator.
- Perturb camera parameters, joint-centre definitions and segment geometry separately, then jointly.
- Report anatomical coordinate error and a prespecified movement outcome alongside point error.
- Predefine participant splits and treat participants, not frames, as the evaluation units.

A local Jacobian can reveal weakly observed directions, but it cannot by itself find disconnected alternatives such as the two exact depth roots above. Uncertainty analysis needs both local conditioning and tests for competing solutions.

## Scope and reproducibility

The public repository contains the synthetic generator, optimization code, exact-root tests, aggregate real-data tables, protocol amendments and an adapter for authorized local replication. Raw recordings, participant trajectories and original model weights remain local.

The real-data reference is Motive's fitted skeleton rather than direct bone motion. The study uses three evaluation participants, a previously inspected cohort, a known camera and reference pelvis translation. Observation-dropout conditions keep the original 3D prediction fixed. These boundaries limit the claim to a diagnostic audit of this pipeline and dataset.

The [code, full tables and protocol history](https://github.com/Ajishpradeep/kinematic-observability) are public. The main conclusion is simple to audit: report what a reconstruction satisfies, what it agrees with, and how far it is from an independent reference as three separate quantities.

## References

- Multiple View Geometry in Computer Vision, Second Edition — Richard Hartley and Andrew Zisserman, Cambridge University Press 2004 — https://www.robots.ox.ac.uk/~vgg/hzbook/
- Conclusion or Illusion: Quantifying Uncertainty in Inverse Analyses From Marker-Based Motion Capture due to Errors in Marker Registration and Model Scaling — T. K. Uchida and Ajay Seth, Frontiers in Bioengineering and Biotechnology 2022 — https://doi.org/10.3389/fbioe.2022.874725
- Is My Model Good Enough? Best Practices for Verification and Validation of Musculoskeletal Models and Simulations of Movement — Jennifer L. Hicks, Thomas K. Uchida, Ajay Seth, Apoorva Rajagopal and Scott L. Delp, Journal of Biomechanical Engineering 2015 — https://doi.org/10.1115/1.4029304
- Towards Single Camera Human 3D-Kinematics — Marian Bittner, Wei-Tse Yang, Xucong Zhang, Ajay Seth, Jan van Gemert and Frans C. T. van der Helm, Sensors 2023 — https://doi.org/10.3390/s23010341
- 3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data — Zhi-Yi Lin, Bofan Lyu, Judith Cueto Fernandez, Eline van der Kruk, Ajay Seth and Xucong Zhang, arXiv 2024 — https://arxiv.org/abs/2402.13172
- OpenCapBench: A Benchmark to Bridge Pose Estimation and Biomechanics — Yoni Gozlan, Antoine Falisse, Scott D. Uhlrich, Anthony Gatti, Michael J. Black, Jennifer L. Hicks, Scott L. Delp and Akshay S. Chaudhari, WACV 2025 — https://openaccess.thecvf.com/content/WACV2025/html/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.html
- OpenCap Monocular: Exploring monocular video for estimating 3D human movement dynamics — Selim Gilon, Emily Y. Miller and Scott D. Uhlrich, arXiv 2026 — https://arxiv.org/abs/2603.24733
