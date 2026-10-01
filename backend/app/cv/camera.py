"""Conservative background-motion veto; never compensates physical coordinates.

No-motion-detected is not proof of a fixed camera. Physical estimates additionally
require the uploader's explicit stationary-camera confirmation. Weak estimates
remain unknown and cannot authorize physical metrics.
"""

import math

import cv2
import numpy as np


class CameraMotionMonitor:
    def __init__(self, fps):
        if not math.isfinite(fps) or fps <= 0:
            raise ValueError("FPS must be positive")
        self.interval = max(1, round(fps / 5))
        self.previous = self.mask = None
        self.cumulative = np.eye(3)
        self.samples = self.valid_pairs = 0
        self.centres, self.scales, self.angles = [], [], []

    def update(self, index, frame, boxes=()):
        if index % self.interval:
            return
        ratio = min(1, 640 / frame.shape[1])
        gray = cv2.cvtColor(
            cv2.resize(frame, (round(frame.shape[1] * ratio), round(frame.shape[0] * ratio))),
            cv2.COLOR_BGR2GRAY,
        )
        mask = np.full_like(gray, 255)
        for box in boxes:
            x1, y1, x2, y2 = np.round(np.asarray(box) * ratio).astype(int)
            cv2.rectangle(
                mask,
                (max(0, x1 - 5), max(0, y1 - 5)),
                (min(gray.shape[1] - 1, x2 + 5), min(gray.shape[0] - 1, y2 + 5)),
                0,
                -1,
            )
        if self.previous is not None:
            self.samples += 1
            points = cv2.goodFeaturesToTrack(self.previous, 400, 0.01, 8, mask=self.mask)
            if points is not None and len(points) >= 20:
                current, valid, _ = cv2.calcOpticalFlowPyrLK(self.previous, gray, points, None)
                if current is not None:
                    valid = valid.ravel().astype(bool)
                    before, after = points[valid], current[valid]
                    if len(before) >= 20:
                        affine, inliers = cv2.estimateAffinePartial2D(
                            before, after, method=cv2.RANSAC, ransacReprojThreshold=2
                        )
                        if affine is not None and inliers.sum() >= 20 and inliers.mean() >= 0.6:
                            transform = np.vstack([affine, [0, 0, 1]])
                            if np.isfinite(transform).all():
                                self.cumulative = transform @ self.cumulative
                                centre = np.array([gray.shape[1] / 2, gray.shape[0] / 2, 1])
                                self.centres.append((self.cumulative @ centre - centre)[:2])
                                self.scales.append(float(np.linalg.norm(self.cumulative[:2, 0])))
                                self.angles.append(
                                    math.degrees(math.atan2(self.cumulative[1, 0], self.cumulative[0, 0]))
                                )
                                self.valid_pairs += 1
        self.previous, self.mask = gray, mask

    def summary(self):
        shift = max((float(np.linalg.norm(p)) for p in self.centres), default=0)
        scale = max((abs(s - 1) for s in self.scales), default=0)
        rotation = max((abs(a) for a in self.angles), default=0)
        # 3px at a max-640px working image, 2% zoom, or one degree rotation.
        motion = shift > 3 or scale > 0.02 or rotation > 1
        enough = self.valid_pairs >= 8 and self.valid_pairs >= self.samples * 0.6
        status = "moving" if motion else "no_motion_detected" if enough else "unknown"
        return {
            "status": status,
            "valid_pairs": self.valid_pairs,
            "sample_pairs": self.samples,
            "max_shift_working_px": round(shift, 3),
            "max_scale_change": round(scale, 5),
            "max_rotation_degrees": round(rotation, 3),
            "method": "masked sparse optical flow / RANSAC affine veto at 5 Hz, max width 640",
        }
