"""Fit on development takes, then evaluate held-out groups using frozen cutoffs."""

import argparse
from pathlib import Path

import numpy as np

from observability.assets import local_output, sha256

from .design import read_json, write_json
from .measure import METHODS, REFERENCES, measure_split
from .metrics import (
    change_metrics,
    decisions,
    distribution,
    fit_policy,
    policy_outcomes,
    risk_curve,
)

OUTCOMES = ("absolute", "change")
SPLITS = ("development", "confirmation")
SCORES = ("confidence", "ray_gap")


def endpoint(values, outcome, outer=False, vector=False):
    """Apply the frozen within-window endpoint or difference operator."""
    if outcome == "absolute":
        return values.reshape((-1, 3) if vector else -1)
    if vector:
        windows = values.reshape(-1, 3, 3, 2, 3)
        delta = (
            windows[:, :, 2:3] - windows[:, :, :1]
            if outer
            else np.diff(windows, axis=2)
        )
        return delta.reshape(-1, 3)
    windows = values.reshape(-1, 3, 3, 2)
    if outer:
        return np.maximum(windows[:, :, 0], windows[:, :, 2]).reshape(-1)
    return np.maximum(windows[:, :, :-1], windows[:, :, 1:]).reshape(-1)


def _finite_vector(x):
    return np.isfinite(x).all(axis=-1)


def _stack(records, key):
    return np.stack([row[key] for row in records])


def build_rows(records, method, outcome, outer=False, shift=0, threshold=0):
    index = METHODS.index(method)

    def apply(values, vector=False):
        return endpoint(values, outcome, outer, vector)

    estimate = apply(_stack(records, "xyz")[:, index], True)
    score = apply(_stack(records, "wrist_score")[:, index])
    if threshold:
        allowed = score <= 1 - threshold
        estimate[~allowed] = np.nan
        score[~allowed] = np.nan
    scores = {"confidence": score}
    if method == "two_view":
        gap = apply(_stack(records, "ray_gap")[:, index])
        scores["ray_gap"] = np.where(np.isfinite(score), gap, np.nan)
    reference = {
        name: apply(
            np.stack([row["reference"][name][1 + shift] for row in records]), True
        )
        for name in REFERENCES
    }
    per_take = len(estimate) // len(records)
    return {
        "estimate": estimate,
        "oracle": apply(_stack(records, "oracle")[:, index], True),
        "reference": reference,
        "score": scores,
        "loss": {
            name: np.linalg.norm(estimate - target, axis=1)
            for name, target in reference.items()
        },
        "group": np.repeat([row["group"] for row in records], per_take),
        "fps": np.repeat([row["fps"] for row in records], per_take),
        "take": np.repeat([row["take_id"] for row in records], per_take),
    }


def fit(records, config):
    policies = {}
    for method in METHODS:
        for outcome in OUTCOMES:
            rows = build_rows(records, method, outcome)
            for score_name, score in rows["score"].items():
                key = f"{method}/{outcome}/{score_name}"
                policies[key] = {}
                for level, tolerance in (
                    ("primary", config["tolerances_mm"][outcome]),
                    ("strict", config["tolerances_mm"][outcome] / 2),
                ):
                    policies[key][level] = {}
                    targets = {"midpoint": rows["loss"]["midpoint"]}
                    for alt in REFERENCES[1:]:
                        primary = rows["loss"]["midpoint"]
                        alternative = rows["loss"][alt]
                        common = np.isfinite(primary) & np.isfinite(alternative)
                        targets[f"midpoint_with_{alt}"] = np.where(
                            common, primary, np.nan
                        )
                        targets[f"{alt}_with_midpoint"] = np.where(
                            common, alternative, np.nan
                        )
                    for ref, loss in targets.items():
                        policies[key][level][ref] = fit_policy(
                            loss,
                            score,
                            rows["group"],
                            tolerance,
                            config["max_accepted_failure"],
                            config["min_coverage"],
                            config["repeat_score_quantile"],
                        )
    return policies


