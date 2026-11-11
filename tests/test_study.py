"""Controlled invariants for held-out wrist transfer and decision analysis."""

import unittest

import numpy as np

from observability.pilot.calibration import project_points, world_to_camera
from observability.pilot.triangulation import _world_ray
from observability.study.analyze import endpoint
from observability.study.design import schedule
from observability.study.measure import (
    DEPTH_ANCHOR_MM,
    estimate,
    on_depth_plane,
    projection_support,
)
from observability.study.metrics import (
    change_metrics,
    decisions,
    fit_policy,
    policy_outcomes,
    rank_correlation,
    risk_curve,
)
from observability.study.publication import group_labels
from observability.study.supplements.movement import (
    COARSE_BINS,
    frozen_cutoffs,
    in_bin,
    offset_decomposition,
    window_pairs,
)


class StudyTests(unittest.TestCase):
    def test_schedule_and_deltas_do_not_bridge_windows_or_wrists(self):
        np.testing.assert_array_equal(
            schedule(101), [[14, 20, 26], [44, 50, 56], [74, 80, 86]]
        )
        vector = np.zeros((1, 9, 2, 3))
        vector[0, :, 0, 0] = [0, 1, 3, 100, 101, 103, 200, 201, 203]
        vector[0, :, 1, 0] = [7, 9, 12, 0, 2, 5, 10, 12, 15]
        np.testing.assert_array_equal(
            endpoint(vector, "change", vector=True)[:, 0], [1, 2, 2, 3] * 3
        )
        np.testing.assert_array_equal(
            endpoint(vector, "change", outer=True, vector=True)[:, 0], [3, 5] * 3
        )
        vector[0, 1, 0] = np.nan
        self.assertEqual(
            np.isnan(endpoint(vector, "change", vector=True)[:, 0]).sum(), 2
        )
        self.assertEqual(
            np.isnan(endpoint(vector, "change", outer=True, vector=True)).sum(), 0
        )
        score = np.arange(18).reshape(1, 9, 2)
        np.testing.assert_array_equal(endpoint(score, "change")[:4], [2, 3, 4, 5])

    def test_depth_plane_and_two_ray_control(self):
        def camera(x):
            return {
                "camera_axes_in_world": np.diag([1.0, -1.0, -1.0]),
                "camera_position_mm": np.array([x, 1000.0, -2000.0]),
                "K": np.array([[800.0, 0, 500.0], [0, 800.0, 400.0], [0, 0, 1.0]]),
                "distortion": [0.05, -0.01, 0.001, 0, 0],
            }

        cameras = [camera(-500), camera(500)]
        points = np.array([[[50.0, 1050.0, 0.0], [120.0, 900.0, 300.0]]])
        pixels = np.stack([project_points(points, c) for c in cameras])
        xyz, score, gap = estimate(pixels, np.ones((2, 1, 2)), cameras)
        np.testing.assert_allclose(xyz[2], points, atol=1e-5)
        np.testing.assert_allclose(gap[2], 0, atol=1e-5)
        np.testing.assert_allclose(
            xyz[:2, 0, 0], np.repeat(points[:, :1, :], 2, axis=0)[:, 0], atol=1e-5
        )
        for index, c in enumerate(cameras):
            reconstructed = on_depth_plane(_world_ray(pixels[index, 0, 1], c), c)
            np.testing.assert_allclose(
                project_points(reconstructed, c), pixels[index, 0, 1], atol=1e-5
            )
            self.assertAlmostEqual(
                world_to_camera(c)[0][2] @ (reconstructed - DEPTH_ANCHOR_MM), 0
            )
        self.assertTrue((score == 0).all())
        scores = np.ones((2, 1, 2))
        scores[1, 0, 0] = np.nan
        xyz, _, _ = estimate(pixels, scores, cameras)
        self.assertTrue(np.isfinite(xyz[0, 0, 0]).all())
        self.assertTrue(np.isnan(xyz[1:, 0, 0]).all())

    def test_oracle_support_requires_both_image_rectangles(self):
        cameras = [{"width": 20, "height": 10}, {"width": 10, "height": 20}]
        pixels = np.array(
            [
                [[[9.0, 9.0], [1.0, 2.0], [2.0, 10.0], [2.0, 1.0]]],
                [[[9.0, 9.0], [10.0, 2.0], [3.0, 10.0], [np.nan, 1.0]]],
            ]
        )
        np.testing.assert_array_equal(
            projection_support(pixels, cameras), [[True, False, False, False]]
        )

    def test_transfer_gain_signed_projection_and_magnitude_are_distinct(self):
        reference = np.array([[10.0, 0.0, 0.0], [0.0, 20.0, 0.0], [0.0, 0.0, 30.0]])
        exact = change_metrics(reference, reference, 10)
        self.assertAlmostEqual(exact["vector_gain"], 1)
        self.assertAlmostEqual(exact["slope"], 1)
        self.assertAlmostEqual(exact["intercept_mm"], 0)
        self.assertAlmostEqual(exact["direction_cosine"]["median"], 1)
        flipped = change_metrics(reference, -2 * reference, 10)
        self.assertAlmostEqual(flipped["vector_gain"], -2)
        self.assertAlmostEqual(flipped["slope"], 2)
        self.assertAlmostEqual(flipped["direction_cosine"]["median"], -1)
        self.assertEqual(flipped["projection_positive_fraction"], 0)
        zero = change_metrics(reference, np.zeros_like(reference), 10)
        self.assertEqual(zero["direction_cosine"]["n"], 0)
        self.assertEqual(zero["moved_reference_n"], 3)
        self.assertEqual(zero["vector_gain"], 0)

    def test_risk_ties_and_failure_denominators(self):
        score = np.array([0.0, 0.0, 1.0, 2.0])
        loss = np.array([1.0, 3.0, 4.0, 8.0])
        curve = risk_curve(loss, score, 3, 8)
        self.assertEqual(curve, risk_curve(loss[[1, 0, 2, 3]], score, 3, 8))
        self.assertEqual(curve["curve"]["scheduled_coverage"], [0.25, 0.375, 0.5])
        self.assertEqual(curve["curve"]["failure_fraction"], [0.0, 1 / 3, 0.5])
        self.assertAlmostEqual(curve["aurc_over_mean"], (1 + 2 / 3 + 1) / 4)
        self.assertAlmostEqual(rank_correlation(score, score), 1)

    def test_policy_treats_accept_as_fixed_when_reference_changes(self):
        score = np.array([0.0, 0.0, 1.0, 2.0, np.nan])
        loss = np.array([0.0, 0.0, 100.0, 100.0, np.nan])
        groups = np.array(["a", "b", "a", "b", "b"])
        fitted = fit_policy(loss, score, groups, 50, 0.2, 0.1, 0.8)
        self.assertEqual(fitted["accept"], 0)
        self.assertEqual(fitted["development_coverage"], 0.4)
        decision = decisions(score, fitted)
        np.testing.assert_array_equal(decision, [2, 2, 1, 0, 0])
        self.assertEqual(
            policy_outcomes(decision, loss, 50)["accepted_failure_fraction"], 0
        )
        self.assertEqual(
            policy_outcomes(decision, loss + 60, 50)["accepted_failure_fraction"], 1
        )
        infeasible = fit_policy(loss + 60, score, groups, 50, 0.2, 0.1, 0.8)
        self.assertIsNone(infeasible["accept"])
        self.assertFalse((decisions(score, infeasible) == 2).any())

    def test_window_pairs_match_the_frozen_change_endpoints(self):
        values = np.arange(9 * 2 * 3, dtype=float).reshape(1, 9, 2, 3) ** 1.5
        first, second = window_pairs(values)
        np.testing.assert_allclose(
            (second - first).reshape(-1, 3),
            endpoint(values, "change", vector=True),
        )

    def test_shared_offset_cancels_and_power_identity_holds(self):
        rng = np.random.default_rng(3)
        first, second = rng.normal(size=(2, 50, 3))
        shared, moving, share = offset_decomposition(first, second)
        np.testing.assert_allclose(
            np.sum(first**2 + second**2, axis=-1), 2 * shared**2 + moving**2 / 2
        )
        np.testing.assert_allclose(moving, np.linalg.norm(second - first, axis=-1))
        constant = np.ones((4, 3))
        _, change, full = offset_decomposition(constant, constant)
        np.testing.assert_array_equal(change, 0)
        self.assertEqual(full, 1.0)
        self.assertTrue(0 < share < 1)

    def test_movement_bins_partition_and_frozen_cutoffs_are_read_not_fit(self):
        true = np.array([0.0, 9.99, 10.0, 49.9, 50.0, 1e4])
        counts = [int(in_bin(true, low, high).sum()) for low, high in COARSE_BINS]
        self.assertEqual(counts, [2, 2, 2])
        policy = {
            "policy": {
                f"two_view/change/{name}": {"primary": {"midpoint": {"accept": value}}}
                for name, value in (("confidence", 0.3), ("ray_gap", 60.0))
            }
        }
        self.assertEqual(frozen_cutoffs(policy), {"confidence": 0.3, "ray_gap": 60.0})

    def test_public_group_labels_hide_opaque_keys(self):
        analysis = {
            "development": {"groups": {"SESSION-b": {}, "SESSION-a": {}}},
            "confirmation": {"groups": {"SESSION-c": {}}},
        }
        labels = group_labels(analysis)
        self.assertEqual(labels[("development", "SESSION-a")], "D1")
        self.assertEqual(labels[("development", "SESSION-b")], "D2")
        self.assertEqual(labels[("confirmation", "SESSION-c")], "C1")
