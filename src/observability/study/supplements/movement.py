"""Post hoc description of displacement error by the size of the true movement.

This supplement was added after the planned analysis. It reuses the frozen rows and
the frozen development cutoffs, and it fits nothing. Its outputs are descriptive.
"""

import argparse
from pathlib import Path

import numpy as np

from observability.assets import local_output, sha256
from observability.pilot.calibration import project_points

from ..design import read_json, write_json
from ..measure import METHODS, _read_calibration, measure_split
from ..metrics import rank_correlation

SPLITS = ("development", "confirmation")
TOLERANCE_MM = 50.0
FINE_BINS = ((0, 10), (10, 25), (25, 50), (50, 100), (100, 200), (200, None))
COARSE_BINS = ((0, 10), (10, 50), (50, None))
SEPARATED_PX = 60.0
FAR_PX = 150.0


def window_pairs(values):
    """Split (..., 9, 2, D) window samples into consecutive endpoint pairs."""
    shaped = values.reshape(values.shape[:-3] + (3, 3) + values.shape[-2:])
    return shaped[..., :, :-1, :, :], shaped[..., :, 1:, :, :]


def offset_decomposition(first, second):
    """Split two endpoint errors into a shared offset and half their difference.

    For every pair, |e1|^2 + |e2|^2 = 2|s|^2 + 2|h|^2 with s = (e1 + e2) / 2 and
    h = (e2 - e1) / 2, so the returned share is the fraction of squared position
    error that is common to both endpoints and cancels in the displacement.
    """
    shared = np.linalg.norm((first + second) / 2, axis=-1)
    half = np.linalg.norm((second - first) / 2, axis=-1)
    power = np.sum(shared**2)
    total = power + np.sum(half**2)
    return shared, 2 * half, float(power / total) if total else None


def in_bin(values, low, high):
    return (values >= low) & (values < (np.inf if high is None else high))


