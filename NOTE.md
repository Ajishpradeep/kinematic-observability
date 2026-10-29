<!-- note: category=evaluation -->
# A valid reconstruction can still be the wrong one

```claim
Fixed segment lengths and a small image residual do not establish 3D accuracy. In a three-participant audit, articulated refinement reduced the image residual while increasing mean wrist error; replacing detected pixels with reference projections changed the result substantially.
```

A reconstructed limb can keep the prescribed segment lengths, fit the image closely, and still place its endpoint at the wrong 3D position. Those properties need to be measured separately before anatomical consistency is treated as evidence that a pose estimate has improved.

Recent video-based biomechanical estimators combine image features, temporal context, musculoskeletal coordinates and synthetic anatomical supervision. Lin et al. (2024), for example, regress OpenSim coordinates and segment scales from two calibrated views without an explicit 2D-joint bottleneck. I built a smaller keypoint-based monocular diagnostic to isolate how observation quality, model geometry and kinematic constraints interact.

The identifiability problem has a direct parallel in marker-based biomechanics. Uchida and Seth (2022) showed that small marker-fitting residuals can conceal uncertainty from marker registration and model scaling. Here I test the analogous failure mode for monocular image residuals and fixed-length forward kinematics.

## A constraint removes possibilities without identifying the truth

Consider a two-segment chain with root position $r$, segment lengths $l_1,l_2$, and unit directions $d_1,d_2$. Its middle and distal points are

$$
p_1=r+l_1d_1,\qquad p_2=r+l_1d_1+l_2d_2.
$$

These equations enforce the selected lengths by construction, regardless of whether the lengths describe the individual or the directions are correct. The bend angle is $\arccos(d_1^\top d_2)$. Bounding it restricts the geometric chain, while axial segment twist and the anatomical joint coordinate system remain outside this two-link model.

Sensitivity to a proximal rotation is equally structured. For a revolute coordinate $q_k$ with unit axis $a_k$ and axis origin $o_k$, the Jacobian column of a downstream point is

$$
\frac{\partial p_2}{\partial q_k}=a_k\times(p_2-o_k).
$$

First-order displacement scales with the perpendicular lever arm to the proximal axis. A small shoulder-angle error can therefore move the wrist by several centimetres. Bittner et al. (2023) use this relationship in D3KE to motivate positional supervision alongside biomechanical-coordinate regression. In practice, the comparison between an articulated estimator and a Cartesian predictor depends on the angular errors of the former and the coordinate noise of the latter.

## A pixel leaves a direction unmeasured

Perspective projection maps $(X,Y,Z)$ to $(f_xX/Z+c_x,f_yY/Z+c_y)$. Every point on a camera ray projects to the same pixel, and fixing segment length can narrow that ray to several intersections rather than a unique point.

Take a known root at $(0,0,3.0)$ m and a segment of length $0.5$ m. A distal point on the ray $(0.1z,0,z)$ must satisfy

$$
1.01z^2-6z+8.75=0.
$$

The two positive roots are $z_1=2.571$ m and $z_2=3.369$ m. Both produce 0.0 mm segment-length violation and 0.0 px reprojection residual, while their 3D positions are 798 mm apart. The repository includes a numerical test for both invariants. This ambiguity is geometric; network capacity and optimizer quality do not remove it.

## What the experiment changes

The diagnostic parameterizes a free root, two spherical angles for the proximal segment, a bending-plane angle and an inter-segment bend angle. The initial 3D pose, observed pixels and optimization budget remain fixed while I compare the initial prediction, root-outward length correction, Cartesian pixel refinement and fixed-length forward-kinematic refinement with no cap, a soft boundary penalty or a hard sigmoid bound.

Refinement minimizes a 3D proximity term and a confidence-weighted pixel residual:

$$
\mathcal L=\sum_j\frac{\|p_j-p_j^0\|^2}{(0.08\,\mathrm m)^2}
+\sum_j w_j\frac{\|\pi_K(p_j)-u_j\|^2}{(5\,\mathrm{px})^2}
+\mathcal L_{\mathrm{bound}}.
$$

Here $p_j^0$ is the initial prediction, $u_j$ the observed pixel, $K$ the calibrated camera matrix and $w_j$ the observation weight. The constants $0.08$ m and $5$ px define the engineering trade-off between staying near the initial pose and agreeing with the image. Setting $w_j=0$ removes a pixel term during refinement while leaving the upstream 3D prediction unchanged.

The synthetic mechanism check contains 1,536 chains: 512 samples for each of three seeds across random orientations, translations, lengths and bend angles. Correlated angular and coordinate perturbations corrupt the initial 3D predictions, and Gaussian noise perturbs the image observations.

