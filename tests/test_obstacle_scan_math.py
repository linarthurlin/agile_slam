"""Numerical tests for filtering and transforming simulated LiDAR points."""
from pathlib import Path
import sys
import unittest

import numpy as np


sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "ros2_ws/src/agile_navigation/scripts"
    ),
)
from obstacle_scan_math import transform_finite_points


class ObstacleScanMathTests(unittest.TestCase):
    def test_invalid_points_are_removed_before_matrix_multiplication(self):
        points = np.array(
            [[1.0, 0.0, 0.0], [np.nan, 1.0, 0.0], [0.0, np.inf, 0.0]]
        )
        with np.errstate(invalid="raise"):
            transformed = transform_finite_points(
                points, np.eye(3), [0.0, 2.0, 0.0]
            )
        np.testing.assert_allclose(transformed, [[1.0, 2.0, 0.0]])

    def test_transform_applies_rotation_then_translation(self):
        points = np.array([[1.0, 0.0, 0.0]])
        rotation = np.array(
            [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
        )
        transformed = transform_finite_points(points, rotation, [3.0, 4.0, 0.0])
        np.testing.assert_allclose(transformed, [[3.0, 5.0, 0.0]])

    def test_nonfinite_transform_outputs_are_removed(self):
        points = np.array([[1.0, 0.0, 0.0]])
        with np.errstate(invalid="raise"):
            transformed = transform_finite_points(
                points, np.eye(3), [np.nan, 0.0, 0.0]
            )
        self.assertEqual(transformed.shape, (0, 3))


if __name__ == "__main__":
    unittest.main()