def _summary(rows, name, mask, outcome, floor, tolerance):
    loss = rows["loss"][name]
    estimate = rows["estimate"]
    target = rows["reference"][name]
    valid = mask & np.isfinite(loss)
    ref_valid = mask & _finite_vector(target)
    estimable = mask & _finite_vector(estimate)
    result = {
        "scheduled": int(mask.sum()),
        "takes": len(np.unique(rows["take"][mask])),
        "reference_available": int(ref_valid.sum()),
        "estimate_available": int(estimable.sum()),
        "scored_takes": len(np.unique(rows["take"][valid])),
        "loss_mm": distribution(loss[valid]),
        "failures": int((valid & (loss > tolerance)).sum()),
    }
    if outcome == "change":
        result.update(
            reference_moved=int(
                (ref_valid & (np.linalg.norm(target, axis=1) >= floor)).sum()
            ),
            transfer=change_metrics(target[valid], estimate[valid], floor),
        )
    return result


def _reference_transfer(rows, mask, alt, score, primary_policy, tolerance):
    a = rows["loss"]["midpoint"][mask]
    b = rows["loss"][alt][mask]
    common = np.isfinite(a) & np.isfinite(b)
    if not common.any():
        return {"paired": 0}
    x = decisions(score[mask][common], primary_policy["midpoint"])
    y = decisions(score[mask][common], primary_policy[f"midpoint_with_{alt}"])
    z = decisions(score[mask][common], primary_policy[f"{alt}_with_midpoint"])
    baseline = a[common] > tolerance
    changed = b[common] > tolerance
    return {
        "paired": int(common.sum()),
        "loss_midpoint_mm": distribution(a[common]),
        "loss_alternative_mm": distribution(b[common]),
        "loss_alternative_minus_midpoint_mm": distribution(b[common] - a[common]),
        "reference_separation_mm": distribution(
            np.linalg.norm(
                rows["reference"][alt][mask][common]
                - rows["reference"]["midpoint"][mask][common],
                axis=-1,
            )
        ),
        "label_switches": int(np.sum(baseline != changed)),
        "became_failure": int(np.sum(~baseline & changed)),
        "became_pass": int(np.sum(baseline & ~changed)),
        "paired_policy_switches": int(np.sum(y != z)),
        "paired_action_matrix": np.bincount(3 * y + z, minlength=9)
        .reshape(3, 3)
        .tolist(),
        "accepted_label_switches": int(np.sum((x == 2) & (baseline != changed))),
        "frozen_on_midpoint": policy_outcomes(x, a[common], tolerance),
        "frozen_on_alternative": policy_outcomes(x, b[common], tolerance),
        "matched_fit_on_midpoint": policy_outcomes(y, a[common], tolerance),
        "matched_fit_on_alternative": policy_outcomes(z, b[common], tolerance),
    }


def _scored(rows, mask, policy, tolerance):
    loss = rows["loss"]["midpoint"][mask]
    results = {}
    for name, score in rows["score"].items():
        score_local = score[mask]
        valid = np.isfinite(loss) & np.isfinite(score_local)
        fitted = policy[name]
        results[name] = {
            "ranking": risk_curve(
                loss[valid], score_local[valid], tolerance, len(loss)
            ),
            "primary_policy": policy_outcomes(
                decisions(score_local, fitted["midpoint"]), loss, tolerance
            ),
            "reference_transfer": {
                alt: _reference_transfer(rows, mask, alt, score, fitted, tolerance)
                for alt in REFERENCES[1:]
            },
        }
    return results


