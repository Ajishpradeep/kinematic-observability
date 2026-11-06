"""Inference through public pretrained YOLO26 and Fast SAM 3D Body interfaces.

No fine-tuned checkpoints or automatic anatomical remapping. Outputs retain native joints.
"""

import argparse
import json
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

import numpy as np

from observability.assets import local_output, sha256
from observability.verification import source_hashes

YOLO_REPO = "Ultralytics/YOLO26"
YOLO_REVISION = "070ac3c51435984d992ba92eb3f234daf4e4500d"
SAM_REPO = "facebook/sam-3d-body-dinov3"
SAM_REVISION = "11aaa346c7204874a1cbafe3d39a979080b2c55a"
FAST_SAM_URL = "https://github.com/yangtiming/Fast-SAM-3D-Body"


def verify_fast_sam(root):
    """Require an unchanged public source checkout, then record the exact revision."""
    root = root.resolve()

    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True
        ).strip()

    origin = git("remote", "get-url", "origin")
    if origin.endswith(".git"):
        origin = origin[:-4]
    if origin != FAST_SAM_URL or git(
        "status", "--porcelain", "--untracked-files=all", "--", "sam_3d_body"
    ):
        raise ValueError(
            "Fast SAM requires an unchanged checkout of the public upstream repository"
        )
    return {"repository": origin, "revision": git("rev-parse", "HEAD")}


def load_yolo(name, cache, device):
    from huggingface_hub import hf_hub_download
    from ultralytics import YOLO

    path = hf_hub_download(
        YOLO_REPO, name + ".pt", revision=YOLO_REVISION, cache_dir=cache
    )
    detector = YOLO(path)
    provenance = {
        "repository": YOLO_REPO,
        "revision": YOLO_REVISION,
        "filename": name + ".pt",
        "sha256": sha256(path),
        "ultralytics": metadata.version("ultralytics"),
        "device": device,
    }
    return detector, provenance


def load_fast_sam(root, cache, device):
    from huggingface_hub import hf_hub_download

    provenance = verify_fast_sam(root)
    sys.path.insert(0, str(root.resolve()))
    import sam_3d_body

    if root.resolve() not in Path(sam_3d_body.__file__).resolve().parents:
        raise ValueError("sam_3d_body resolved outside the selected public checkout")
    paths = {
        name: hf_hub_download(SAM_REPO, name, revision=SAM_REVISION, cache_dir=cache)
        for name in ("model.ckpt", "model_config.yaml", "assets/mhr_model.pt")
    }
    model, config = sam_3d_body.load_sam_3d_body(
        paths["model.ckpt"], device=device, mhr_path=paths["assets/mhr_model.pt"]
    )
    estimator = sam_3d_body.SAM3DBodyEstimator(model, config)
    provenance.update(
        checkpoint_repository=SAM_REPO,
        checkpoint_revision=SAM_REVISION,
        sha256={name: sha256(path) for name, path in paths.items()},
    )
    return estimator, provenance


