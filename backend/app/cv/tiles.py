"""Dependency-light tiled experiment geometry; no inference or tracker defaults."""

import numpy as np

from app.cv.validation import iou


def tile_windows(width, height, overlap=0.15):
    if width <= 0 or height <= 0 or not 0 <= overlap < 1:
        raise ValueError("Positive image size and overlap in [0,1) required")
    tw = min(width, int(np.ceil(width * (1 + overlap) / 2)))
    th = min(height, int(np.ceil(height * (1 + overlap) / 2)))
    return list(dict.fromkeys((x, y, x + tw, y + th) for y in (0, height - th) for x in (0, width - tw)))


def nms_indices(boxes, scores, threshold=0.5):
    boxes, scores = np.asarray(boxes).reshape(-1, 4), np.asarray(scores)
    if len(boxes) != len(scores) or not 0 <= threshold <= 1:
        raise ValueError("Box/score lengths or IoU threshold invalid")
    valid = (
        np.isfinite(boxes).all(axis=1)
        & np.isfinite(scores)
        & (boxes[:, 2] > boxes[:, 0])
        & (boxes[:, 3] > boxes[:, 1])
    )
    order = sorted(np.flatnonzero(valid), key=lambda index: (-scores[index], index))
    keep = []
    while order:
        index = order.pop(0)
        keep.append(index)
        order = [other for other in order if iou(boxes[index], boxes[other]) <= threshold]
    return np.asarray(keep, dtype=int)
