"""Score projection conventions and frame offsets on frozen alignment inputs."""

import json
from collections import Counter
from pathlib import Path

import numpy as np

from observability.assets import local_output

from .calibration import parse_mcal, project_points

CONVENTIONS = ("motive_y_up", "axes_transpose", "matrix_direct")
SHIFTS = tuple(range(-5, 6))
JOINT_CONFIDENCE = 0.25
ACCEPTANCE = {
    "marker_median_px": 50.0,
    "marker_p90_px": 100.0,
    "best_shift_abs_frames": 1,
    "views_with_small_shift_fraction": 0.80,
    "zero_shift_regret_px": 5.0,
    "alternative_error_ratio": 2.0,
}


def _score(projected, reference_valid, detected, confidence, shift):
    errors = []
    n_frames = len(projected)
    for detected_index in range(n_frames):
        reference_index = detected_index + shift
        if reference_index < 0 or reference_index >= n_frames:
            continue
        valid = (
            reference_valid[reference_index]
            & np.isfinite(projected[reference_index]).all(axis=1)
            & np.isfinite(detected[detected_index]).all(axis=1)
            & (confidence[detected_index] >= JOINT_CONFIDENCE)
        )
        valid[:2] = False
        if valid.any():
            errors.extend(
                np.linalg.norm(
                    detected[detected_index, valid] - projected[reference_index, valid],
                    axis=1,
                ).tolist()
            )
    if not errors:
        return {"n": 0, "median_px": None, "p90_px": None, "mean_px": None}
    values = np.asarray(errors)
    return {
        "n": len(errors),
        "median_px": float(np.median(values)),
        "p90_px": float(np.percentile(values, 90)),
        "mean_px": float(np.mean(values)),
    }


def score_alignment(
    sample,
    detector_manifest,
    output=Path("local/pilot/alignment/score.json"),
):
    """Compare fixed projection conventions and offsets, then apply frozen gates."""
    output = local_output(Path(output))
    root = Path(
        json.loads(Path("local/pilot/manifest-private.json").read_text())["root"]
    )
    predictions = np.load(detector_manifest["arrays"])
    detected_xy = predictions["coco17_xy_px"]
    detected_confidence = predictions["coco17_confidence"]
    item_lookup = {
        (item["take_id"], item["camera_index"], item["frame"]): index
        for index, item in enumerate(detector_manifest["items"])
    }
    results = []
    for record in sample["records"]:
        reference = np.load(record["reference_path"])
        frames = reference["frames"]
        xyz = reference["xyz_mm"]
        valid = reference["valid"]
        coco_indices = reference["coco17_indices"]
        calibration = parse_mcal(root / record["calibration_path"])
        for camera in record["cameras"]:
            indices = [
                item_lookup[(record["take_id"], camera["camera_index"], int(frame))]
                for frame in frames
            ]
            detector_xy = detected_xy[indices][:, coco_indices]
            detector_conf = detected_confidence[indices][:, coco_indices]
            camera_model = calibration[camera["camera_serial"]]
            scores = {}
            for convention in CONVENTIONS:
                projected = project_points(xyz, camera_model, convention)
                scores[convention] = {
                    str(shift): _score(
                        projected, valid, detector_xy, detector_conf, shift
                    )
                    for shift in SHIFTS
                }
            expected = scores["motive_y_up"]
            finite_shifts = [
                shift
                for shift in SHIFTS
                if expected[str(shift)]["median_px"] is not None
            ]
            best_shift = min(
                finite_shifts,
                key=lambda shift: expected[str(shift)]["median_px"],
            )
            results.append(
                {
                    "take_id": record["take_id"],
                    "session_id": record["session_id"],
                    "camera_index": camera["camera_index"],
                    "reference_source": record["reference_source"],
                    "scores": scores,
                    "best_expected_shift": best_shift,
                }
            )

    marker_results = [
        result
        for result in results
        if result["reference_source"] == "marker_constructed"
    ]
    expected_zero = [
        result["scores"]["motive_y_up"]["0"]["median_px"] for result in marker_results
    ]
    expected_p90 = [
        result["scores"]["motive_y_up"]["0"]["p90_px"] for result in marker_results
    ]
    alternative_zero = {
        convention: [
            result["scores"][convention]["0"]["median_px"]
            for result in marker_results
            if result["scores"][convention]["0"]["median_px"] is not None
        ]
        for convention in CONVENTIONS[1:]
    }
    best_shifts = [result["best_expected_shift"] for result in marker_results]
    best_medians = [
        result["scores"]["motive_y_up"][str(result["best_expected_shift"])]["median_px"]
        for result in marker_results
    ]
    pooled_expected = float(np.median(expected_zero))
    finite_alternatives = [
        value
        for values in alternative_zero.values()
        for value in values
        if value is not None
    ]
    convention_ratio = (
        float(np.median(finite_alternatives)) / pooled_expected
        if finite_alternatives
        else None
    )
    small_shift_fraction = float(
        np.mean(np.abs(best_shifts) <= ACCEPTANCE["best_shift_abs_frames"])
    )
    zero_regret = float(np.median(np.asarray(expected_zero) - np.asarray(best_medians)))
    gates = {
        "projection_convention": convention_ratio is None
        or convention_ratio >= ACCEPTANCE["alternative_error_ratio"],
        "marker_pixel_median": pooled_expected <= ACCEPTANCE["marker_median_px"],
        "marker_pixel_p90": float(np.median(expected_p90))
        <= ACCEPTANCE["marker_p90_px"],
        "timing_small_shift": small_shift_fraction
        >= ACCEPTANCE["views_with_small_shift_fraction"],
        "timing_zero_regret": zero_regret <= ACCEPTANCE["zero_shift_regret_px"],
    }
    summary = {
        "schema": "optitrack-alignment-score-v1",
        "frozen_acceptance": ACCEPTANCE,
        "marker_views": len(marker_results),
        "fitted_views": len(results) - len(marker_results),
        "expected_zero_median_px": pooled_expected,
        "expected_zero_median_p90_px": float(np.median(expected_p90)),
        "alternative_to_expected_error_ratio": convention_ratio,
        "best_shift_distribution": {
            str(key): value for key, value in sorted(Counter(best_shifts).items())
        },
        "small_shift_fraction": small_shift_fraction,
        "zero_shift_regret_px": zero_regret,
        "gates": gates,
        "all_required_gates_pass": all(gates.values()),
        "results": results,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    return summary
