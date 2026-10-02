"""Optional image-space playable area. Independent of metric calibration."""

import cv2
import numpy as np


def validate_polygon(points, frame_size):
    polygon = np.asarray(points, dtype=float)
    if polygon.ndim != 2 or polygon.shape[1:] != (2,) or not 3 <= len(polygon) <= 32:
        raise ValueError("Mark 3 to 32 playable-area boundary points in perimeter order")
    width, height = frame_size
    if not np.isfinite(polygon).all() or width <= 0 or height <= 0:
        raise ValueError("Playable-area points must be finite")
    if ((polygon < 0).any() or (polygon[:, 0] > width - 1).any() or (polygon[:, 1] > height - 1).any()):
        raise ValueError("Playable-area points must be inside the video frame")
    if len(np.unique(polygon, axis=0)) != len(polygon):
        raise ValueError("Playable-area boundary cannot contain duplicate points")

    def cross(a, b, c):
        u, v = b - a, c - a
        return float(u[0] * v[1] - u[1] * v[0])

    def intersects(a, b, c, d):
        ab_c, ab_d, cd_a, cd_b = cross(a, b, c), cross(a, b, d), cross(c, d, a), cross(c, d, b)
        if ab_c * ab_d < 0 and cd_a * cd_b < 0:
            return True
        return any(
            abs(value) <= 1e-8 and (p >= np.minimum(x, y) - 1e-8).all() and (p <= np.maximum(x, y) + 1e-8).all()
            for value, p, x, y in ((ab_c, c, a, b), (ab_d, d, a, b), (cd_a, a, c, d), (cd_b, b, c, d))
        )

    count = len(polygon)
    for i in range(count):
        for j in range(i + 1, count):
            if j == i + 1 or (i == 0 and j == count - 1):
                continue
            if intersects(polygon[i], polygon[(i + 1) % count], polygon[j], polygon[(j + 1) % count]):
                raise ValueError("Playable-area boundary cannot cross or touch itself")
    contour = polygon.astype(np.float32)
    if abs(cv2.contourArea(contour)) < width * height * .001:
        raise ValueError("Playable-area polygon is too small or collinear")
    return contour


class PitchArea:
    def __init__(self, specification, frame_size):
        self.polygon = validate_polygon(specification["points"], frame_size)
        fraction = specification.get("margin_fraction", .005)
        if not np.isfinite(fraction) or not 0 <= fraction <= .02:
            raise ValueError("Playable-area margin must be between 0 and 2% of image size")
        self.margin_px = fraction * max(frame_size)

    def contains(self, point):
        p = np.asarray(point, dtype=float)
        return bool(p.shape == (2,) and np.isfinite(p).all() and cv2.pointPolygonTest(self.polygon, tuple(p), True) >= -self.margin_px)

    def selection(self, points):
        return np.asarray([self.contains(point) for point in points], dtype=bool)
