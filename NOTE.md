<!-- note: category=evaluation -->
# A valid reconstruction can still be the wrong one

```claim
In 5,414 real upper-limb observations, fixed-length forward kinematics reduced the image residual from 17.91 px to 1.36 px and enforced exact segment lengths, yet mean wrist error increased from 78.3 mm to 80.3 mm. Structure, image agreement and 3D accuracy must be measured separately.
```

A reconstructed arm can obey its prescribed lengths and land on the observed pixels while placing the wrist at the wrong depth. I tested that failure mode first in a matched synthetic mechanism check, then against synchronized monocular predictions and OptiTrack Motive references from high-speed upper-limb sports motion.

The synthetic solver behaves exactly as hoped: fixed-length refinement cuts distal error by more than half. The real-data ranking then reverses, and a diagnostic control reveals why. Replacing detected keypoints with reference-projected pixels halves wrist error, while nearly 4 cm of depth error remains. The experiment therefore separates two problems that are easy to blur together: correspondence in the image and identifiability along the camera ray.

## A constraint removes possibilities without identifying the truth

For a two-segment chain with root position $r$, segment lengths $l_1,l_2$, and unit directions $d_1,d_2$,

$$
p_1=r+l_1d_1,\qquad p_2=r+l_1d_1+l_2d_2.
$$

Forward kinematics guarantees the selected lengths. Reprojection measures agreement with the image. Reference error measures distance to an independently estimated 3D target. These quantities answer different questions, even when they move together.

The same distinction appears in marker-based inverse analysis. Uchida and Seth (2022) showed that small marker-fitting residuals can coexist with uncertainty introduced by marker registration and model scaling. Hicks et al. (2015) formalized the corresponding separation between software verification, experimental validation and sensitivity analysis. Here, exact geometric tests verify the implementation, the shared-generator simulation tests its mechanism, and the OptiTrack comparison measures its behaviour on real trajectories.

A proximal rotation also has a predictable distal effect. For revolute coordinate $q_k$, axis $a_k$ and origin $o_k$,

$$
\frac{\partial p_2}{\partial q_k}=a_k\times(p_2-o_k).
$$

The perpendicular distance from the axis to the downstream point sets the first-order displacement. Bittner et al. (2023) use this sensitivity to motivate positional supervision alongside coordinate regression in a monocular biomechanical estimator. The interactive view below makes the same geometry tangible: rotate at the shoulder and the longer moment arm carries the wrist farther than the elbow.

## A pixel leaves depth unresolved

Perspective projection maps $(X,Y,Z)$ to $(f_xX/Z+c_x,f_yY/Z+c_y)$. Every point on one camera ray shares the same pixel (Hartley and Zisserman, 2004). A known length narrows that ray, but may leave multiple valid intersections.

Take a root at $(0,0,3.0)$ m, a segment of length $0.5$ m, and a distal point on the ray $(0.1z,0,z)$. The length equation is

$$
1.01z^2-6z+8.75=0.
$$

Its positive roots are $z_1=2.571$ m and $z_2=3.369$ m. Both produce 0.0 mm length violation and 0.0 px image residual, while the resulting 3D points lie 798 mm apart. A numerical test in the repository evaluates both roots directly.

The lever-arm interaction sweeps a proximal perturbation from $-12^\circ$ to $+12^\circ$. The range is illustrative; the depth-root construction is exact.

```figure
{
  "type": "kinematic-ambiguity",
  "title": "One pixel, two valid 3D reconstructions",
  "caption": "The paired views connect the camera measurement to the two solutions that remain in depth; the lever-arm view shows how proximal angular error propagates downstream.",
  "rootDepth": "3.0 m",
  "segmentLength": "0.5 m",
  "raySlope": "0.1",
  "roots": ["2.571 m", "3.369 m"],
  "separation": "798 mm",
  "angleRange": ["-12°", "+12°"]
}
```

## Matched synthetic assumptions reward the articulated model

