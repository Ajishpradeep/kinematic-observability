<!-- note: category=evaluation -->
# A valid reconstruction can still be the wrong one

```claim
Fixed segment lengths and a small image residual do not establish 3D accuracy. In an exploratory three-person audit, an articulated refinement reduced the image residual but increased mean wrist error; replacing the detected pixels with reference projections changed the result substantially.
```

A reconstructed limb can keep exactly the right length, fit the image closely, and still put its endpoint in the wrong place. I wanted to separate those three properties before treating an anatomical constraint as evidence that a pose estimate had improved.

The distinction matters when a model has to infer movement from a single camera. Lin et al. (2024) predict biomechanical coordinates and body segment scales from two-view images, with positional supervision through an OpenSim forward-kinematics model. Their work also identifies a problem that becomes important here: image landmarks and anatomical joint centres need not coincide. I built a much smaller diagnostic to investigate the interaction between geometry, observations and model mismatch. It is not a reproduction of their network or OpenSim model.

## A constraint removes possibilities without identifying the truth

Consider a two-segment chain with root position $r$, segment lengths $l_1,l_2$, and unit directions $d_1,d_2$. Its middle and distal points are

$$
p_1=r+l_1d_1,\qquad p_2=r+l_1d_1+l_2d_2.
$$

These equations guarantee the selected lengths. They do not guarantee that those lengths describe the person, or that either direction is correct. The bend angle is $\arccos(d_1^\top d_2)$. An interval imposed on that angle constrains this geometric model; it does not define an anatomical joint coordinate system or reveal segment twist.

The sensitivity to a proximal rotation is equally specific. For a revolute coordinate $q_k$, axis $a_k$ and axis origin $o_k$, the derivative of a downstream point is

$$
\frac{\partial p_2}{\partial q_k}=a_k\times(p_2-o_k).
$$

The perpendicular distance to the axis controls the first-order displacement caused by an angle error. This explains why a small proximal error can move a distal point considerably. It does not establish that an FK estimator will fail more often than a coordinate predictor; that depends on the errors each estimator makes.

## A pixel leaves a direction unmeasured

Perspective projection maps $(X,Y,Z)$ to $(f_xX/Z+c_x,f_yY/Z+c_y)$. Points along the same camera ray have the same image coordinates. A length constraint can reduce that ambiguity without eliminating it.

Take a known root at $(0,0,3)$ metres and a segment of length $0.5$ metres. A distal point on the ray $(0.1z,0,z)$ must satisfy

$$
1.01z^2-6z+8.75=0.
$$

Both roots are positive. They yield different depths, the same segment length, and the same projected point. The numerical test in the repository checks both the length and the pixel equality. This is an exact geometric counterexample, independent of training, confidence scores or optimizer quality.

## What the experiment changes

The model has a free root, two angles for the first segment, a bending-plane angle and a bend angle. I compare the initial 3D prediction with root-outward length correction, Cartesian refinement and articulated refinement. The articulated variants use no angle cap, a soft cap, or a hard sigmoid bound. All refinements share the same initial pose, observations and optimization budget.

The objective combines a 3D tether to the initial prediction with a pixel residual:

$$
\mathcal L=\sum_j\frac{\|p_j-p_j^0\|^2}{(0.08\,\mathrm m)^2}
+\sum_j w_j\frac{\|\pi_K(p_j)-u_j\|^2}{(5\,\mathrm{px})^2}
+\mathcal L_{\mathrm{bound}}.
$$

Here $p_j^0$ is the initial prediction, $u_j$ an observed pixel location, $K$ the known camera calibration, and $w_j$ a heuristic observation weight. The scales are declared engineering settings, not fitted uncertainty estimates. Setting a weight to zero removes an observation. It does not simulate an image occlusion seen by the original network.

The first experiment samples three-dimensional chains with random orientations, translations, lengths and bends, using 512 cases for each of three seeds. The initial predictions contain correlated angular perturbations and coordinate noise; image observations contain noise. The solver shares the generator's geometry, so this is a controlled mechanism check, not evidence of transfer to human video.

With correct lengths and all observations, articulated refinement reduced mean distal error from 101.5 mm to 43.5 mm in the soft-cap condition. A deliberately restrictive 90° hard cap instead gave 68.8 mm. Those values demonstrate sensitivity to an incorrect bound in this simulation. The 90° cap is a stress condition, not a claim about normal or pathological human ROM.

## The real-data result does not follow the synthetic ranking

