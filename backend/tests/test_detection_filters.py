import cv2
import numpy as np
import pytest

from app.cv.pitch import pitch_box_selection
from app.cv.tiles import nms_indices, tile_windows


def test_pitch_envelope_keeps_players_goal_border_and_rejects_stand_people():
    image = np.zeros((240, 320, 3), np.uint8)
    cv2.rectangle(image, (15, 80), (305, 220), (30, 130, 30), -1)
    cv2.rectangle(image, (90, 110), (110, 160), (230, 230, 230), -1)
    boxes = [[90, 110, 110, 160], [20, 40, 40, 83], [90, 0, 110, 40], [10, 200, 30, 222]]
    keep, info = pitch_box_selection(image, boxes)
    assert info["status"] == "available"
    assert keep.tolist() == [True, True, False, True]


def test_unknown_scene_passes_through_but_invalid_boxes_do_not():
    image = np.zeros((240, 320, 3), np.uint8)
    boxes = [[10, 10, 20, 20], [np.nan, 10, 20, 20], [20, 10, 10, 20]]
    keep, info = pitch_box_selection(image, boxes)
    assert info["status"] == "unknown"
    assert keep.tolist() == [True, False, False]
    assert pitch_box_selection(image, [])[0].size == 0


def test_tiny_green_patch_does_not_authorize_scene_filter():
    image = np.zeros((240, 320, 3), np.uint8)
    cv2.rectangle(image, (20, 20), (40, 40), (30, 130, 30), -1)
    keep, info = pitch_box_selection(image, [[100, 100, 120, 120]])
    assert info["status"] == "unknown" and keep[0]


def test_tile_windows_cover_edges_and_overlap_seams():
    windows = tile_windows(1280, 720)
    assert len(windows) == 4
    assert windows[0] == (0, 0, 736, 414)
    assert windows[-1] == (544, 306, 1280, 720)
    coverage = np.zeros((720, 1280), dtype=int)
    for x1, y1, x2, y2 in windows:
        coverage[y1:y2, x1:x2] += 1
    assert coverage.min() == 1 and coverage.max() == 4
    with pytest.raises(ValueError):
        tile_windows(0, 10)


def test_tile_nms_retains_one_duplicate_and_distinct_nearby_people():
    boxes = [[10, 10, 30, 50], [11, 11, 31, 51], [32, 10, 52, 50], [np.nan, 0, 2, 2]]
    assert nms_indices(boxes, [0.7, 0.9, 0.8, 1]).tolist() == [1, 2]
    assert nms_indices([], []).size == 0