def native_prediction(
    detector, image, device, threshold, estimator=None, intrinsics=None
):
    """Preserve per-image detections; indices are not temporal person identities."""
    result = detector.predict(str(image), device=device, conf=threshold, verbose=False)[
        0
    ]
    boxes = result.boxes.xyxy.cpu().numpy()
    arrays = {
        "image_size_hw": np.asarray(result.orig_shape, dtype=np.int64),
        "boxes_xyxy": boxes,
        "box_confidence": result.boxes.conf.cpu().numpy(),
        "coco17_xy_px": result.keypoints.xy.cpu().numpy(),
        "coco17_confidence": result.keypoints.conf.cpu().numpy(),
    }
    if estimator is not None:
        if len(boxes):
            kwargs = {"bboxes": boxes, "inference_type": "body"}
            if intrinsics is not None:
                import torch

                kwargs["cam_int"] = torch.as_tensor(
                    intrinsics, dtype=torch.float32, device=estimator.device
                )[None]
            people = estimator.process_one_image(str(image), **kwargs)
        else:
            people = []
        if len(people) != len(boxes):
            raise ValueError("SAM output count differs from supplied detections")
        arrays["mhr70_xy_px"] = (
            np.stack([p["pred_keypoints_2d"] for p in people])
            if people
            else np.empty((0, 70, 2))
        )
        arrays["mhr70_xyz_m"] = (
            np.stack([p["pred_keypoints_3d"] for p in people])
            if people
            else np.empty((0, 70, 3))
        )
        arrays["camera_translation_m"] = (
            np.stack([p["pred_cam_t"] for p in people]) if people else np.empty((0, 3))
        )
    if any(not np.isfinite(array).all() for array in arrays.values()):
        raise ValueError("nonfinite model output")
    return arrays


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", choices=["yolo26", "fast-sam3d"], required=True)
    parser.add_argument(
        "--yolo", choices=[f"yolo26{s}-pose" for s in "nsmlx"], default="yolo26n-pose"
    )
    parser.add_argument("--images", type=Path, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--fast-sam-root", type=Path)
    parser.add_argument(
        "--intrinsics",
        type=Path,
        help="Optional 3x3 K as JSON; applies to every supplied image",
    )
    parser.add_argument(
        "--cache", type=Path, default=Path("/tmp/observability-public-models")
    )
    args = parser.parse_args(argv)
    output = local_output(args.out)
    if output.exists():
        parser.error("output exists; choose a fresh run directory")
    if (
        Path.cwd().resolve() == args.cache.resolve()
        or Path.cwd().resolve() in args.cache.resolve().parents
    ):
        parser.error("model cache must remain outside the repository")
    if (
        not all(image.is_file() for image in args.images)
        or not 0 < args.confidence <= 1
    ):
        parser.error("images must exist and confidence must be in (0, 1]")
    if args.model == "fast-sam3d" and (not args.fast_sam_root or args.device == "cpu"):
        parser.error(
            "Fast SAM requires --fast-sam-root and a CUDA --device (for example cuda:0)"
        )
    intrinsics = (
        np.asarray(json.loads(args.intrinsics.read_text()), dtype=np.float32)
        if args.intrinsics
        else None
    )
    if intrinsics is not None and (
        intrinsics.shape != (3, 3) or not np.isfinite(intrinsics).all()
    ):
        parser.error("intrinsics must be a finite 3x3 JSON matrix")
    detector, yolo_provenance = load_yolo(args.yolo, str(args.cache), args.device)
    estimator, sam_provenance = (
        load_fast_sam(args.fast_sam_root, str(args.cache), args.device)
        if args.model == "fast-sam3d"
        else (None, None)
    )
    output.mkdir(parents=True)
    manifest = {
        "model": args.model,
        "detector": yolo_provenance,
        "sam": sam_provenance,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": metadata.version("torch"),
        "confidence": args.confidence,
        "intrinsics": intrinsics.tolist() if intrinsics is not None else None,
        "sam_mode": "body_without_hand_refinement" if estimator else None,
        "source_sha256": source_hashes(),
        "frames": [],
        "status": "running",
        "identity_tracking": False,
        "coordinate_note": "Native MHR output plus camera_translation_m gives camera-space metres; verify projection before reference scoring.",
    }
    try:
        for index, image in enumerate(args.images):
            arrays = native_prediction(
                detector, image, args.device, args.confidence, estimator, intrinsics
            )
            filename = f"frame-{index:06d}.npz"
            np.savez_compressed(output / filename, **arrays)
            manifest["frames"].append(
                {
                    "index": index,
                    "input_sha256": sha256(image),
                    "output": filename,
                    "sha256": sha256(output / filename),
                    "detections": len(arrays["boxes_xyxy"]),
                }
            )
        manifest["status"] = "complete"
    except BaseException:
        manifest["status"] = "failed"
        raise
    finally:
        (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