The diagnostic model has a free root, two angles for the first segment, a bending-plane angle and a bend angle. Every condition starts from the same 3D prediction and uses the same pixel observations and optimization budget.

The four core conditions are the initial prediction, root-outward length projection, Cartesian pixel refinement, and fixed-length forward kinematics with pixels. Soft and hard bend bounds provide additional sensitivity checks. Refinement minimizes

$$
\mathcal L=\sum_j\frac{\|p_j-p_j^0\|^2}{(0.08\,\mathrm m)^2}
+\sum_j w_j\frac{\|\pi_K(p_j)-u_j\|^2}{(5\,\mathrm{px})^2}
+\mathcal L_{\mathrm{bound}}.
$$

Here $p_j^0$ is the initial prediction, $u_j$ the observed pixel, $K$ the camera calibration, and $w_j$ a heuristic observation weight. The 0.08 m and 5 px scales define the engineering trade-off between staying near the initial pose and agreeing with the image.

The synthetic benchmark contains 1,536 chains: 512 samples for each of three seeds, spanning random orientations, translations, lengths and bends. Correlated angular and coordinate perturbations corrupt the initial 3D predictions, and Gaussian noise perturbs the pixels.

With oracle lengths and weighted observations, mean distal error changes from 101.5 mm initially to 102.5 mm after length projection, 53.1 mm after Cartesian refinement, and 43.5 mm after fixed-length FK. A deliberately restrictive $90^\circ$ hard bend cap raises FK error to 68.8 mm. This stress condition places valid generated poses outside the permitted interval and exposes the cost of a misspecified hard boundary.

The generator and solver share the same chain geometry, so this experiment answers a focused question: can the implementation exploit correct structure under matched assumptions? The answer is yes.

## Real observations reverse the ranking

The real-data audit evaluates P01, P05 and P07, all held out from the 3D predictor's training. Together they contribute 5,414 shoulder–elbow–wrist chains across both arms and two camera views: 2,586 from P01, 1,480 from P05 and 1,348 from P07.

The primary condition gives each solver participant-specific reference-derived lengths, calibrated cameras, reference pelvis translation and confidence-weighted detected pixels. These diagnostic inputs isolate the behaviour of the chain and reprojection objective from global localization. Results are macro means of the three participant means after 200 optimization steps.

| Method | Wrist 3D error, mm | Wrist depth error, mm | Image residual, px | Length deviation, mm |
|---|---:|---:|---:|---:|
| Initial prediction | 78.3 | 49.6 | 17.91 | 18.83 |
| Root-outward length projection | 83.2 | 47.1 | 19.10 | 0.00 |
| Cartesian refinement with pixels | 76.2 | 48.3 | 0.37 | 24.73 |
| Fixed-length FK with pixels | 80.3 | 53.1 | 1.36 | 0.00 |
| FK with a soft $150^\circ$ cap | 80.3 | 53.1 | 1.36 | 0.00 |
| FK with a hard $150^\circ$ cap | 80.0 | 52.8 | 1.39 | 0.00 |

The length column makes the trade-off visible. Cartesian refinement achieves the lowest wrist and image errors in the macro mean, while increasing segment-length distortion to 24.73 mm. Fixed-length FK removes that distortion and reduces image residual to 1.36 px, but moves wrist error from 78.3 mm to 80.3 mm and depth error from 49.6 mm to 53.1 mm.

The $150^\circ$ real-data cap is a permissive condition, unlike the deliberately restrictive $90^\circ$ synthetic stress test. Its soft and hard variants barely change the output, showing that this boundary contributes little under the recorded upper-limb condition. The important competition is between image correspondence, the proximity tether and depth ambiguity.

## Participant outcomes disagree with the aggregate

