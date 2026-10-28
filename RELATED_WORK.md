# Research lineage and the question this study can answer

Ajish Pradeep · literature audit, 28 October 2026

This study asks whether structural consistency and image agreement are reliable indicators of reconstruction accuracy when observations or body geometry are imperfect. It engages with the research of Eline van der Kruk, Ajay Seth and Xucong Zhang, and with the methods their work uses or compares against. It is an independent diagnostic, not a reproduction, endorsement, or claim to solve their research programmes.

This is a focused, source-linked review, not an exhaustive bibliography or systematic review. Sources were selected by following the joint video-kinematics paper, relevant author publication lists, and methodological references that change the experiment's interpretation. Sections below distinguish published findings, our interpretation, and work not yet done. A citation establishes attribution, not personal endorsement by any researcher.

## 1. Direct estimation already includes monocular biomechanics

**Bittner, Yang, Zhang, Seth, van Gemert and van der Helm (2023), [Towards Single Camera Human 3D-Kinematics / D3KE](https://arxiv.org/abs/2301.05435)**, Sensors 23(1), 341; see Methods, Fig. 3 and Discussion §§5.3–5.5. D3KE predicts model coordinates and segment scales from monocular images, then refines a sequence. Its differentiable skeletal layer supplies positional supervision. Fig. 3 already explains the distal effect of proximal angle errors. Its discussion identifies unfamiliar viewpoints, abnormal movement, occluded-joint assumptions and mobile execution as further work. Thus neither monocular FK nor the lever-arm observation is new here. Our useful connection is an auditable test of assumptions, not a replacement for D3KE.

**Lin, Lyu, Cueto Fernandez, van der Kruk, Seth and Zhang (2024), [3D Kinematics Estimation from Video with a Biomechanical Model and Synthetic Training Data](https://arxiv.org/html/2402.13172v4)**; see §§2.1, 3.2–3.4, 4.3 and 4.6. This is direct image-feature inference, not a keypoint-lifting pipeline. Calibrated two-view feature sampling and temporal refinement accompany angle/scale regression; supervision includes angles, scales, physiological bounds and FK positions. ODAH addresses synthetic anatomical correspondence and appearance variation. Its position evaluation uses Procrustes alignment, unlike our reported metric errors. Our detector-pixel controls cannot diagnose this network's failures or support numerical comparisons with its tables.

## 2. A small fitting residual is an old and important warning

**Uchida and Seth (2022), [Conclusion or Illusion: Quantifying Uncertainty in Inverse Analyses From Marker-Based Motion Capture due to Errors in Marker Registration and Model Scaling](https://doi.org/10.3389/fbioe.2022.874725)**, Frontiers in Bioengineering and Biotechnology 10:874725; see uncertainty propagation, results and discussion. Their OpenSim analysis varies marker registration and scaling and finds materially different kinematics and kinetics despite low tracking errors. This is the closest conceptual precedent. We examine a related distinction with monocular pixels, a much smaller geometric model, and cached upper-limb predictions; we do not establish a new general principle or reproduce their uncertainty distribution.

**Hicks, Uchida, Seth, Rajagopal and Delp (2015), [Is My Model Good Enough?](https://doi.org/10.1115/1.4029304)**, Journal of Biomechanical Engineering 137:020905; see §2 and geometry validation in §3.2. Their separation of software verification, experimental validation and sensitivity testing is the right standard for this artifact. Our exact tests verify geometric code; a synthetic generator sharing the same geometry cannot validate human anatomy. Reference-derived lengths used in fitting also prevent treating all reference comparisons as independent validation.

**Li, Osman, Seth and Kok (2026), [Calibration-free IMU-based Relative Orientation Estimation under Dynamic Human Motion](https://arxiv.org/html/2610.31156v1)**, preprint; see §§III–VI. The joint-centre acceleration constraint supports joint estimation of relative sensor orientation and sensor offsets. Different excitation is informative for those quantities. Relative IMU orientation is not yet anatomical joint angle; the paper leaves sensor-to-segment calibration for future work. Its zero-phase filtering also matters before calling the whole pipeline causal. The connection to our work is the question of what measurements identify, not a claim that IMU observability results transfer to monocular images.

## 3. Personalization is more than changing segment lengths

**Chaurasia, Cueto Fernandez, Prendergast and van der Kruk (2026), [BODIESReg](https://arxiv.org/html/2607.15463v1)**, preprint; see §3, §5.1 and Appendix D. Pose-aligned initialization precedes body-surface registration. The limitations explicitly distinguish surface fit, model-regressed joint centres and anatomically defined segment measurements. This makes correspondence a concrete research issue, not just detector noise. Our interpretation: uncertainty in a surface-to-anatomy mapping should be evaluated before using it as a firm kinematic constraint. This study does not run or assess BODIESReg.

**Maarleveld, Veeger, van der Helm, Son, Lieber and van der Kruk (2025), [What the PCSA?](https://doi.org/10.1016/j.jbiomech.2025.112976)**, Journal of Biomechanics 193:112976; see §§1.1–1.4, 4 and 5. The review examines age/sex differences in muscle parameters and the limits of uniform strength scaling. Muscle mass, physiological cross-sectional area and maximum isometric force are not interchangeable measurements. Our length perturbations test geometric sensitivity only: they do not test muscle personalization, demographic fairness, or the conclusions of this review.

**van der Kruk et al. (2022), [Why do older adults stand-up differently to young adults?](https://www.nature.com/articles/s41514-022-00094-x)**, npj Aging 8:13; see Discussion and Methods. The study examines compensatory sit-to-walk strategies in relation to capacity and movement objectives. It is a reason to preserve meaningful variation rather than automatically regularize movement toward a typical template. Our sports-arm audit measures none of these clinical or functional outcomes; the proposed connection needs task-specific validation.

**van der Kruk and Reijne (2018), [Accuracy of human motion capture systems for sport applications](https://doi.org/10.1080/17461391.2018.1463397)**, European Journal of Sport Science 18:806–819. Accuracy depends on the capture conditions and measured quantity. A system specification is not a joint-centre error bound for our recordings. This reinforces the need to state what the Motive fitted-skeleton reference measures.

The [BODIES programmes](https://bodieslab.com/projects/)—Breaking BIASmechanics, Diversity Outside In and Care is Coming Home—supply research motivation, not results or proof of a particular algorithm requirement. The lab also lists van der Kruk's [BIASmechanics: The human behind the model](https://bodieslab.com/wp-content/uploads/2026/07/BIASmechanics-the-human-behind-the-model_Eline-van-der-Kruk_Jul2026.pdf) as an in-review chapter. Its discussion of whose data and models are represented is relevant to cohort reporting; this three-person evaluation cannot establish population-wide validity.

## 4. Computer vision contributes information as well as constraints

**Markhorst, Lin, Chew, van Gemert and Zhang (2026), [MuPPet: Multi-person 2D-to-3D Pose Lifting](https://arxiv.org/html/2604.09715v1)**; see §§3 and 4.4–4.5. The diffusion-based lifter uses temporal and inter-person information, person encoding and permutation augmentation. Its group-interaction evaluation asks whether other people help recover pose under occlusion. This gives a useful contrast: adding informative context is different from tightening a geometric bound. Our single-chain, fixed-prediction dropout test evaluates neither MuPPet nor image-domain occlusion robustness. A caregiver or second person is an optional future setting, not assumed information for a person alone at home.

**Gozlan et al. (2025), [OpenCapBench and SynthPose](https://openaccess.thecvf.com/content/WACV2025/html/Gozlan_OpenCapBench_A_Benchmark_to_Bridge_Pose_Estimation_and_Biomechanics_WACV_2025_paper.html)**, WACV. The benchmark evaluates biomechanical angles and the accompanying method learns denser landmarks from synthetic data. This suggests a more concrete next experiment than another arbitrary loss: compare sparse and anatomically motivated observations under a fixed downstream estimator. Dense landmarks would not automatically be independent or accurate; definition, error correlation and anatomical correspondence must be checked.

## 5. Follow the actual upstream methods

These are not all papers by the three researchers. They are dependencies or relevant comparators with explicit roles in the literature above.

| Source | Verified relationship | Consequence for this project |
|---|---|---|
| Seth et al. (2018), [OpenSim](https://doi.org/10.1371/journal.pcbi.1006223) | Framework cited by Lin and D3KE | A geometric two-link implementation is not an OpenSim musculoskeletal model. |
| Rajagopal et al. (2016), [Full-Body Musculoskeletal Model for Muscle-Driven Simulation of Human Gait](https://doi.org/10.1109/TBME.2016.2586891) | Lin §3.4 cites this model | Joint frames and coupled coordinates matter; selecting lengths does not recreate the model. |
| Pavlakos et al. (2019), [Expressive Body Capture / SMPL-X](https://openaccess.thecvf.com/content_CVPR_2019/html/Pavlakos_Expressive_Body_Capture_3D_Hands_Face_and_Body_From_a_CVPR_2019_paper.html) | Lin uses SMPL-X; BODIESReg uses its VPoser pose prior | Surface-model joints and musculoskeletal joints require an explicit correspondence. |
| Mahmood et al. (2019), [AMASS](https://arxiv.org/abs/1904.03278) | Motion source in Lin's synthetic pipeline | Anatomical labels are constructed through modelling; synthetic labels are not direct bone measurements. |
| Spurr et al. (2020), [Weakly Supervised 3D Hand Pose Estimation via Biomechanical Constraints](https://arxiv.org/abs/2003.09282) | Lin cites it for the biomechanical penalty | Constraints plus 2D supervision already have a literature; benefit under particular conditions is compatible with unresolved ambiguity. |
| Pagnon, Domalain and Reveret (2022), [Pose2Sim](https://doi.org/10.21105/joss.04362) | Multi-view comparison in Lin's related work | Keep calibration, triangulation and downstream IK separate when attributing an improvement. |
| Uhlrich et al. (2023), [OpenCap](https://doi.org/10.1371/journal.pcbi.1011462) | Lin discusses the mapping from detected landmarks to anatomical markers | Learned marker augmentation is an existing correspondence strategy, not a new proposal here. |
| Shin et al. (2024), [WHAM](https://openaccess.thecvf.com/content/CVPR2024/papers/Shin_WHAM_Reconstructing_World-grounded_Humans_with_Accurate_3D_Motion_CVPR_2024_paper.pdf) | Initial pose estimator in OpenCap Monocular | Temporal image information and contact-aware global recovery exceed this isolated-chain diagnostic. |

**Gilon, Miller and Uhlrich (2026), [OpenCap Monocular](https://arxiv.org/html/2603.24733v1)**, preprint; see §§2.2–2.4. Its WHAM initialization is refined using confidence-weighted reprojection and other objectives, followed by virtual markers and OpenSim IK. Known height, camera assumptions and contact information contribute to estimation. It reports marker/force-plate validation and deploys using cloud processing. Therefore monocular biomechanical refinement is already a concrete comparator. We have not run it, and our wrist errors cannot be compared with its joint-angle or pelvis metrics. A future evaluation should ask what information each method receives, not just whether each uses FK.

## 6. Sources considered but not treated as demonstrated results

[ODAH-SpeedSkater](https://resolver.tudelft.nl/uuid:fbe7a517-5fb8-4d86-b8d8-966154ee28d7) is Punitha Devaraja's 2024 MSc thesis, with van der Kruk as mentor and Seth on the committee—not a journal follow-up co-authored by all three target researchers. Its repository abstract describes task-specific synthetic video generation and limited testing. It is useful context for movement coverage, not evidence of generalization to patients.

[MSK-Morph](https://doi.org/10.64898/2026.04.28.721455), by Cueto Fernandez and colleagues including Seth and van der Kruk, is listed as in review on the [lab publication page](https://bodieslab.com/publications-2/). The primary preprint was inaccessible during this audit. It remains a priority for a subsequent full-text read; no numerical or detailed methodological claim here depends on it. FLEMM is also listed as in submission/early access; do not describe it as a tested public baseline without obtaining the release.

Unrelated gaze, speech and haptics papers are not included merely because an author matches. Model Health and OpenCap product relationships do not establish a specific lab's privacy policy, deployment contract or recruitment plan.

## 7. What this changes in the research plan

The current result is a transparent diagnostic artifact. It supports a research direction, not a claim of method novelty or readiness for clinical use.

1. **Correspondence first.** On accessible synchronized video/reference data, compare detected landmarks, anatomically defined/augmented landmarks and reference projections. Separate detector localization from mapping uncertainty rather than claiming the current oracle-pixel control isolates either.
2. **Information-matched comparisons.** Compare appropriate published systems only after documenting their camera, height, temporal, contact and anatomy inputs. Include actual image occlusions with estimator reruns, plus non-occluded controls. Predefine participant splits and report participant-level effects.
3. **Propagation to the chosen output.** Vary calibration, joint-centre offsets and model geometry separately and jointly. Measure anatomical coordinate error and a prespecified movement endpoint, not only wrist distance. Local measurement-Jacobian analysis needs parameter scaling and explicit gauge handling; it does not alone detect disconnected alternative solutions or provide calibrated uncertainty.
4. **Preserve atypical movement.** Test whether personalization or a learned prior improves reference accuracy while preserving compensatory strategies. Do not use a typical-population ROM cap as a clinical truth.
5. **Deployment after validation.** Evaluate causal temporal windows, numerical conversion, memory, latency, thermal behaviour and accuracy on an actual device. On-device experience is relevant expertise; this repository contains no on-device biomechanics benchmark.

No new experiments are claimed by this literature update. The original protocol, amendments, tables and source hashes remain unchanged.

### Affiliation note

The shared papers retain their historical Delft affiliations. As checked on 28 October 2026, [Xucong Zhang's page](https://www.ccmitss.com/zhang) reports his October move to ELLIS Institute Finland and the University of Turku, corroborated by the [Turku staff directory](https://www.utu.fi/en/university/faculty-of-technology/computing/contact/software-engineering-contact%20information). Research continuity should not be mistaken for a confirmed current Delft supervisory arrangement.
