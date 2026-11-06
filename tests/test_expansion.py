"""Check private outputs, neutral inventories and public-model boundaries without model downloads."""

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import torch

from observability.assets import inspect_asset, local_output
from observability.models import main, native_prediction, verify_fast_sam


class ExpansionTests(unittest.TestCase):
    def test_inventory_counts_without_names_or_symlink_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sensitive-name.avi").write_bytes(b"abc")
            (root / "reference.csv").write_text("header")
            (root / "loop").symlink_to(root, target_is_directory=True)
            result = inspect_asset({"id": "capture", "path": str(root)}, scan=True)
        self.assertEqual(result["files_by_extension"], {".avi": 1, ".csv": 1})
        self.assertEqual(result["bytes_by_extension"][".avi"], 3)
        self.assertNotIn("sensitive-name", str(result))
        self.assertTrue(result["complete"])

    def test_private_output_enforced(self):
        with self.assertRaises(ValueError):
            local_output(Path("results/predictions"))
        self.assertEqual(
            local_output(Path("local/predictions")),
            (Path.cwd() / "local/predictions").resolve(),
        )

    def test_custom_detector_checkpoint_not_accepted(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(
                [
                    "--model",
                    "yolo26",
                    "--yolo",
                    "custom.pt",
                    "--images",
                    "image.png",
                    "--out",
                    "local/predictions",
                ]
            )

    def test_fast_sam_checkout_must_match_public_upstream_and_be_clean(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.run(
                    ["git", "-C", str(root), *args], check=True, capture_output=True
                )

            git("init", "-q")
            git(
                "remote",
                "add",
                "origin",
                "https://github.com/yangtiming/Fast-SAM-3D-Body.git",
            )
            (root / "sam_3d_body").mkdir()
            (root / "sam_3d_body/__init__.py").write_text("")
            git("add", ".")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "-qm",
                "fixture",
            )
            self.assertEqual(
                verify_fast_sam(root)["repository"],
                "https://github.com/yangtiming/Fast-SAM-3D-Body",
            )
            (root / "sam_3d_body/__init__.py").write_text("modified")
            with self.assertRaises(ValueError):
                verify_fast_sam(root)

    def test_empty_detection_does_not_invoke_sam(self):
        result = SimpleNamespace(
            orig_shape=(20, 10),
            boxes=SimpleNamespace(xyxy=torch.empty(0, 4), conf=torch.empty(0)),
            keypoints=SimpleNamespace(
                xy=torch.empty(0, 17, 2), conf=torch.empty(0, 17)
            ),
        )
        detector = Mock()
        detector.predict.return_value = [result]
        estimator = Mock()
        arrays = native_prediction(detector, Path("image.png"), "cpu", 0.25, estimator)
        estimator.process_one_image.assert_not_called()
        self.assertEqual(arrays["mhr70_xyz_m"].shape, (0, 70, 3))

    def test_native_outputs_retain_joint_sets_and_translation(self):
        result = SimpleNamespace(
            orig_shape=(20, 10),
            boxes=SimpleNamespace(
                xyxy=torch.tensor([[0.0, 0.0, 10.0, 20.0]]), conf=torch.ones(1)
            ),
            keypoints=SimpleNamespace(xy=torch.zeros(1, 17, 2), conf=torch.ones(1, 17)),
        )
        detector = Mock()
        detector.predict.return_value = [result]
        estimator = Mock()
        estimator.process_one_image.return_value = [
            {
                "pred_keypoints_2d": np.zeros((70, 2)),
                "pred_keypoints_3d": np.ones((70, 3)),
                "pred_cam_t": np.array([0.0, 0.0, 3.0]),
            }
        ]
        arrays = native_prediction(detector, Path("image.png"), "cpu", 0.25, estimator)
        self.assertEqual(arrays["coco17_xy_px"].shape, (1, 17, 2))
        self.assertEqual(arrays["mhr70_xyz_m"].shape, (1, 70, 3))
        np.testing.assert_array_equal(arrays["camera_translation_m"], [[0, 0, 3]])
        self.assertEqual(
            estimator.process_one_image.call_args.kwargs["inference_type"], "body"
        )


if __name__ == "__main__":
    unittest.main()
