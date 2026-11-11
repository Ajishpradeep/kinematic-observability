"""Stock public detector execution for the private alignment sample."""

import json
import platform
from pathlib import Path

import numpy as np

from observability.assets import local_output
from observability.models import load_yolo


def _select_largest_person(result):
    boxes = result.boxes.xyxy.cpu().numpy()
    if not len(boxes):
        return None
    area = np.maximum(0.0, boxes[:, 2] - boxes[:, 0]) * np.maximum(
        0.0, boxes[:, 3] - boxes[:, 1]
    )
    confidence = result.boxes.conf.cpu().numpy()
    selected = int(np.lexsort((confidence, area))[-1])
    return {
        "box": boxes[selected],
        "box_confidence": confidence[selected],
        "xy": result.keypoints.xy.cpu().numpy()[selected],
        "confidence": result.keypoints.conf.cpu().numpy()[selected],
        "detections": len(boxes),
    }


def run_alignment_detector(
    sample,
    output_dir=Path("local/pilot/alignment/yolo26n"),
    cache=Path("/tmp/observability-public-models"),
    device="cpu",
    threshold=0.10,
    batch_size=8,
):
    """Run stock YOLO26n-pose with a frozen largest-person selection rule."""
    output_dir = local_output(Path(output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for record in sample["records"]:
        for camera in record["cameras"]:
            for image in camera["images"]:
                items.append(
                    {
                        "take_id": record["take_id"],
                        "session_id": record["session_id"],
                        "reference_source": record["reference_source"],
                        "camera_index": camera["camera_index"],
                        "frame": image["frame"],
                        "path": image["path"],
                        "input_sha256": image["sha256"],
                    }
                )
    detector, provenance = load_yolo("yolo26n-pose", str(cache), device)
    xy = np.full((len(items), 17, 2), np.nan, dtype=np.float32)
    confidence = np.full((len(items), 17), np.nan, dtype=np.float32)
    boxes = np.full((len(items), 4), np.nan, dtype=np.float32)
    box_confidence = np.full(len(items), np.nan, dtype=np.float32)
    detections = np.zeros(len(items), dtype=np.int32)
    paths = [item["path"] for item in items]
    for start in range(0, len(paths), batch_size):
        stop = min(start + batch_size, len(paths))
        results = detector.predict(
            paths[start:stop],
            device=device,
            conf=threshold,
            imgsz=640,
            batch=batch_size,
            verbose=False,
        )
        if len(results) != stop - start:
            raise ValueError("detector result count differs from input count")
        for offset, result in enumerate(results):
            index = start + offset
            selected = _select_largest_person(result)
            if selected is None:
                continue
            xy[index] = selected["xy"]
            confidence[index] = selected["confidence"]
            boxes[index] = selected["box"]
            box_confidence[index] = selected["box_confidence"]
            detections[index] = selected["detections"]

    arrays_path = local_output(output_dir / "predictions.npz")
    np.savez_compressed(
        arrays_path,
        coco17_xy_px=xy,
        coco17_confidence=confidence,
        selected_box_xyxy=boxes,
        selected_box_confidence=box_confidence,
        detections=detections,
    )
    manifest = {
        "schema": "alignment-yolo26n-pose-v1",
        "model": provenance,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "threshold": threshold,
        "image_size": 640,
        "person_selection": "largest box; box confidence breaks exact area ties",
        "identity_tracking": False,
        "items": items,
        "arrays": str(arrays_path.relative_to(Path.cwd())),
        "detected_images": int(np.isfinite(boxes).all(axis=1).sum()),
    }
    manifest_path = local_output(output_dir / "manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
