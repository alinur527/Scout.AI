"""Conservative image-space grass envelope, independent of physical calibration.

Unknown scenes pass through. This is a scene filter, not a football-player classifier.
"""

import cv2
import numpy as np


def pitch_envelope(frame):
    height, width = frame.shape[:2]
    scale = min(1.0, 640 / width)
    image = cv2.resize(frame, (round(width * scale), round(height * scale)))
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    green = cv2.inRange(hsv, np.array([35, 45, 25]), np.array([95, 255, 255]))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    green = cv2.morphologyEx(green, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, {"status": "unknown", "reason": "no_green_region"}
    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour) / green.size
    if area < 0.05:
        return None, {"status": "unknown", "reason": "insufficient_green_area"}
    mask = np.zeros_like(green)
    cv2.fillConvexPoly(mask, cv2.convexHull(contour), 255)
    # Include field borders, goal mouths and uncertain bbox bottoms near grass.
    radius = max(8, round(image.shape[0] * 0.02))
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * radius + 1,) * 2))
    mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_NEAREST)
    return mask, {"status": "available", "green_area_fraction": area}


def pitch_box_selection(frame, boxes):
    boxes = np.asarray(boxes, dtype=float).reshape(-1, 4)
    valid = np.isfinite(boxes).all(axis=1) & (boxes[:, 2] > boxes[:, 0]) & (boxes[:, 3] > boxes[:, 1])
    mask, info = pitch_envelope(frame)
    if mask is None:
        return valid, info
    height, width = mask.shape
    indices = np.flatnonzero(valid)
    feet = np.column_stack(((boxes[indices, 0] + boxes[indices, 2]) / 2, boxes[indices, 3]))
    inside_image = (feet[:, 0] >= 0) & (feet[:, 0] < width) & (feet[:, 1] >= 0) & (feet[:, 1] <= height)
    keep = np.zeros(len(boxes), dtype=bool)
    indices, feet = indices[inside_image], feet[inside_image]
    x = np.clip(feet[:, 0].astype(int), 0, width - 1)
    y = np.clip(feet[:, 1].astype(int), 0, height - 1)
    keep[indices] = mask[y, x] != 0
    return keep, info
