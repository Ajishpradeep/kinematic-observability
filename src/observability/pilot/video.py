"""Video naming and metadata utilities for private OptiTrack manifests."""

import re
from pathlib import Path

_CAMERA_SERIAL = re.compile(r"\((C\d+)\)", re.IGNORECASE)


def video_take_stem(path):
    """Return the exact take portion preceding Motive's camera suffix."""
    stem = Path(path).stem
    boundary = stem.casefold().find("-camera")
    return stem[:boundary].strip() if boundary >= 0 else stem.strip()


def camera_serial(path):
    """Extract a Motive colour-camera serial when present."""
    match = _CAMERA_SERIAL.search(Path(path).name)
    return match.group(1).upper() if match else None


def probe_video(path):
    """Read container metadata without decoding or copying source frames."""
    try:
        import cv2
    except ImportError:
        return {"status": "reader_unavailable"}
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        capture.release()
        return {"status": "unreadable"}
    fourcc = int(capture.get(cv2.CAP_PROP_FOURCC))
    result = {
        "status": "readable",
        "width": int(round(capture.get(cv2.CAP_PROP_FRAME_WIDTH))),
        "height": int(round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))),
        "nominal_fps": float(capture.get(cv2.CAP_PROP_FPS)),
        "container_frames": int(round(capture.get(cv2.CAP_PROP_FRAME_COUNT))),
        "fourcc": "".join(chr((fourcc >> (8 * index)) & 0xFF) for index in range(4)),
    }
    capture.release()
    return result
