import numpy as np
import pytest

from app.cv.pitch_roi import PitchArea, validate_polygon


def test_polygon_uses_ground_point_and_keeps_goalkeeper_at_edge():
    area = PitchArea({"points": [[10, 10], [90, 10], [90, 90], [10, 90]], "margin_fraction": .01}, (100, 100))
    assert area.contains([10, 60]) and area.contains([9, 60])
    assert not area.contains([8.9, 60]) and not area.contains([50, 99])
    assert area.selection([[10, 60], [9, 60], [50, 99]]).tolist() == [True, True, False]
    assert not area.contains([np.nan, 50])


def test_valid_concave_polygon_and_zero_margin():
    area = PitchArea({"points": [[0, 0], [99, 0], [99, 99], [50, 50], [0, 99]], "margin_fraction": 0}, (100, 100))
    assert area.contains([50, 20]) and not area.contains([50, 90])


@pytest.mark.parametrize("points", [
    [], [[0, 0], [10, 10]], [[0, 0]] * 3,
    [[0, 0], [99, 99], [0, 99], [99, 0]],
    [[0, 0], [50, 0], [99, 0]], [[0, 0], [100, 0], [99, 99]],
    [[0, 0], [np.inf, 0], [99, 99]],
])
def test_invalid_polygon_rejected(points):
    with pytest.raises(ValueError):
        validate_polygon(points, (100, 100))


@pytest.mark.parametrize("margin", [-.01, .03, np.nan])
def test_invalid_margin_rejected(margin):
    with pytest.raises(ValueError):
        PitchArea({"points": [[0, 0], [99, 0], [99, 99]], "margin_fraction": margin}, (100, 100))
