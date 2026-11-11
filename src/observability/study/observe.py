"""Decode scheduled OptiTrack pixels and infer stock COCO17 observations."""

import argparse
import hashlib
import platform
from pathlib import Path

import numpy as np

from observability.assets import local_output, sha256
from observability.models import load_yolo
from observability.pilot.detector import _select_largest_person

from .design import read_json, write_json

BOX_CONFIDENCE = 0.10
IMAGE_SIZE = 640
WEIGHT_SHA256 = "eb3bb8268828aeaf515cec23a4bfafd793944a86fe9af94ba7823609c14522a9"


def infer_take(record, root, model, device):
    import cv2

    frames = [frame for window in record["windows"] for frame in window]
    shape = (2, len(frames))
    decoded = np.zeros(shape, dtype=bool)
    xy = np.full(shape + (17, 2), np.nan)
    confidence = np.full(shape + (17,), np.nan)
    boxes = np.full(shape + (5,), np.nan)
    detections = np.zeros(shape, dtype=int)
    pixel_hash = [[""] * len(frames) for _ in range(2)]
    decode_status = [[""] * len(frames) for _ in range(2)]
    for view_index, view in enumerate(record["views"]):
        capture = cv2.VideoCapture(str(root / view["path"]))
        images, indices = [], []
        try:
            for index, frame in enumerate(frames):
                if not capture.isOpened():
                    decode_status[view_index][index] = "unreadable"
                    continue
                if not capture.set(cv2.CAP_PROP_POS_FRAMES, frame):
                    decode_status[view_index][index] = "seek_failed"
                    continue
                ok, image = capture.read()
                after = capture.get(cv2.CAP_PROP_POS_FRAMES)
                if not ok or image is None:
                    decode_status[view_index][index] = "decode_failed"
                elif abs(after - frame - 1) > 0.01:
                    decode_status[view_index][index] = "unexpected_position"
                else:
                    decoded[view_index, index] = True
                    decode_status[view_index][index] = "decoded"
                    pixel_hash[view_index][index] = hashlib.sha256(
                        image.tobytes()
                    ).hexdigest()
                    images.append(image)
                    indices.append(index)
        finally:
            capture.release()
        if not images:
            continue
        predictions = model.predict(
            images,
            device=device,
            conf=BOX_CONFIDENCE,
            imgsz=IMAGE_SIZE,
            batch=len(images),
            verbose=False,
        )
        if len(predictions) != len(images):
            raise ValueError("detector result count differs from decoded frames")
        for index, result in zip(indices, predictions):
            selected = _select_largest_person(result)
            if selected is None:
                continue
            xy[view_index, index] = selected["xy"]
            confidence[view_index, index] = selected["confidence"]
            boxes[view_index, index, :4] = selected["box"]
            boxes[view_index, index, 4] = selected["box_confidence"]
            detections[view_index, index] = selected["detections"]
    return {
        "decoded": decoded,
        "xy": xy,
        "confidence": confidence,
        "boxes": boxes,
        "detections": detections,
        "frames": frames,
    }, {"pixel_sha256_bgr": pixel_hash, "decode_status": decode_status}


def run(design_path, output, cache, device, shard, shards, threads):
    import cv2
    import torch

    torch.set_num_threads(threads)
    cv2.setNumThreads(1)
    design = read_json(design_path)
    design_hash = sha256(design_path)
    root = Path(design["root"])
    output = local_output(Path(output))
    output.mkdir(exist_ok=True, parents=True)
    model, provenance = load_yolo("yolo26n-pose", str(cache), device)
    if provenance["sha256"] != WEIGHT_SHA256:
        raise ValueError("checkpoint differs from the pinned study weights")
    implementation = {
        str(path): sha256(path)
        for path in (
            Path(__file__).resolve().relative_to(Path.cwd()),
            Path("src/observability/models.py"),
            Path("src/observability/pilot/detector.py"),
        )
    }
    config = {
        "design_sha256": design_hash,
        "implementation_sha256": implementation,
        "model": provenance,
        "torch": torch.__version__,
        "opencv": cv2.__version__,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch_threads": threads,
        "box_confidence": BOX_CONFIDENCE,
        "image_size": IMAGE_SIZE,
        "person_selection": "largest box, score breaks area ties; no identity tracking",
        "preprocessing": "OpenCV decoded uint8 BGR; stock detector letterbox; no undistortion before inference",
    }
    records = [row for row in design["records"] if row["status"] == "scheduled"]
    calibrations = {}
    for index, record in enumerate(records[shard::shards], start=1):
        take = record["take_id"]
        manifest_path = output / f"{take}.json"
        arrays_path = output / f"{take}.npz"
        if manifest_path.exists():
            cached = read_json(manifest_path)
            if cached["config"] != config or cached["arrays_sha256"] != sha256(
                arrays_path
            ):
                raise ValueError("cached inference has different provenance")
            continue
        calibration = record["calibration"]
        if calibration not in calibrations:
            calibrations[calibration] = sha256(root / calibration)
        inputs = {
            "body_csv": sha256(root / record["body_csv"]),
            "calibration": calibrations[calibration],
            "videos": [sha256(root / view["path"]) for view in record["views"]],
        }
        arrays, metadata = infer_take(record, root, model, device)
        temporary = arrays_path.with_suffix(".tmp")
        with temporary.open("wb") as stream:
            np.savez_compressed(stream, **arrays)
        temporary.chmod(0o600)
        temporary.replace(arrays_path)
        write_json(
            manifest_path,
            {
                "config": config,
                "take_id": take,
                "source_sha256": inputs,
                "arrays_sha256": sha256(arrays_path),
                **metadata,
            },
        )
        if index % 5 == 0:
            print(f"shard {shard}: {index} scheduled takes processed", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", type=Path, default=Path("local/study/design.json"))
    parser.add_argument("--output", type=Path, default=Path("local/study/observations"))
    parser.add_argument(
        "--cache", type=Path, default=Path("/tmp/observability-public-models")
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards or args.threads < 1:
        parser.error("invalid shard or thread count")
    run(
        args.design,
        args.output,
        args.cache,
        args.device,
        args.shard,
        args.shards,
        args.threads,
    )