With true lengths and complete observations, fixed-length refinement reduces mean distal error from 101.5 mm to 43.5 mm. Cartesian refinement reaches 53.1 mm, while root-outward length correction reaches 102.5 mm. A deliberately restrictive $90^\circ$ hard cap raises the FK result to 68.8 mm by forcing generated poses outside the permitted interval. Under matched generator and solver geometry, the articulated model performs as intended.

## The real-data result does not follow the synthetic ranking

The real-data audit evaluates cached monocular predictions against synchronized OptiTrack Motive skeleton trajectories from high-speed upper-limb sports motion. P01, P05 and P07 were held out from the 3D predictor's training and contribute 5,414 shoulder–elbow–wrist observations across both arms and two camera views: 2,586 from P01, 1,480 from P05 and 1,348 from P07.

The primary condition supplies participant-specific reference lengths, calibrated cameras, reference pelvis translations and confidence-weighted detected pixels. This isolates kinematic and reprojection behaviour from global localization. The values below are means of the three participant means after 200 optimization steps.

| Method | Wrist 3D error, mm | Wrist depth error, mm | Image residual, px | Length deviation, mm |
|---|---:|---:|---:|---:|
| Initial prediction | 78.3 | 49.6 | 17.91 | 18.83 |
| Root-outward length correction | 83.2 | 47.1 | 19.10 | 0.00 |
| Cartesian refinement with pixels | 76.2 | 48.3 | 0.37 | 24.73 |
| Fixed-length FK with pixels | 80.3 | 53.1 | 1.36 | 0.00 |
| FK with a soft $150^\circ$ cap | 80.3 | 53.1 | 1.36 | 0.00 |
| FK with a hard $150^\circ$ cap | 80.0 | 52.8 | 1.39 | 0.00 |

The Cartesian solver obtains the smallest image residual and the lowest macro-averaged wrist error, but increases segment-length distortion to 24.73 mm. Fixed-length FK removes that distortion and reduces the image residual from 17.91 px to 1.36 px, yet wrist error rises from 78.3 mm to 80.3 mm and depth error rises from 49.6 mm to 53.1 mm.

The permissive $150^\circ$ cap contributes little under these recorded motions: soft, hard and uncapped FK differ by less than 0.3 mm in wrist error. The $90^\circ$ synthetic cap serves a different purpose, deliberately activating a misspecified boundary to measure its effect.

Participant means reveal the instability behind the aggregate. Uncapped FK improves P01 from 78.3 mm to 71.7 mm and P07 from 78.9 mm to 76.8 mm, while P05 degrades from 77.8 mm to 92.5 mm. One geometric prior therefore produces participant-specific gains and failures even though every reconstructed chain satisfies the same length equations.

## Better observations change the answer

I added a post-pilot control that replaces detected keypoints with the 2D projections of the Motive reference skeleton. At 400 steps, this substitution reduces uncapped FK wrist error from 80.4 mm to 39.3 mm and depth error from 53.2 mm to 38.5 mm.

The control changes detector localization and landmark definition together. It therefore locates a major failure source at the observation-correspondence boundary without assigning separate effects to pixel noise and anatomical landmark mismatch. The remaining 38.5 mm depth error is consistent with the camera-ray ambiguity established above.

Lin et al. (2024) address correspondence by learning biomechanical coordinates from image features with synthetic anatomical supervision. OpenCapBench and SynthPose (Gozlan et al., 2025) learn denser anatomy-oriented landmarks for downstream biomechanical analysis. OpenCap Monocular (Gilon et al., 2026) combines monocular initialization with confidence-weighted reprojection, temporal and contact objectives, virtual markers and OpenSim inverse kinematics. Each method adds information unavailable to the isolated single-frame chain used here.

Doubling the real-data optimization budget from 200 to 400 steps changes participant-level wrist error by less than 0.5 mm across the full-observation methods. Within this tested budget, incomplete optimization is an unlikely explanation for the remaining depth residual.

## Scope of the release

The companion repository distributes the synthetic benchmark, numerical verification suite, aggregate real-data tables, protocol amendments and an adapter for authorized local replication. Raw participant recordings, Motive trajectories and original model weights remain local.

The real-data reference is Motive's fitted skeleton, the evaluation contains three participants, and the solver receives calibrated cameras plus reference pelvis translation. Observation-dropout conditions alter the post-hoc refinement objective while holding the upstream prediction fixed. The release is therefore a diagnostic audit of the reconstruction objective rather than an end-to-end monocular benchmark.

## Implications for personalized monocular capture

Separating geometric consistency from observational identifiability changes the next experiment in three ways.

