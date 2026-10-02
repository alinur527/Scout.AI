import math
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from app.cv.analytics import MatchAnalytics
from app.cv.calibration import FieldTransformer
from app.cv.camera import CameraMotionMonitor
from app.cv.ground import ground_point
from app.cv.processor import VideoProcessor, inference_size_for_frame
from app.services.inference import report
from app.services.video import inspect_video


def test_known_linear_path_has_exact_distance_speed_without_smoothing():
    a = MatchAnalytics(7, smoothing_seconds=0)
    for t in [0, 0.1, 0.25, 0.5, 0.8, 1, 1.4, 1.8, 2]:
        a.update_metrics(1, [2 * t, 0], t)
    assert a.get_total_distance(1) == pytest.approx(4)
    assert max(a.player_speeds[1]) == pytest.approx(7.2)
    assert a.sprint_count[1] == 0
    assert len(a.segments[1]) == 1


def test_ema_matches_analytic_reference_and_is_fps_independent():
    n, delta, tau = 20, 0.2, 0.15
    ratio = math.exp(-delta / tau)
    expected = n * delta - delta * ratio * (1 - ratio**n) / (1 - ratio)
    for fps in [12, 30, 60]:
        a = MatchAnalytics(fps)
        for i in range(n + 1):
            a.update_metrics(1, [i * delta, 0], i * delta)
        assert a.get_total_distance(1) == pytest.approx(expected)


def test_gap_and_teleport_start_segments_and_never_add_distance_or_sprint():
    a = MatchAnalytics(30, smoothing_seconds=0)
    for t, point in [
        (0, [0, 0]),
        (0.1, [0.1, 0]),
        (2, [20, 0]),
        (2.1, [20.1, 0]),
        (2.2, [80, 0]),
        (2.3, [80.1, 0]),
    ]:
        a.update_metrics(1, point, t)
    assert a.get_total_distance(1) == pytest.approx(0.3)
    assert len(a.segments[1]) == 3
    assert a.rejected[1] == 2
    assert a.sprint_count[1] == 0
    assert a.player_speeds[1][2] == a.player_speeds[1][4] == 0


@pytest.mark.parametrize(
    "point,time",
    [([np.nan, 0], 0.2), ([1, 2, 3], 0.2), ([0, 0], np.nan), ([0, 0], np.inf), ([0, 0], None), ([], 0.2)],
)
def test_invalid_observation_cannot_poison_history_or_bridge_distance(point, time):
    a = MatchAnalytics(30, smoothing_seconds=0)
    a.update_metrics(1, [0, 0], 0)
    a.update_metrics(1, point, time)
    a.update_metrics(1, [1, 0], 0.3)
    assert a.get_total_distance(1) == 0
    assert np.isfinite(a.player_speeds[1]).all()
    assert len(a.segments[1]) == 2


def test_duplicate_and_backward_timestamps_are_ignored():
    a = MatchAnalytics(30, smoothing_seconds=0)
    a.update_metrics(1, [0, 0], 0)
    a.update_metrics(1, [100, 0], 0)
    a.update_metrics(1, [100, 0], -1)
    a.update_metrics(1, [0.2, 0], 0.1)
    assert a.get_total_distance(1) == pytest.approx(0.2)
    assert len(a.player_data[1]) == 2


def test_sprints_are_events_with_duration_and_return_below_threshold():
    a = MatchAnalytics(30, smoothing_seconds=0)
    x, t = 0, 0
    a.update_metrics(1, [x, 0], t)
    for speed, count in [(7, 20), (0, 3), (7, 5), (0, 3), (7, 20)]:
        for _ in range(count):
            t += 0.1
            x += speed * 0.1
            a.update_metrics(1, [x, 0], t)
    assert a.sprint_count[1] == 2  # Five fast intervals are shorter than .6s.


def test_short_track_and_missing_observations_do_not_create_sprints():
    a = MatchAnalytics(30, smoothing_seconds=0)
    a.update_metrics(1, [0, 0], 0)
    assert a.get_total_distance(1) == 0
    a.update_metrics(1, [4.2, 0], 0.6)
    assert a.get_total_distance(1) == 0
    assert a.sprint_count[1] == 0