The macro mean combines three qualitatively different outcomes.

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
  "title": "The same constraint produces different participant outcomes",
  "caption": "Select a cohort for absolute errors. Each matrix cell shows change from that cohort's initial wrist 3D error; lower is better.",
  "methods": ["Initial", "Length projection", "Cartesian pixels", "Fixed-length FK"],
  "cohorts": [
    {"label": "Synthetic", "sample": "1,536 chains", "note": "Matched generator and solver assumptions strongly favour the articulated model.", "values": ["101.5 mm", "102.5 mm", "53.1 mm", "43.5 mm"]},
    {"label": "Real mean", "sample": "5,414 chains; macro mean", "note": "Real observations reverse the synthetic advantage of fixed-length FK.", "values": ["78.3 mm", "83.2 mm", "76.2 mm", "80.3 mm"]},
    {"label": "P01", "sample": "2,586 chains", "note": "Both pixel-based refinements improve the initial wrist estimate.", "values": ["78.3 mm", "77.7 mm", "65.2 mm", "71.7 mm"]},
    {"label": "P05", "sample": "1,480 chains", "note": "Every structural correction shown here increases wrist error.", "values": ["77.8 mm", "87.8 mm", "83.7 mm", "92.5 mm"]},
    {"label": "P07", "sample": "1,348 chains", "note": "Fixed-length FK helps slightly; Cartesian refinement is nearly neutral.", "values": ["78.9 mm", "84.0 mm", "79.6 mm", "76.8 mm"]}
  ]
}
```

P01 improves under both pixel-based refinements. P05 moves in the opposite direction, with FK increasing wrist error by 14.7 mm. P07 changes little, although FK produces a small improvement. The participant, rather than the repeated chain observation, is therefore the meaningful evaluation unit.

## Better correspondence halves the error; depth remains

The post-pilot control replaces detected pixels with projections of the reference skeleton. At 400 steps, no-cap FK produces 80.4 mm mean wrist error with detected pixels and 39.3 mm with reference-projected pixels. Depth error falls from 53.2 mm to 38.5 mm.

This is the sharpest result in the audit. Roughly half the wrist error disappears when the downstream solver receives pixels defined by the reference skeleton, locating a major source of failure in observation and landmark correspondence. The remaining 38.5 mm depth error shows what exact 2D correspondence and fixed lengths still leave unresolved under the single-frame proximity objective.

The control changes detector localization and landmark definition together. Lin et al. (2024) address correspondence through direct image-feature inference, biomechanical coordinates and synthetic anatomical supervision. OpenCapBench and SynthPose (Gozlan et al., 2025) learn denser, anatomy-oriented landmarks for downstream biomechanics. These approaches add information at the observation boundary rather than asking a length constraint to repair an ambiguous measurement.

Doubling the optimization budget from 200 to 400 steps shifts participant-level wrist error by less than 0.5 mm across the full-observation methods. Within this tested budget, additional iterations leave the depth residual essentially unchanged and point the next experiment toward observations, model correspondence and temporal information.

## The next step is to add information, not only constraints

Three consequences follow from the synthetic-to-real reversal.

- **Personalization must include anatomical correspondence.** Surface shape, segment length and internal joint centres are related but distinct quantities. BODIESReg (Chaurasia et al., 2026) makes surface registration and anatomical landmark estimation explicit stages of personalization. A useful uncertainty model must propagate that mapping into the kinematic estimate instead of treating a fitted surface or length as exact anatomy.
- **Observability depends on motion and viewpoint.** Li et al. (2026) show in calibration-free inertial estimation that different motion excitations identify relative orientation and sensor location. The visual counterpart is to measure which movement phases and camera viewpoints separate competing depth solutions, then use those intervals deliberately.
- **Richer evidence can be more valuable than a tighter bound.** Dense anatomical landmarks in OpenCapBench, temporal and contact objectives in OpenCap Monocular (Gilon et al., 2026), and multi-frame image evidence all supply measurements that a single-frame length constraint lacks.

The downstream outcome matters as much as joint-point error. Van der Kruk et al. (2022) found distinct compensatory strategies in sit-to-walk movement. A clinical estimator should preserve such functional variation while improving accuracy, rather than scoring success by how closely motion follows a population template.

The next experiment will therefore rerun the image estimator under visible occlusion, compare sparse detector joints with anatomy-aware landmark definitions, perturb camera and joint-centre geometry separately, and propagate each uncertainty source into a prespecified movement measure. Participant splits and evaluation outcomes will be fixed before comparison.

## Scope and release

The public repository contains the synthetic generator, exact-root tests, optimization code, aggregate real-data tables, protocol amendments and an adapter for authorized local replication. Raw recordings, participant trajectories and original model weights remain local. Motive's fitted skeleton supplies the 3D reference, the real evaluation contains three participants, and the solver receives known cameras plus reference pelvis translation. Observation-dropout conditions alter the post-hoc objective while keeping the upstream prediction fixed. These choices define the audit as a diagnostic of this pipeline rather than an end-to-end monocular benchmark.

The [code, tables and protocol history](https://github.com/Ajishpradeep/kinematic-observability) make the central rule auditable: report the structure a reconstruction satisfies, the observations it agrees with, and its error against an independent reference as three separate measurements.

## References

- Multiple View Geometry in Computer Vision, Second Edition — Richard Hartley and Andrew Zisserman, Cambridge University Press 2004 — https://www.robots.ox.ac.uk/~vgg/hzbook/
- Conclusion or Illusion: Quantifying Uncertainty in Inverse Analyses From Marker-Based Motion Capture due to Errors in Marker Registration and Model Scaling — T. K. Uchida and Ajay Seth, Frontiers in Bioengineering and Biotechnology 2022 — https://doi.org/10.3389/fbioe.2022.874725
- Is My Model Good Enough? Best Practices for Verification and Validation of Musculoskeletal Models and Simulations of Movement — Jennifer L. Hicks, Thomas K. Uchida, Ajay Seth, Apoorva Rajagopal and Scott L. Delp, Journal of Biomechanical Engineering 2015 — https://doi.org/10.1115/1.4029304
- Towards Single Camera Human 3D-Kinematics — Marian Bittner, Wei-Tse Yang, Xucong Zhang, Ajay Seth, Jan van Gemert and Frans C. T. van der Helm, Sensors 2023 — https://doi.org/10.3390/s23010341
- 3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data — Zhi-Yi Lin, Bofan Lyu, Judith Cueto Fernandez, Eline van der Kruk, Ajay Seth and Xucong Zhang, arXiv 2024 — https://arxiv.org/abs/2402.13172
- OpenCapBench: A Benchmark to Bridge Pose Estimation and Biomechanics — Yoni Gozlan, Antoine Falisse, Scott D. Uhlrich, Anthony Gatti, Michael J. Black, Jennifer L. Hicks, Scott L. Delp and Akshay S. Chaudhari, WACV 2025 — https://openaccess.thecvf.com/content/WACV2025/html/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.html
- OpenCap Monocular: Exploring monocular video for estimating 3D human movement dynamics — Selim Gilon, Emily Y. Miller and Scott D. Uhlrich, arXiv 2026 — https://arxiv.org/abs/2603.24733
- BODIESReg: An Open-Source Pipeline for Registering 3D Body Scans Using Pose-Aligned Initialization — Vikash Chaurasia, Judit Cueto Fernandez, J. Micah Prendergast and Eline van der Kruk, arXiv 2026 — https://arxiv.org/abs/2607.15463
- Calibration-free IMU-based Relative Orientation Estimation under Dynamic Human Motion — Ruiyuan Li, Hassan Osman, Ajay Seth and Manon Kok, arXiv 2026 — https://arxiv.org/abs/2610.31156
- Why do older adults stand-up differently to young adults? Investigation of compensatory movement strategies in sit-to-walk — Eline van der Kruk, Paul Strutton, Louis J. Koizia, Michael Fertleman, Peter Reilly and Anthony M. J. Bull, npj Aging 2022 — https://doi.org/10.1038/s41514-022-00094-x
