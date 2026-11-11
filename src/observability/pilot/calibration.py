"""Independent Motive calibration parsing and explicit projection conventions."""

import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np


def _decode_mcal(path):
    content = Path(path).read_bytes()
    for encoding in ("utf-16-le", "utf-8-sig", "utf-8"):
        try:
            text = content.decode(encoding)
            if "<" in text and "Camera" in text:
                return text.lstrip("\ufeff")
        except UnicodeDecodeError:
            continue
    raise ValueError("unsupported calibration encoding")


def parse_mcal(path):
    """Return standard-model cameras indexed by serial."""
    root = ET.fromstring(_decode_mcal(path))
    cameras = {}
    for element in root.findall(".//Camera"):
        serial = element.attrib.get("Serial", "").upper()
        attributes = element.find("Attributes")
        intrinsic = element.find("IntrinsicStandardCameraModel")
        extrinsic = element.find("Extrinsic")
        if not serial or attributes is None or intrinsic is None or extrinsic is None:
            continue
        rotation = np.array(
            [
                float(extrinsic.attrib["OrientMatrix{}".format(index)])
                for index in range(9)
            ]
        ).reshape(3, 3)
        cameras[serial] = {
            "width": int(round(float(attributes.attrib["ImagerPixelWidth"]))),
            "height": int(round(float(attributes.attrib["ImagerPixelHeight"]))),
            "K": np.array(
                [
                    [
                        float(intrinsic.attrib["HorizontalFocalLength"]),
                        0.0,
                        float(intrinsic.attrib["LensCenterX"]),
                    ],
                    [
                        0.0,
                        float(intrinsic.attrib["VerticalFocalLength"]),
                        float(intrinsic.attrib["LensCenterY"]),
                    ],
                    [0.0, 0.0, 1.0],
                ]
            ),
            "distortion": np.array(
                [
                    float(intrinsic.attrib["k1"]),
                    float(intrinsic.attrib["k2"]),
                    float(intrinsic.attrib["TangentialX"]),
                    float(intrinsic.attrib["TangentialY"]),
                    float(intrinsic.attrib["k3"]),
                ]
            ),
            "camera_position_mm": 1000.0
            * np.array(
                [
                    float(extrinsic.attrib["X"]),
                    float(extrinsic.attrib["Y"]),
                    float(extrinsic.attrib["Z"]),
                ]
            ),
            "camera_axes_in_world": rotation,
        }
    if not cameras:
        raise ValueError("calibration has no standard-model cameras")
    return cameras


def world_to_camera(camera, convention="motive_y_up"):
    """Return an explicit world-to-camera rotation and translation."""
    orientation = np.asarray(camera["camera_axes_in_world"], dtype=float)
    position = np.asarray(camera["camera_position_mm"], dtype=float)
    if convention == "motive_y_up":
        image_axis_flip = np.diag([1.0, -1.0, -1.0])
        rotation = (orientation @ image_axis_flip).T
    elif convention == "axes_transpose":
        rotation = orientation.T
    elif convention == "matrix_direct":
        rotation = orientation
    else:
        raise ValueError("unknown projection convention")
    translation = -rotation @ position
    return rotation, translation


def project_points(points_world_mm, camera, convention="motive_y_up"):
    """Project finite world points using the standard radial-tangential model."""
    points = np.asarray(points_world_mm, dtype=float)
    if points.shape[-1] != 3:
        raise ValueError("points must have shape (..., 3)")
    flat = points.reshape(-1, 3)
    output = np.full((len(flat), 2), np.nan, dtype=float)
    finite = np.isfinite(flat).all(axis=1)
    rotation, translation = world_to_camera(camera, convention)
    camera_points = flat[finite] @ rotation.T + translation
    forward = camera_points[:, 2] > 0
    if forward.any():
        selected = camera_points[forward]
        x = selected[:, 0] / selected[:, 2]
        y = selected[:, 1] / selected[:, 2]
        k1, k2, p1, p2, k3 = camera["distortion"]
        radius2 = x * x + y * y
        radial = 1.0 + k1 * radius2 + k2 * radius2**2 + k3 * radius2**3
        distorted_x = x * radial + 2.0 * p1 * x * y + p2 * (radius2 + 2.0 * x * x)
        distorted_y = y * radial + p1 * (radius2 + 2.0 * y * y) + 2.0 * p2 * x * y
        homogeneous = np.column_stack(
            (distorted_x, distorted_y, np.ones_like(distorted_x))
        )
        pixels = homogeneous @ np.asarray(camera["K"], dtype=float).T
        valid_indices = np.flatnonzero(finite)[forward]
        output[valid_indices] = pixels[:, :2]
    return output.reshape(points.shape[:-1] + (2,))
