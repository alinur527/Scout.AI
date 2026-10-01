"""Confidence-aware ankle mean and deterministic bottom-centre fallback.

Kept unsmoothed: the football experiment found temporal smoothing increased
visual feet error. Physical-coordinate smoothing remains in MatchAnalytics.
"""

import numpy as np


def ground_point(box, keypoints=None, confidence=None):
    box = np.asarray(box, dtype=float)
    if box.shape != (4,) or not np.isfinite(box).all() or box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError("Detection requires a finite positive-area bounding box")
    xy = np.asarray(keypoints) if keypoints is not None else np.empty((0, 2))
    scores = np.asarray(confidence) if confidence is not None else np.empty(0)
    valid = []
    if xy.ndim == 2 and xy.shape[0] >= 17 and xy.shape[1] == 2 and scores.shape == (xy.shape[0],):
        valid = [xy[k] for k in (15, 16) if scores[k] >= 0.4 and np.isfinite(xy[k]).all()]
    return np.mean(valid, axis=0) if valid else np.array([(box[0] + box[2]) / 2, box[3]])
