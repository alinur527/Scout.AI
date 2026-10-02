"""Validated manual homography, adapted from the legacy FieldTransformer."""

import cv2
import numpy as np


class FieldTransformer:
    def __init__(self, source_points, field_length, field_width, frame_size=None):
        points = np.asarray(source_points, dtype=np.float32)
        if points.shape != (4, 2) or not np.isfinite(points).all():
            raise ValueError("Calibration requires four finite pixel coordinates")
        if field_length <= 0 or field_width <= 0:
            raise ValueError("Field dimensions must be positive")
        if frame_size and (
            np.any(points < 0)
            or np.any(points[:, 0] >= frame_size[0])
            or np.any(points[:, 1] >= frame_size[1])
        ):
            raise ValueError("All calibration corners must lie inside the video frame")
        if not cv2.isContourConvex(points) or abs(cv2.contourArea(points)) < 100:
            raise ValueError(
                "Choose four distinct corners in perimeter order; avoid crossing or collinear points"
            )
        self.source_points = points
        destination = np.array(
            [[0, 0], [field_length, 0], [field_length, field_width], [0, field_width]], dtype=np.float32
        )
        self.M = cv2.getPerspectiveTransform(points, destination)
        if not np.isfinite(self.M).all() or abs(np.linalg.det(self.M)) < 1e-10:
            raise ValueError("Calibration is degenerate")

    def transform_points(self, points):
        if len(points) == 0:
            return np.empty((0, 2))
        return cv2.perspectiveTransform(
            np.asarray(points, dtype=np.float32).reshape(-1, 1, 2), self.M
        ).reshape(-1, 2)

    def contains(self, point):
        return cv2.pointPolygonTest(self.source_points, tuple(map(float, point)), False) >= 0