def _summary_with_oracle(rows, mask, outcome, floor, tolerance):
    summary = {
        ref: _summary(rows, ref, mask, outcome, floor, tolerance) for ref in REFERENCES
    }
    valid = (
        mask & np.isfinite(rows["loss"]["midpoint"]) & _finite_vector(rows["oracle"])
    )
    oracle_loss = np.linalg.norm(
        rows["oracle"][valid] - rows["reference"]["midpoint"][valid], axis=1
    )
    summary["oracle_midpoint_loss_mm"] = distribution(oracle_loss)
    summary["detector_matched_oracle_loss_mm"] = distribution(
        rows["loss"]["midpoint"][valid]
    )
    return summary


def _denominators(records):
    decoded = _stack(records, "decoded")
    detections = _stack(records, "detections")
    confidence = _stack(records, "confidence")
    pixels = _stack(records, "pixels")
    schema = {
        ref: np.asarray([row["reference_schema"][ref] for row in records])
        .sum(axis=0)
        .tolist()
        for ref in REFERENCES
    }
    result = {
        "takes": len(records),
        "groups": len({row["group"] for row in records}),
        "unique_frames": int(np.prod(decoded.shape[::2])),
        "camera_slots": decoded.size,
        "oracle_supported_positions": sum(
            row["oracle_supported_positions"] for row in records
        ),
        "oracle_outside_common_image": sum(
            row["oracle_outside_common_image"] for row in records
        ),
        "oracle_max_error_mm": max(row["oracle_max_error_mm"] for row in records),
        "decoded": int(decoded.sum()),
        "decoded_no_person": int(np.sum(decoded & (detections == 0))),
        "decoded_multiple_people": int(np.sum(decoded & (detections > 1))),
        "view_wrist_slots": confidence.size,
        "finite_positive_view_wrist_scores_and_pixels": int(
            np.sum(np.isfinite(confidence) & (confidence > 0) & _finite_vector(pixels))
        ),
        "view_wrist_below_0_25_with_positive_finite_scores_and_pixels": int(
            np.sum(
                np.isfinite(confidence)
                & (confidence > 0)
                & (confidence < 0.25)
                & _finite_vector(pixels)
            )
        ),
        "reference_schema_takes_by_left_right": schema,
        "by_view": [
            {
                "slots": decoded[:, view].size,
                "decoded": int(decoded[:, view].sum()),
                "no_person": int(np.sum(decoded[:, view] & (detections[:, view] == 0))),
                "multiple_people": int(np.sum(detections[:, view] > 1)),
            }
            for view in range(2)
        ],
    }
    return result


def _matched_methods(rows_by_method, outcome, floor):
    common = np.logical_and.reduce(
        [np.isfinite(rows["loss"]["midpoint"]) for rows in rows_by_method.values()]
    )
    result = {}
    for method, rows in rows_by_method.items():
        info = {"loss_mm": distribution(rows["loss"]["midpoint"][common])}
        if outcome == "change":
            info["transfer"] = change_metrics(
                rows["reference"]["midpoint"][common], rows["estimate"][common], floor
            )
        result[method] = info
    return result


