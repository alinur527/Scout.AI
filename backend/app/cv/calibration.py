"""Validated manual homography, adapted from the legacy FieldTransformer."""

import cv2
import numpy as np


class FieldTransformer:
    def __init__(self, source_points, field_length, field_width, frame_size=None):
        points = np.asarray(source_points, dtype=np.float32)
        if points.shape != (4, 2) or not np.isfinite(points).all():
            raise ValueError("Calibration requires four finite pixel coordinates")
        if not np.isfinite([field_length, field_width]).all() or not (
            5 <= field_length <= 150 and 5 <= field_width <= 100
        ):
            raise ValueError("Rectangle dimensions must be finite: length 5–150 m, width 5–100 m")
        if frame_size and (
            np.any(points < 0)
            or np.any(points[:, 0] >= frame_size[0])
            or np.any(points[:, 1] >= frame_size[1])
        ):
            raise ValueError("All calibration corners must lie inside the video frame")
        if (
            len(np.unique(points, axis=0)) != 4
            or not cv2.isContourConvex(points)
            or abs(cv2.contourArea(points)) < 100
        ):
            raise ValueError(
                "Choose four distinct corners in perimeter order; avoid crossing or collinear points"
            )
        self.source_points = points
        self.dimensions = np.array([field_length, field_width])
        destination = np.array(
            [[0, 0], [field_length, 0], [field_length, field_width], [0, field_width]], dtype=np.float32
        )
        self.M = cv2.getPerspectiveTransform(points, destination)
        if (
            not np.isfinite(self.M).all()
            or abs(np.linalg.det(self.M)) < 1e-10
            or np.linalg.cond(self.M) > 1e8
        ):
            raise ValueError("Calibration is degenerate")

    def transform_points(self, points):
        if len(points) == 0:
            return np.empty((0, 2))
        array = np.asarray(points, dtype=np.float32)
        if array.ndim != 2 or array.shape[1] != 2 or not np.isfinite(array).all():
            raise ValueError("Ground coordinates must be finite pixel pairs")
        homogeneous = np.column_stack([array, np.ones(len(array))]) @ self.M.T
        if np.any(np.abs(homogeneous[:, 2]) < 1e-8):
            raise ValueError("Ground coordinate lies at the homography horizon")
        result = homogeneous[:, :2] / homogeneous[:, 2:]
        if not np.isfinite(result).all() or np.any(result < -1e-3) or np.any(result > self.dimensions + 1e-3):
            raise ValueError("Ground coordinates lie outside the calibrated rectangle")
        return result

    def contains(self, point):
        if np.asarray(point).shape != (2,) or not np.isfinite(point).all():
            return False
        return cv2.pointPolygonTest(self.source_points, tuple(map(float, point)), False) >= 0