def _median(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return float(np.median(values)) if len(values) else None


def _p90(values):
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    return float(np.percentile(values, 90)) if len(values) else None


def _cosine(estimated, reference):
    norm = np.linalg.norm(estimated, axis=-1) * np.linalg.norm(reference, axis=-1)
    return np.sum(estimated * reference, axis=-1) / np.maximum(norm, 1e-9)


def _bin_rows(
    error, true, estimated_vector, reference_vector, valid, bins, direction=True
):
    rows = []
    for low, high in bins:
        mask = valid & in_bin(true, low, high)
        estimated = np.linalg.norm(estimated_vector[mask], axis=-1)
        rows.append(
            {
                "lower_mm": low,
                "upper_mm": high,
                "pairs": int(mask.sum()),
                "median_true_mm": _median(true[mask]),
                "median_estimated_mm": _median(estimated),
                "median_error_mm": _median(error[mask]),
                "p90_error_mm": _p90(error[mask]),
                "median_error_over_true": _median(
                    error[mask] / np.maximum(true[mask], 1e-9)
                ),
                "median_cosine": (
                    _median(_cosine(estimated_vector[mask], reference_vector[mask]))
                    if direction and low >= 10
                    else None
                ),
                "over_tolerance": int((error[mask] > TOLERANCE_MM).sum()),
                "zero_over_tolerance": int((true[mask] > TOLERANCE_MM).sum()),
                "beats_zero": (
                    float((error[mask] < true[mask]).mean()) if mask.any() else None
                ),
            }
        )
    return rows


def _cameras(record, root, observations):
    metadata = read_json(observations / f"{record['take_id']}.json")
    calibration = _read_calibration(
        root / record["calibration"], metadata["source_sha256"]["calibration"]
    )
    return [calibration[view["camera_serial"]] for view in record["views"]]


def summarize(records, design, observations, cutoffs):
    """Describe one split from measured takes without fitting any parameter."""
    root = Path(design["root"])
    by_take = {row["take_id"]: row for row in design["records"]}
    estimates = np.stack([row["xyz"] for row in records])  # take, method, 9, 2, 3
    reference = np.stack([row["reference"]["midpoint"][1] for row in records])
    groups = np.array([row["group"] for row in records])
    detections = np.stack([row["detections"] for row in records])  # take, view, 9
    pixels = np.stack([row["pixels"] for row in records])  # take, view, 9, 2, 2
    projected = np.stack(
        [
            np.stack(
                [
                    project_points(row["reference"]["midpoint"][1], camera)
                    for camera in _cameras(by_take[row["take_id"]], root, observations)
                ]
            )
            for row in records
        ]
    )
    ref_a, ref_b = window_pairs(reference)
    reference_change = ref_b - ref_a
    true = np.linalg.norm(reference_change, axis=-1)
    measured = np.isfinite(true)
    group = np.broadcast_to(groups[:, None, None, None], true.shape)
    view_multiple = detections.reshape(detections.shape[:2] + (3, 3)) > 1
    multiple = (view_multiple[..., :-1] | view_multiple[..., 1:]).any(axis=1)
    multiple = np.broadcast_to(multiple[..., None], true.shape)

    result = {
        "pairs": int(measured.sum()),
        "true_displacement_mm": {
            str(p): float(np.percentile(true[measured], p))
            for p in (10, 25, 50, 75, 90)
        },
        "fraction_below_mm": {
            str(t): float((true[measured] < t).mean()) for t in (5, 10, 25, 50, 100)
        },
        "zero_movement": {
            "median_error_mm": _median(true[measured]),
            "over_tolerance": int((true[measured] > TOLERANCE_MM).sum()),
            "fine": _bin_rows(
                true,
                true,
                np.zeros_like(reference_change),
                reference_change,
                measured,
                FINE_BINS,
                direction=False,
            ),
        },
        "methods": {},
        "groups": {},
    }
    for index, method in enumerate(METHODS):
        est_a, est_b = window_pairs(estimates[:, index])
        change = est_b - est_a
        error = np.linalg.norm(change - reference_change, axis=-1)
        valid = measured & np.isfinite(error)
        shared, moving, _ = offset_decomposition(est_a - ref_a, est_b - ref_b)
        position = (
            np.linalg.norm(est_a - ref_a, axis=-1)
            + np.linalg.norm(est_b - ref_b, axis=-1)
        ) / 2
        result["methods"][method] = {
            "pairs": int(valid.sum()),
            "median_error_mm": _median(error[valid]),
            "p90_error_mm": _p90(error[valid]),
            "over_tolerance": int((error[valid] > TOLERANCE_MM).sum()),
            "beats_zero": float((error[valid] < true[valid]).mean()),
            "median_shared_offset_mm": _median(shared[valid]),
            "median_offset_change_mm": _median(moving[valid]),
            "shared_share_of_squared_error": offset_decomposition(
                (est_a - ref_a)[valid], (est_b - ref_b)[valid]
            )[2],
            "rank_correlation_position_change": rank_correlation(
                position[valid], error[valid]
            ),
            "single_detection_median_mm": _median(error[valid & ~multiple]),
            "multiple_detection_median_mm": _median(error[valid & multiple]),
            "fine": _bin_rows(error, true, change, reference_change, valid, FINE_BINS),
            "coarse": _bin_rows(
                error, true, change, reference_change, valid, COARSE_BINS
            ),
        }
        if method == "two_view":
            two_view_error, two_view_valid = error, valid
    for name in np.unique(groups):
        mask = two_view_valid & (group == name)
        result["groups"][str(name)] = {
            "pairs": int(mask.sum()),
            "median_true_mm": _median(true[mask]),
            "two_view_median_error_mm": _median(two_view_error[mask]),
            "zero_over_tolerance": int((true[mask] > TOLERANCE_MM).sum()),
            "two_view_over_tolerance": int((two_view_error[mask] > TOLERANCE_MM).sum()),
        }

    distance = np.linalg.norm(pixels - projected, axis=-1)  # take, view, 9, side
    opposite = np.linalg.norm(pixels - projected[..., ::-1, :], axis=-1)
    separation = np.linalg.norm(projected[..., 0, :] - projected[..., 1, :], axis=-1)
    separation = np.broadcast_to(separation[..., None], distance.shape)
    pix_a, pix_b = window_pairs(pixels)
    pro_a, pro_b = window_pairs(projected)
    pixel_change_error = np.linalg.norm((pix_b - pix_a) - (pro_b - pro_a), axis=-1)
    true_pixel_change = np.linalg.norm(pro_b - pro_a, axis=-1)
    usable = np.isfinite(distance) & np.isfinite(opposite)
    separated = usable & (separation > SEPARATED_PX)
    nearer_opposite = separated & (opposite < distance)
    far = usable & (np.minimum(distance, opposite) > FAR_PX)
    flagged = (nearer_opposite | far).reshape(far.shape[:2] + (3, 3, 2))
    flagged = (flagged[:, :, :, :-1] | flagged[:, :, :, 1:]).any(axis=1)
    tail = two_view_valid & (two_view_error > TOLERANCE_MM)
    result["image"] = {
        "median_pixel_distance": _median(distance),
        "p90_pixel_distance": _p90(distance),
        "median_pixel_change_error": _median(pixel_change_error),
        "p90_pixel_change_error": _p90(pixel_change_error),
        "median_true_pixel_change": _median(true_pixel_change),
        "median_wrist_separation_px": _median(separation[usable]),
        "usable": int(usable.sum()),
        "separated": int(separated.sum()),
        "nearer_opposite_fraction": float(nearer_opposite.sum() / separated.sum()),
        "far_fraction": float(far.sum() / usable.sum()),
        "flagged_pairs": int((two_view_valid & flagged).sum()),
        "flagged_median_error_mm": _median(two_view_error[two_view_valid & flagged]),
        "unflagged_pairs": int((two_view_valid & ~flagged).sum()),
        "unflagged_median_error_mm": _median(two_view_error[two_view_valid & ~flagged]),
        "share_of_tail_flagged": float((tail & flagged).sum() / tail.sum()),
    }

    scores = {
        "confidence": np.stack([row["wrist_score"][2] for row in records]),
        "ray_gap": np.stack([row["ray_gap"][2] for row in records]),
    }
    result["policies"] = {}
    for name, values in scores.items():
        first, second = window_pairs(values[..., None])
        score = np.maximum(first, second)[..., 0]
        accepted = two_view_valid & (score <= cutoffs[name])
        result["policies"][name] = {
            "cutoff": cutoffs[name],
            "accepted": int(accepted.sum()),
            "over_tolerance": int((two_view_error[accepted] > TOLERANCE_MM).sum()),
            "median_true_accepted_mm": _median(true[accepted]),
            "median_true_rejected_mm": _median(true[two_view_valid & ~accepted]),
            "coarse": [
                {
                    "lower_mm": low,
                    "upper_mm": high,
                    "accepted": int((mask := accepted & in_bin(true, low, high)).sum()),
                    "over_tolerance": int((two_view_error[mask] > TOLERANCE_MM).sum()),
                }
                for low, high in COARSE_BINS
            ],
            "groups": {
                str(g): {
                    "accepted": int((mask := accepted & (group == g)).sum()),
                    "over_tolerance": int((two_view_error[mask] > TOLERANCE_MM).sum()),
                    "median_true_mm": _median(true[mask]),
                }
                for g in np.unique(groups)
            },
        }
    return result


def frozen_cutoffs(policy):
    return {
        name: policy["policy"][f"two_view/change/{name}"]["primary"]["midpoint"][
            "accept"
        ]
        for name in ("confidence", "ray_gap")
    }


def run(design_path, observations, analysis, output):
    design = read_json(design_path)
    design["sha256"] = sha256(design_path)
    policy_path = analysis / "policy.json"
    cutoffs = frozen_cutoffs(read_json(policy_path))
    output = local_output(Path(output))
    output.mkdir(parents=True, exist_ok=True)
    for split in SPLITS:
        records = list(measure_split(design, observations, split))
        summary = summarize(records, design, observations, cutoffs)
        summary["provenance"] = {
            "design_sha256": design["sha256"],
            "policy_sha256": sha256(policy_path),
            "status": "post hoc, descriptive",
        }
        write_json(output / f"{split}.json", summary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=Path("local/study/design.json"))
    parser.add_argument(
        "--observations", type=Path, default=Path("local/study/observations")
    )
    parser.add_argument("--analysis", type=Path, default=Path("local/study/analysis"))
    parser.add_argument("--output", type=Path, default=Path("local/study/movement"))
    args = parser.parse_args(argv)
    run(args.design, args.observations, args.analysis, args.output)


if __name__ == "__main__":
    main()