- **Personalization must include anatomical correspondence.** BODIESReg (Chaurasia et al., 2026) treats surface registration and anatomical landmark estimation as explicit stages. Surface shape and segment length provide useful information, but internal joint-centre uncertainty must still propagate into the kinematic estimate. Maarleveld et al. (2025) make the same broader point for muscle parameters: physiological variation extends beyond uniform geometric scaling.
- **Motion and viewpoint determine what becomes observable.** Li et al. (2026) show in calibration-free inertial estimation that relative orientation and sensor location depend on different motion excitations. The visual analogue is to identify which camera viewpoints and movement phases separate competing depth solutions instead of weighting every frame equally.
- **Expanding the observation set can be more effective than restricting the solver.** MuPPet (Markhorst et al., 2026) pools temporal and inter-person evidence; OpenCapBench supplies dense synthetic landmarks; OpenCap Monocular adds temporal, contact and virtual-marker constraints. These approaches target missing information rather than relying on a tighter range-of-motion bound.

The downstream movement measure also matters. Van der Kruk et al. (2022) found distinct compensatory strategies in sit-to-walk motion. A clinical estimator must preserve such functional variation while improving accuracy, rather than defining success as convergence toward a population-average trajectory.

The next study will compare sparse detector joints, anatomy-aware landmarks and reference projections under controlled image occlusion; perturb camera and joint-centre geometry separately; and propagate each uncertainty source into a prespecified movement outcome. Participant splits and evaluation measures will be fixed before comparison.

Following the framework of Hicks et al. (2015), numerical verification, reference-based validation and sensitivity analysis will remain separate parts of that evaluation.

The [public code and complete aggregate results](https://github.com/Ajishpradeep/kinematic-observability) include the numerical tests, sensitivity conditions and protocol history. The operational rule is simple: report the constraints a reconstruction satisfies, the observations it agrees with and its error against an independent reference as separate quantities.

## References

- Conclusion or Illusion: Quantifying Uncertainty in Inverse Analyses From Marker-Based Motion Capture due to Errors in Marker Registration and Model Scaling — T. K. Uchida and Ajay Seth, Frontiers in Bioengineering and Biotechnology 2022 — https://doi.org/10.3389/fbioe.2022.874725
- Is My Model Good Enough? Best Practices for Verification and Validation of Musculoskeletal Models and Simulations of Movement — Jennifer L. Hicks, Thomas K. Uchida, Ajay Seth, Apoorva Rajagopal and Scott L. Delp, Journal of Biomechanical Engineering 2015 — https://doi.org/10.1115/1.4029304
- Towards Single Camera Human 3D-Kinematics — Marian Bittner, Wei-Tse Yang, Xucong Zhang, Ajay Seth, Jan van Gemert and Frans C. T. van der Helm, Sensors 2023 — https://doi.org/10.3390/s23010341
- 3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data — Zhi-Yi Lin, Bofan Lyu, Judith Cueto Fernandez, Eline van der Kruk, Ajay Seth and Xucong Zhang, arXiv 2024 — https://arxiv.org/abs/2402.13172
- BODIESReg: An Open-Source Pipeline for Registering 3D Body Scans Using Pose-Aligned Initialization — Vikash Chaurasia, Judit Cueto Fernandez, J. Micah Prendergast and Eline van der Kruk, arXiv 2026 — https://arxiv.org/abs/2607.15463
- What the PCSA? A systematic review exploring the age- and sex-related differences in muscle parameter values — Vera C. Maarleveld, DirkJan H. E. J. Veeger, Frans C. T. van der Helm, Jaebum Son, Richard L. Lieber and Eline van der Kruk, Journal of Biomechanics 2025 — https://doi.org/10.1016/j.jbiomech.2025.112976
- Calibration-free IMU-based Relative Orientation Estimation under Dynamic Human Motion — Ruiyuan Li, Hassan Osman, Ajay Seth and Manon Kok, arXiv 2026 — https://arxiv.org/abs/2610.31156
- MuPPet: Multi-person 2D-to-3D Pose Lifting — Niels Markhorst, Zhi-Yi Lin, Ryan Chew, Jan van Gemert and Xucong Zhang, arXiv 2026 — https://arxiv.org/abs/2604.09715
- OpenCapBench: A Benchmark to Bridge Pose Estimation and Biomechanics — Yoni Gozlan, Antoine Falisse, Scott D. Uhlrich, Anthony Gatti, Michael J. Black, Jennifer L. Hicks, Scott L. Delp and Akshay S. Chaudhari, WACV 2025 — https://openaccess.thecvf.com/content/WACV2025/html/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.html
- OpenCap Monocular: Exploring monocular video for estimating 3D human movement dynamics — Selim Gilon, Emily Y. Miller and Scott D. Uhlrich, arXiv 2026 — https://arxiv.org/abs/2603.24733
- Why do older adults stand-up differently to young adults? Investigation of compensatory movement strategies in sit-to-walk — Eline van der Kruk, Paul Strutton, Louis J. Koizia, Michael Fertleman, Peter Reilly and Anthony M. J. Bull, npj Aging 2022 — https://doi.org/10.1038/s41514-022-00094-x
