"""Validate candidate pair structure without treating nominal timing as alignment."""

import json
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

from observability.assets import local_output

from .calibration import parse_mcal
from .inventory import _body_metadata
from .video import probe_video


def _distribution(values):
    return {str(key): count for key, count in sorted(Counter(values).items())}


def validate_inputs(manifest, output_dir=Path("local/pilot")):
    """Check camera, calibration, container, rate, and frame-count compatibility."""
    root = Path(manifest["root"])
    output_dir = local_output(Path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    calibration_cache = {}
    video_cache = {}
    records = []
    for record in manifest["records"]:
        calibration_paths = [root / path for path in record["calibration_candidates"]]
        cameras = None
        calibration_error = None
        if len(calibration_paths) == 1:
            calibration_path = calibration_paths[0]
            try:
                if calibration_path not in calibration_cache:
                    calibration_cache[calibration_path] = parse_mcal(calibration_path)
                cameras = calibration_cache[calibration_path]
            except (OSError, ValueError, KeyError, ET.ParseError) as error:
                calibration_error = type(error).__name__

        rate, body_frames, rotation = _body_metadata(root / record["body_csv"])
        videos = []
        for candidate in record["candidate_videos"]:
            path = root / candidate["path"]
            if path not in video_cache:
                video_cache[path] = probe_video(path)
            metadata = video_cache[path]
            serial = candidate["camera_serial"]
            camera = cameras.get(serial) if cameras is not None and serial else None
            videos.append(
                {
                    "serial_present": serial is not None,
                    "serial_in_calibration": camera is not None,
                    "metadata": metadata,
                    "dimension_matches_calibration": bool(
                        camera is not None
                        and metadata.get("width") == camera["width"]
                        and metadata.get("height") == camera["height"]
                    ),
                    "frame_delta_vs_body": (
                        metadata.get("container_frames", 0) - body_frames
                        if metadata.get("status") == "readable"
                        else None
                    ),
                    "fps_delta_vs_export": (
                        metadata.get("nominal_fps", 0.0) - rate
                        if metadata.get("status") == "readable"
                        else None
                    ),
                }
            )
        serials = [
            candidate["camera_serial"]
            for candidate in record["candidate_videos"]
            if candidate["camera_serial"] is not None
        ]
        eligible = bool(
            len(videos) == 2
            and len(set(serials)) == 2
            and calibration_error is None
            and all(video["metadata"].get("status") == "readable" for video in videos)
            and all(video["serial_in_calibration"] for video in videos)
            and all(video["dimension_matches_calibration"] for video in videos)
        )
        records.append(
            {
                "take_id": record["take_id"],
                "session_id": record["session_id"],
                "body_frames": body_frames,
                "export_rate_hz": rate,
                "rotation_format": rotation,
                "calibration_candidates": len(calibration_paths),
                "calibration_error": calibration_error,
                "videos": videos,
                "unique_camera_serials": len(set(serials)),
                "eligible_for_alignment_probe": eligible,
            }
        )

    videos = [video for record in records for video in record["videos"]]
    frame_deltas = [
        video["frame_delta_vs_body"]
        for video in videos
        if video["frame_delta_vs_body"] is not None
    ]
    fps_deltas = [
        round(video["fps_delta_vs_export"], 3)
        for video in videos
        if video["fps_delta_vs_export"] is not None
    ]
    summary = {
        "schema": "optitrack-input-validation-summary-v1",
        "takes": len(records),
        "eligible_for_alignment_probe": sum(
            record["eligible_for_alignment_probe"] for record in records
        ),
        "candidate_video_count": _distribution(
            len(record["videos"]) for record in records
        ),
        "calibration_count": _distribution(
            record["calibration_candidates"] for record in records
        ),
        "unique_camera_serial_count": _distribution(
            record["unique_camera_serials"] for record in records
        ),
        "video_status": _distribution(
            video["metadata"].get("status", "unknown") for video in videos
        ),
        "dimension_match": _distribution(
            video["dimension_matches_calibration"] for video in videos
        ),
        "serial_in_calibration": _distribution(
            video["serial_in_calibration"] for video in videos
        ),
        "frame_delta_vs_body": _distribution(frame_deltas),
        "fps_delta_vs_export_hz": _distribution(fps_deltas),
        "qualifications": [
            "Container metadata does not prove decoded-frame completeness.",
            "Equal nominal rates and counts do not prove temporal alignment.",
            "Only exactly two calibrated readable cameras enter alignment probing.",
        ],
    }
    private = {
        "schema": "optitrack-input-validation-private-v1",
        "records": records,
    }
    private_path = local_output(output_dir / "input-validation-private.json")
    summary_path = local_output(output_dir / "input-validation-summary.json")
    private_path.write_text(json.dumps(private, indent=2) + "\n")
    private_path.chmod(0o600)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return {
        "private": private,
        "summary": summary,
        "private_path": private_path,
        "summary_path": summary_path,
    }
