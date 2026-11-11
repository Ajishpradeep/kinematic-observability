"""Prepare traceable two-view alignment samples from verified container candidates."""

import json
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np

from observability.assets import local_output, sha256

from .motive import load_positions
from .references import (
    FITTED_REFERENCE_SPECS,
    MARKER_REFERENCE_SPECS,
    fitted_joint_references,
    marker_joint_references,
)


def _direct_pair(record):
    videos = record["videos"]
    return bool(
        record["eligible_for_alignment_probe"]
        and len(videos) == 2
        and all(video["frame_delta_vs_body"] == 0 for video in videos)
        and all(abs(video["fps_delta_vs_export"]) < 0.01 for video in videos)
    )


def _candidates_per_session(validation_records):
    eligible = defaultdict(list)
    for record in validation_records:
        if _direct_pair(record):
            eligible[record["session_id"]].append(record)
    ordered = {}
    for session_id in sorted(eligible):
        records = sorted(eligible[session_id], key=lambda row: row["body_frames"])
        median = records[len(records) // 2]["body_frames"]
        ordered[session_id] = sorted(
            records,
            key=lambda row: (abs(row["body_frames"] - median), row["take_id"]),
        )
    return ordered


def _motion_centre(reference):
    xyz = reference["xyz"]
    valid = reference["valid"]
    displacement = np.linalg.norm(np.diff(xyz, axis=0), axis=2)
    pair_valid = valid[1:] & valid[:-1]
    displacement[~pair_valid] = np.nan
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        motion = np.nanmedian(displacement, axis=1)
    coverage = valid[1:].sum(axis=1)
    motion[coverage < 6] = np.nan
    if not np.isfinite(motion).any():
        raise ValueError("no frame has enough marker coverage for alignment")
    return int(np.nanargmax(motion)) + 1


def prepare_alignment_sample(
    manifest,
    input_validation,
    output_dir=Path("local/pilot/alignment"),
    window_frames=31,
    excluded_take_ids=(),
):
    """Extract lossless frame windows around motion, one take per session."""
    if window_frames < 9 or window_frames % 2 == 0:
        raise ValueError("window_frames must be an odd integer of at least nine")
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError("OpenCV is required to extract alignment frames") from error

    root = Path(manifest["root"])
    output_dir = local_output(Path(output_dir))
    image_dir = local_output(output_dir / "images")
    reference_dir = local_output(output_dir / "references")
    image_dir.mkdir(parents=True, exist_ok=True)
    reference_dir.mkdir(parents=True, exist_ok=True)
    manifest_by_take = {record["take_id"]: record for record in manifest["records"]}
    excluded_take_ids = set(excluded_take_ids)
    candidates = _candidates_per_session(
        [
            record
            for record in input_validation["records"]
            if record["take_id"] not in excluded_take_ids
        ]
    )
    required_markers = sorted(
        {marker for _, _, markers in MARKER_REFERENCE_SPECS for marker in markers}
    )
    sample_records = []
    selection_failures = {}
    for session_id, session_candidates in candidates.items():
        selected = None
        failed = 0
        for validation in session_candidates:
            record = manifest_by_take[validation["take_id"]]
            try:
                marker_data = load_positions(
                    root / record["body_csv"],
                    entity_type="Marker",
                    semantic_names=required_markers,
                )
                reference = marker_joint_references(
                    marker_data["positions"], marker_data["semantic_names"]
                )
                centre = _motion_centre(reference)
            except ValueError:
                failed += 1
                continue
            selected = (record, reference, centre, "marker_constructed")
            break
        selection_failures[session_id] = failed
        if selected is None:
            validation = session_candidates[len(session_candidates) // 2]
            record = manifest_by_take[validation["take_id"]]
            fitted_names = [name for _, _, name in FITTED_REFERENCE_SPECS]
            fitted = load_positions(
                root / record["body_csv"],
                entity_type="Bone",
                semantic_names=fitted_names,
            )
            reference = fitted_joint_references(
                fitted["positions"], fitted["semantic_names"]
            )
            centre = _motion_centre(reference)
            selected = (record, reference, centre, "motive_fitted_origins")
        record, reference, centre, reference_source = selected
        radius = window_frames // 2
        start = max(0, min(centre - radius, len(reference["xyz"]) - window_frames))
        frames = np.arange(start, start + window_frames, dtype=int)
        reference_path = local_output(
            reference_dir / "{}.npz".format(record["take_id"])
        )
        np.savez_compressed(
            reference_path,
            frames=frames,
            xyz_mm=reference["xyz"][frames],
            valid=reference["valid"][frames],
            coco17_indices=reference["coco17_indices"],
            names=np.asarray(reference["names"]),
            provenance=reference["provenance"],
        )
        camera_records = []
        for camera_index, video in enumerate(record["candidate_videos"]):
            video_path = root / video["path"]
            capture = cv2.VideoCapture(str(video_path))
            if not capture.isOpened():
                capture.release()
                raise ValueError("candidate video became unreadable")
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(frames[0]))
            images = []
            for frame in frames:
                decoded, image = capture.read()
                if not decoded or image is None:
                    capture.release()
                    raise ValueError("failed to decode selected alignment frame")
                image_path = local_output(
                    image_dir
                    / "{}-c{}-f{:06d}.png".format(
                        record["take_id"], camera_index, int(frame)
                    )
                )
                if not cv2.imwrite(str(image_path), image):
                    capture.release()
                    raise ValueError("failed to write lossless alignment frame")
                images.append(
                    {
                        "frame": int(frame),
                        "path": str(image_path.relative_to(Path.cwd())),
                        "sha256": sha256(image_path),
                    }
                )
            capture.release()
            camera_records.append(
                {
                    "camera_index": camera_index,
                    "camera_serial": video["camera_serial"],
                    "video_path": video["path"],
                    "images": images,
                }
            )
        sample_records.append(
            {
                "take_id": record["take_id"],
                "session_id": record["session_id"],
                "body_csv": record["body_csv"],
                "calibration_path": record["calibration_candidates"][0],
                "reference_path": str(reference_path.relative_to(Path.cwd())),
                "reference_source": reference_source,
                "frames": frames.tolist(),
                "cameras": camera_records,
            }
        )
    output = {
        "schema": "optitrack-alignment-sample-v1",
        "selection": "median-duration direct pair per opaque capture group",
        "excluded_take_count": len(excluded_take_ids),
        "selection_failures_before_valid_reference": selection_failures,
        "records": sample_records,
    }
    output_path = local_output(output_dir / "sample-private.json")
    output_path.write_text(json.dumps(output, indent=2) + "\n")
    output_path.chmod(0o600)
    return output