@pytest.mark.parametrize("fps", [0, -1, np.nan, np.inf])
def test_invalid_fps(fps):
    with pytest.raises(ValueError):
        MatchAnalytics(fps)
    with pytest.raises(ValueError):
        CameraMotionMonitor(fps)


def test_missing_and_partial_ankles_use_defined_fallback():
    xy, scores = np.zeros((17, 2)), np.zeros(17)
    xy[15], xy[16] = [4, 18], [8, 19]
    box = [0, 0, 12, 20]
    np.testing.assert_equal(ground_point(box), [6, 20])
    np.testing.assert_equal(ground_point(box, xy, scores), [6, 20])
    scores[15] = 0.7
    np.testing.assert_equal(ground_point(box, xy, scores), [4, 18])
    scores[16] = 0.9
    np.testing.assert_equal(ground_point(box, xy, scores), [6, 18.5])
    xy[15] = [np.nan, 0]
    np.testing.assert_equal(ground_point(box, xy, scores), [8, 19])
    np.testing.assert_equal(ground_point(box, xy[:4], scores[:4]), [6, 20])
    with pytest.raises(ValueError):
        ground_point([0, 0, np.nan, 20])


@pytest.mark.parametrize(
    "corners",
    [
        [[0, 0]] * 4,
        [[0, 0], [100, 100], [100, 0], [0, 100]],
        [[0, 0], [10, 0], [20, 0], [30, 0]],
        [[0, 0], [100, 0], [30, 30], [0, 100]],
        [[0, 0], [100, 0], [100, np.nan], [0, 100]],
    ],
)
def test_invalid_calibration_polygon(corners):
    with pytest.raises(ValueError):
        FieldTransformer(corners, 40, 20)


@pytest.mark.parametrize("length,width", [(np.nan, 20), (40, np.inf), (100000, 20), (4, 20), (40, 101)])
def test_sane_calibration_dimensions(length, width):
    with pytest.raises(ValueError):
        FieldTransformer([[0, 0], [100, 0], [100, 100], [0, 100]], length, width)


def test_calibration_round_trip_bounds_and_invalid_transformed_coords():
    f = FieldTransformer([[10, 10], [110, 10], [110, 110], [10, 110]], 40, 20, (120, 120))
    np.testing.assert_allclose(f.transform_points([[60, 60], [110, 110]]), [[20, 10], [40, 20]])
    for points in [[[np.nan, 0]], [[0, 0]], [[10, 10, 10]]]:
        with pytest.raises(ValueError):
            f.transform_points(points)
    assert not f.contains([np.nan, 0])
    with pytest.raises(ValueError):
        FieldTransformer([[0, 0], [120, 0], [120, 110], [0, 110]], 40, 20, (120, 120))


def test_camera_fixed_translation_zoom_and_textureless():
    rng = np.random.default_rng(12)
    frame = rng.integers(0, 255, (240, 320, 3), dtype=np.uint8)
    for mode, expected in [
        ("fixed", "no_motion_detected"),
        ("pan", "moving"),
        ("zoom", "moving"),
        ("blank", "unknown"),
    ]:
        camera = CameraMotionMonitor(10)
        for i in range(30):
            if mode == "pan":
                image = cv2.warpAffine(frame, np.float32([[1, 0, i], [0, 1, 0]]), (320, 240))
            elif mode == "zoom":
                image = cv2.warpAffine(
                    frame, cv2.getRotationMatrix2D((160, 120), 0, 1 + i * 0.004), (320, 240)
                )
            else:
                image = np.zeros_like(frame) if mode == "blank" else frame
            camera.update(i, image)
        assert camera.summary()["status"] == expected


def job(camera="moving", stationary=True):
    return SimpleNamespace(
        id="fixture",
        selected_player_id=1,
        demo=False,
        video={"width": 200, "height": 200, "fps": 30, "duration_seconds": 3},
        tracks={
            "points": {"1": [[0, 10, 10], [0.1, 11, 10], [2, 100, 10], [2.1, 101, 10]]},
            "frames_processed": 90,
            "device": "cpu",
            "camera_motion": {"status": camera},
            "track_frame_counts": {"1": 4},
            "timestamps_reliable": True,
        },
        calibration={
            "points": [[0, 0], [199, 0], [199, 199], [0, 199]],
            "field_length": 40,
            "field_width": 20,
            "stationary_camera": stationary,
        },
    )


