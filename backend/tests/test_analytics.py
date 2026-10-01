import numpy as np
import pytest

from app.cv.analytics import MatchAnalytics
from app.cv.calibration import FieldTransformer


def test_homography_and_invalid_corners():
    transform = FieldTransformer([[10, 10], [210, 10], [210, 110], [10, 110]], 40, 20)
    np.testing.assert_allclose(transform.transform_points([[110, 60]]), [[20, 10]], atol=1e-4)
    with pytest.raises(ValueError):
        FieldTransformer([[0, 0]] * 4, 40, 20)


def test_timestamps_sprints_short_tracks_and_jumps():
    analytics = MatchAnalytics(30)
    for i in range(30):
        analytics.update_metrics(1, [i * 0.7, 0], i / 10)
    assert 18 < analytics.get_total_distance(1) < 21
    assert 24 < max(analytics.player_speeds[1]) < 26
    assert analytics.sprint_count[1] == 1
    before = analytics.get_total_distance(1)
    analytics.update_metrics(1, [100, 0], 3)
    assert analytics.get_total_distance(1) == before
    assert analytics.rejected[1] == 1
    analytics.update_metrics(1, [101, 0], 10)
    assert analytics.get_total_distance(1) == before
    short = MatchAnalytics(20)
    short.update_metrics(2, [0, 0], 0)
    short.update_metrics(2, [0.1, 0], 0.1)
    assert short.get_total_distance(2) > 0
    with pytest.raises(ValueError):
        MatchAnalytics(0)