The second experiment uses cached monocular predictions and synchronized OptiTrack references. Four people supply the generic segment lengths; three people excluded from the 3D predictor's training supply the evaluation cohort. The evaluation uses 5,414 shoulder–elbow–wrist chain observations, covering both arms and both cameras. These are repeated measurements of three people, not 5,414 independent participants.

The reference positions come from Motive's fitted skeleton. They are not direct measurements of bone motion. I excluded lower limbs from this first study because an ankle-reference problem was already documented for one participant. The selected motion is sports movement, not neurological gait.

The following table uses target-person reference-derived lengths, known camera calibration and reference pelvis translation. These are privileged diagnostic inputs. The values are means of the three participant means, after 200 optimization steps.

| Method | Wrist 3D error, mm | Wrist depth error, mm | Image residual, px |
|---|---:|---:|---:|
| Initial prediction | 78.3 | 49.6 | 17.91 |
| Root-outward length correction | 83.2 | 47.1 | 19.10 |
| Cartesian refinement with pixels | 76.2 | 48.3 | 0.37 |
| Fixed-length FK with pixels | 80.3 | 53.1 | 1.36 |
| FK with a soft 150° cap | 80.3 | 53.1 | 1.36 |
| FK with a hard 150° cap | 80.0 | 52.8 | 1.39 |

The fixed-length methods satisfy the imposed lengths to numerical precision. That consistency accompanies slightly worse average wrist accuracy in the full-observation setting. The image residual becomes small without establishing that depth is right.

Participant-level results prevent the mean from hiding the trade-off. With FK and pixels but no angle cap, wrist error changed from 78.3 to 71.7 mm for one participant, from 77.8 to 92.5 mm for another, and from 78.9 to 76.8 mm for the third. This does not support a claim that constraints universally help or universally hurt.

## Better observations change the answer

After seeing that result, I added a diagnostic control: replace the detector's pixel locations with the reference skeleton's own projections. This control is explicitly post-pilot and uses information unavailable to a deployed estimator.

At 400 steps, the no-cap FK method has 80.4 mm mean wrist error with detected pixels and 39.3 mm with reference-projected pixels. Its corresponding depth errors are 53.2 and 38.5 mm. Even perfect pixel correspondence does not remove the remaining depth error under this regularizer and solver.

The difference shows that observation quality and correspondence can materially change the outcome. It does not isolate anatomical landmark mismatch from detector localization error: both change together in this control. Lin et al.'s distinction between visible landmarks and anatomical joint centres is a reason to examine that gap, not proof that it explains all of it here.

Doubling the real-data optimization budget from 200 to 400 steps changes the full-observation, oracle-length macro wrist errors only slightly. The largest participant-level wrist change across methods in that setting is below 0.5 mm. This checks one budget sensitivity; it is not proof of a global optimum. The full 400-step tables are included.

## What remains unsupported

The public code reproduces the synthetic experiment and numerical checks. Recordings, participant trajectories and original model weights are not distributed. The real-data release contains aggregate tables and an adapter for authorized local replication; it is not a fully open raw-data benchmark.

No network was retrained under image occlusion. The real-data observation-dropout conditions keep the original prediction fixed. The cohort was previously inspected, the sample contains only three evaluation people, and the 3D reference itself is model-dependent. The study also gives the solver a known camera and reference pelvis translation, so it does not solve monocular localization or calibration.

The next useful test is actual image occlusion on an independently accessible video/reference dataset, with separate checks for landmark definitions, camera uncertainty and subject-specific segment frames. OpenCapBench (Gozlan et al., 2025) is relevant because it evaluates the connection between pose estimation and biomechanical outputs. BODIES' personalization programmes make the complementary question concrete: which aspects of a generic model should vary with the person rather than be enforced as universal constraints?

For now, I would report three quantities separately: the constraints a solution satisfies, the observations it agrees with, and its error against an independent reference. A small value for either of the first two is not a substitute for measuring the third.

## References

- 3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data — Zhi-Yi Lin, Bofan Lyu, Judith Cueto Fernandez, Eline van der Kruk, Ajay Seth and Xucong Zhang, arXiv 2024 — https://arxiv.org/abs/2402.13172
- OpenCapBench: A Benchmark to Bridge Pose Estimation and Biomechanics — Gozlan et al., WACV 2025 — https://openaccess.thecvf.com/content/WACV2025/papers/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.pdf
- BODIES research programmes — BODIES Lab, project descriptions 2026 — https://bodieslab.com/projects/

## Code and results

The [reproducible experiment and full aggregate results](https://github.com/Ajishpradeep/kinematic-observability) include the numerical tests, protocol amendments and limitations. This independent study is not affiliated with or endorsed by the researchers cited above.