@pytest.mark.parametrize(
    "camera,stationary", [("moving", True), ("unknown", True), ("no_motion_detected", False)]
)
def test_physical_metrics_blocked_even_when_calibration_is_provided(camera, stationary):
    result = report(job(camera, stationary))
    assert result["metrics"]["total_distance_m"] is None
    assert result["calibration_provided"] and not result["calibrated"]
    assert result["coordinate_space"] == "image"
    assert len(result["movement_segments"]) == 2
    assert result["tracking_quality"]["observed_frame_coverage"] == pytest.approx(4 / 90)


def test_report_calibrated_gaps_and_invalid_samples_are_not_drawn_or_counted():
    fixture = job("no_motion_detected")
    result = report(fixture)
    assert result["calibrated"] and result["metrics"]["total_distance_m"] < 0.3
    assert len(result["movement_segments"]) == 2
    fixture.tracks["points"]["1"] = [[0, 10, 10], [0.1, np.nan, 10], [0.2, 11, 10]]
    result = report(fixture)
    assert len(result["movement_segments"]) == 2
    assert result["metrics"]["total_distance_m"] == 0
    fixture.tracks["points"]["1"] = [[0, 10, 10]]
    with pytest.raises(ValueError, match="at least two"):
        report(fixture)


def test_missing_detections_and_empty_decoding(monkeypatch):
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.device = "cpu"
    processor.model = Mock()
    processor.model.track.return_value = [None]
    detection = SimpleNamespace(tracker_id=None)
    empty = SimpleNamespace(tracker_id=None)
    processor.sv = SimpleNamespace(
        Detections=SimpleNamespace(from_ultralytics=lambda _: detection, empty=lambda: empty)
    )
    cap = Mock()
    cap.get.side_effect = lambda prop: 30 if prop == cv2.CAP_PROP_FPS else 0
    cap.read.side_effect = [(True, np.zeros((100, 100, 3), np.uint8)), (False, None)]
    monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap)
    result = list(processor.process_video("fixture"))
    assert len(result) == 1 and result[0][4] == []
    assert cap.release.called
    cap.read.side_effect = [(False, None)]
    with pytest.raises(ValueError, match="No frames"):
        list(processor.process_video("fixture"))


def test_video_zero_fps(monkeypatch, tmp_path):
    cap = Mock()
    cap.isOpened.return_value = True
    cap.get.return_value = 0
    monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap)
    with pytest.raises(ValueError, match="FPS"):
        inspect_video(tmp_path / "fixture.avi", SimpleNamespace())
    assert cap.release.called


def test_inference_resolution_preserves_hd_detail_and_caps_work():
    for shape, expected in [((360, 636, 3), 640), ((720, 1280, 3), 1280), ((2160, 3840, 3), 1280)]:
        assert inference_size_for_frame(np.empty(shape, dtype=np.uint8)) == expected


def test_unreliable_decoder_timestamps_block_physical_metrics():
    fixture = job("no_motion_detected")
    fixture.tracks["timestamps_reliable"] = False
    assert report(fixture)["metrics"]["total_distance_m"] is None


def test_decoder_timestamps_preserve_variable_intervals_and_flag_fallback(monkeypatch):
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.device = "cpu"
    processor.model = Mock()
    processor.model.track.return_value = [None]
    detection = SimpleNamespace(tracker_id=None)
    processor.sv = SimpleNamespace(
        Detections=SimpleNamespace(from_ultralytics=lambda _: detection, empty=lambda: detection)
    )
    for times, reliable in [([0, 50, 200], True), ([0, 0, 0], False)]:
        cap = Mock()
        pts = iter(times)
        cap.get.side_effect = lambda prop: 30 if prop == cv2.CAP_PROP_FPS else next(pts)
        frame = np.zeros((32, 32, 3), np.uint8)
        cap.read.side_effect = [(True, frame)] * 3 + [(False, None)]
        monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap)
        observations = list(processor.process_video("fixture"))
        assert processor.timestamps_reliable is reliable
        expected = [0, 0.05, 0.2] if reliable else [0, 1 / 30, 2 / 30]
        assert [row[1] for row in observations] == pytest.approx(expected)