def evaluate(records, policies, config):
    group_names = sorted({row["group"] for row in records})
    groups = {
        group: {
            "denominators": _denominators(
                [row for row in records if row["group"] == group]
            )
        }
        for group in group_names
    }
    result = {
        "denominators": _denominators(records),
        "groups": groups,
        "main": {},
        "sensitivity": {},
        "matched_methods": {},
    }
    floor = config["moved_reference_floor_mm"]
    for outcome in OUTCOMES:
        tolerance = config["tolerances_mm"][outcome]
        matched = {}
        for method in METHODS:
            key = f"{method}/{outcome}"
            rows = build_rows(records, method, outcome)
            matched[method] = rows
            all_rows = np.ones(len(rows["estimate"]), dtype=bool)
            policy = {
                name: policies[f"{key}/{name}"]["primary"] for name in rows["score"]
            }
            strict = {
                name: policies[f"{key}/{name}"]["strict"] for name in rows["score"]
            }
            result["main"][key] = {
                "reference_metrics": _summary_with_oracle(
                    rows, all_rows, outcome, floor, tolerance
                ),
                "scores": _scored(rows, all_rows, policy, tolerance),
            }
            for group in group_names:
                mask = rows["group"] == group
                groups[group][key] = {
                    "reference_metrics": _summary_with_oracle(
                        rows, mask, outcome, floor, tolerance
                    ),
                    "scores": _scored(rows, mask, policy, tolerance),
                }
            sensitivity = result["sensitivity"][key] = {
                "strict_tolerance": _scored(rows, all_rows, strict, tolerance / 2),
            }
            for label, kwargs in (
                ("reference_minus_1", {"shift": -1}),
                ("reference_plus_1", {"shift": 1}),
                ("wrist_confidence_0_25", {"threshold": 0.25}),
                ("outer_window", {"outer": True}),
            ):
                if label == "outer_window" and outcome != "change":
                    continue
                alt = build_rows(records, method, outcome, **kwargs)
                mask = np.ones(len(alt["estimate"]), dtype=bool)
                sensitivity[label] = {
                    "midpoint": _summary(
                        alt, "midpoint", mask, outcome, floor, tolerance
                    ),
                    "scores": _scored(alt, mask, policy, tolerance),
                }
                if len(mask) == len(all_rows):
                    paired = np.isfinite(rows["loss"]["midpoint"]) & np.isfinite(
                        alt["loss"]["midpoint"]
                    )
                    sensitivity[label]["primary_on_common_support"] = _summary(
                        rows, "midpoint", paired, outcome, floor, tolerance
                    )
                    sensitivity[label]["sensitivity_on_common_support"] = _summary(
                        alt, "midpoint", paired, outcome, floor, tolerance
                    )
            for fps in sorted(set(rows["fps"])):
                mask = rows["fps"] == fps
                sensitivity[f"fps_{int(fps)}"] = {
                    "midpoint": _summary(
                        rows, "midpoint", mask, outcome, floor, tolerance
                    ),
                    "scores": _scored(rows, mask, policy, tolerance),
                }
        result["matched_methods"][outcome] = _matched_methods(matched, outcome, floor)
    return result


def run(design_path, observations, output):
    output = local_output(Path(output))
    design = read_json(design_path)
    design["sha256"] = sha256(design_path)
    config = design["policy"]
    sources = {
        str(path): sha256(path)
        for directory in ("src/observability/study", "src/observability/pilot")
        for path in sorted(Path(directory).glob("*.py"))
        if path.name != "report.py"
    }
    development = list(measure_split(design, observations, SPLITS[0]))
    observation_config = development[0]["observation_config"]
    if any(row["observation_config"] != observation_config for row in development):
        raise ValueError("mixed development observation provenance")
    policies = fit(development, config)
    manifest = {
        "design_sha256": design["sha256"],
        "implementation_sha256": sources,
        "development_observation_manifests": {
            row["take_id"]: row["observation_manifest_sha256"] for row in development
        },
        "policy": policies,
        "observation_config": observation_config,
    }
    policy_path = output / "policy.json"
    if policy_path.exists() and read_json(policy_path) != manifest:
        raise ValueError("fitted policy or source hash differs from existing freeze")
    write_json(policy_path, manifest)
    for split in SPLITS:
        records = (
            development
            if split == SPLITS[0]
            else list(measure_split(design, observations, split))
        )
        if any(row["observation_config"] != observation_config for row in records):
            raise ValueError("mixed observation provenance")
        evidence = evaluate(records, policies, config)
        evidence["provenance"] = {
            "policy_sha256": sha256(policy_path),
            "observation_manifests": {
                row["take_id"]: row["observation_manifest_sha256"] for row in records
            },
        }
        write_json(output / f"{split}.json", evidence)
        print(split, evidence["denominators"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=Path("local/study/design.json"))
    parser.add_argument(
        "--observations", type=Path, default=Path("local/study/observations")
    )
    parser.add_argument("--output", type=Path, default=Path("local/study/analysis"))
    args = parser.parse_args()
    run(args.design, args.observations, args.output)
