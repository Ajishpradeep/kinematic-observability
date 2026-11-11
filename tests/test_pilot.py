"""Numerical and privacy invariants for the expansion decision pilot."""

import tempfile
import unittest
from pathlib import Path

import numpy as np

from observability.pilot.bootstrap import bootstrap
from observability.pilot.calibration import project_points, world_to_camera
from observability.pilot.inventory import classify_csv, scan_optitrack
from observability.pilot.manifest import build_manifest
from observability.pilot.metrics import (
    observability_spectrum,
    response_curve,
    risk_coverage,
)
from observability.pilot.motive import load_positions
from observability.pilot.references import marker_joint_references, paired_midpoint
from observability.pilot.state import new_state, update_gate
from observability.pilot.triangulation import triangulate_rays
from observability.pilot.video import camera_serial, video_take_stem


class PilotTests(unittest.TestCase):
    def test_motive_parser_preserves_explicit_frame_gaps_and_missing_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.csv"
            path.write_text(
                "Format Version,1.25,Export Frame Rate,120,Length Units,Millimeters\n"
                "\n"
                ",Type,Bone,Bone,Bone,Marker,Marker,Marker\n"
                ",Name,Actor:LHand,,,LRSP,,\n"
                ",ID,1,1,1,2,2,2\n"
                ",Parent,,,,,,\n"
                ",,Position,Position,Position,Position,Position,Position\n"
                "Frame,Time (Seconds),X,Y,Z,X,Y,Z\n"
                "0,0.0,1,2,3,4,5,6\n"
                "2,0.02,7,8,9,,11,12\n"
            )
            result = load_positions(path, "Marker", ["LRSP"])
        self.assertEqual(result["positions"].shape, (3, 1, 3))
        np.testing.assert_allclose(result["positions"][0, 0], [4.0, 5.0, 6.0])
        self.assertTrue(np.isnan(result["positions"][1]).all())
        self.assertTrue(np.isnan(result["positions"][2, 0, 0]))

    def test_video_naming_uses_explicit_camera_boundary(self):
        path = Path("movement-Camera 1 (C12345).avi")
        self.assertEqual(video_take_stem(path), "movement")
        self.assertEqual(camera_serial(path), "C12345")

    def test_projection_identity_camera(self):
        camera = {
            "camera_axes_in_world": np.eye(3),
            "camera_position_mm": np.zeros(3),
            "K": np.array([[100.0, 0.0, 50.0], [0.0, 100.0, 40.0], [0.0, 0.0, 1.0]]),
            "distortion": np.zeros(5),
        }
        rotation, translation = world_to_camera(camera, "axes_transpose")
        np.testing.assert_allclose(rotation, np.eye(3))
        np.testing.assert_allclose(translation, np.zeros(3))
        projected = project_points([[10.0, 20.0, 100.0]], camera, "axes_transpose")
        np.testing.assert_allclose(projected, [[60.0, 60.0]])

    def test_ray_triangulation_recovers_known_intersection(self):
        point = np.array([0.5, 0.25, 3.0])
        first = np.array([-1.0, 0.0, 0.0])
        second = np.array([1.0, 0.0, 0.0])
        result = triangulate_rays(first, point - first, second, point - second)
        np.testing.assert_allclose(result["xyz_mm"], point, atol=1e-12)
        self.assertAlmostEqual(result["ray_gap_mm"], 0.0, places=12)

    def test_manifest_keeps_paths_private_and_ids_stable(self):
        Path("local").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as source_directory:
            source = Path(source_directory)
            session = source / "identifying-session"
            session.mkdir()
            body = session / "sensitive-take.csv"
            body.write_text(
                "Format Version,1.25,Total Frames in Take,2,"
                "Export Frame Rate,120\n"
                "\n,Type,Bone,Marker\n\n\n\n\n"
                "Frame,Time (Seconds),X,Y,Z,W\n"
            )
            (session / "sensitive-take-camera-one.avi").write_bytes(b"one")
            (session / "sensitive-take-camera-two.avi").write_bytes(b"two")
            with tempfile.TemporaryDirectory(dir="local") as output_directory:
                first = build_manifest(source, Path(output_directory))
                second = build_manifest(source, Path(output_directory))
                safe = str(first["summary"])
                self.assertNotIn("identifying", safe)
                self.assertNotIn("sensitive", safe)
                self.assertIn("sensitive", str(first["private"]))
                self.assertEqual(first["summary"]["takes"], 1)
                self.assertEqual(
                    first["private"]["records"][0]["take_id"],
                    second["private"]["records"][0]["take_id"],
                )

    def test_bootstrap_writes_only_private_state_without_selecting_a_study(self):
        Path("local").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory() as source_directory:
            source = Path(source_directory)
            session = source / "source-session"
            session.mkdir()
            (session / "camera.avi").write_bytes(b"data")
            with tempfile.TemporaryDirectory(dir="local") as output_directory:
                result = bootstrap(source, Path(output_directory))
                self.assertTrue(result["inventory_path"].is_file())
                self.assertTrue(result["state_path"].is_file())
                self.assertIsNone(result["state"]["selected_study"])
                self.assertEqual(result["manifest"]["summary"]["takes"], 0)
                self.assertEqual(
                    result["state"]["gates"]["manifest"]["status"], "in_progress"
                )

    def test_csv_classification_uses_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = root / "arbitrary-a.csv"
            body.write_text(
                "Format Version,1.25,Total Frames in Take,2,Export Frame Rate,120\n"
                "\n,Type,Bone,Marker\n\n\n\n\nFrame,Time (Seconds),X,Y,Z,W\n"
            )
            force = root / "arbitrary-b.csv"
            force.write_text(
                "Format Version,1.0\nDevice Name,Bertec 2\nMocapFrame,Fx,Fy,Fz\n"
            )
            self.assertEqual(classify_csv(body), "body")
            self.assertEqual(classify_csv(force), "force")

    def test_inventory_does_not_export_source_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = root / "identifying-session"
            session.mkdir()
            (session / "sensitive-video.avi").write_bytes(b"data")
            result = scan_optitrack(root)
        self.assertNotIn("identifying", str(result))
        self.assertNotIn("sensitive", str(result))
        self.assertEqual(result["sessions"][0]["session"], "S001")

    def test_midpoint_requires_both_direct_landmarks(self):
        first = np.array([[0.0, 0.0, 0.0], [np.nan, 0.0, 0.0]])
        second = np.array([[2.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
        result = paired_midpoint(first, second)
        np.testing.assert_array_equal(result["valid"], [True, False])
        np.testing.assert_allclose(result["xyz"][0], [1.0, 0.0, 0.0])
        self.assertTrue(np.isnan(result["xyz"][1]).all())
        self.assertEqual(result["provenance"].tolist(), ["paired_direct", "missing"])

    def test_marker_references_keep_surface_and_midpoint_provenance_separate(self):
        names = [
            "LCAJ",
            "RCAJ",
            "LHLE",
            "LHME",
            "RHLE",
            "RHME",
            "LRSP",
            "LUSP",
            "RRSP",
            "RUSP",
            "LFLE",
            "LFME",
            "RFLE",
            "RFME",
            "LFAL",
            "LTAM",
            "RFAL",
            "RTAM",
        ]
        positions = np.ones((2, len(names), 3))
        positions[1, names.index("LHME")] = np.nan
        result = marker_joint_references(positions, names)
        self.assertTrue(result["valid"][0].all())
        self.assertFalse(result["valid"][1, 2])
        self.assertEqual(result["provenance"][0], "direct_surface_marker")
        self.assertEqual(result["provenance"][2], "paired_anatomical_midpoint")

    def test_response_curve_detects_attenuation(self):
        reference = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        result = response_curve(reference, 0.5 * reference + 0.25)
        self.assertAlmostEqual(result["slope"], 0.5)
        self.assertAlmostEqual(result["intercept"], 0.25)
        self.assertAlmostEqual(result["r2"], 1.0)

    def test_lower_uncertainty_retains_lower_risk(self):
        result = risk_coverage([1.0, 3.0, 2.0], [0.1, 0.9, 0.5])
        np.testing.assert_allclose(result["risk"], [1.0, 1.5, 2.0])

    def test_observability_rank(self):
        result = observability_spectrum([[1.0, 0.0], [0.0, 0.0]])
        self.assertEqual(result["rank"], 1)
        self.assertTrue(np.isinf(result["condition"]))

    def test_state_selects_no_study_before_evidence(self):
        state = new_state()
        self.assertIsNone(state["selected_study"])
        self.assertTrue(
            all(gate["status"] == "pending" for gate in state["gates"].values())
        )

    def test_gate_completion_requires_dependencies_and_evidence(self):
        state = new_state()
        with self.assertRaises(ValueError):
            update_gate(state, "manifest", "complete", evidence=["inventory.json"])
        with self.assertRaises(ValueError):
            update_gate(state, "scope", "complete")
        update_gate(state, "scope", "complete", evidence=["scope.md"])
        update_gate(state, "manifest", "complete", evidence=["inventory.json"])
        self.assertEqual(state["gates"]["manifest"]["status"], "complete")


if __name__ == "__main__":
    unittest.main()
