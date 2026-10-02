import numpy as np
import pytest

from app.cv.continuity import TrackEndpoints, continuity_result, link_tracklets, merge_track_data, torso_histogram


def add_track(endpoints, identity, start, *, x=10, velocity=0, histogram=None, count=3, height=40):
    if histogram is None:
        histogram = [1.0] + [0.0] * 31
    for i in range(count):
        t = start + i * .04
        point = np.array([x + velocity * i * .04, 70.0])
        box = np.array([point[0] - 5, 70 - height, point[0] + 5, 70.0])
        endpoints.add(identity, t, point, box, histogram)


def test_disjoint_short_unambiguous_tracklets_link_and_preserve_samples():
    endpoints = TrackEndpoints()
    add_track(endpoints, 1, 0)
    add_track(endpoints, 2, .2, x=11)
    aliases, links = link_tracklets(endpoints)
    assert aliases == {1: 1, 2: 1} and len(links) == 1
    a, b = [[0, 10, 70], [.08, 10, 70]], [[.2, 11, 70], [.28, 11, 70]]
    merged, gallery, counts = merge_track_data(
        {"1": a, "2": b}, {"1": {"id": 1}, "2": {"id": 2}}, {"1": 3, "2": 4}, aliases
    )
    assert merged == {"1": a + b} and a == [[0, 10, 70], [.08, 10, 70]]
    assert counts == {"1": 7} and gallery["1"]["id"] == 1


@pytest.mark.parametrize("case", ["overlap", "long_gap", "far", "wrong_kit", "scale", "short", "invalid_appearance", "opposite_motion"])
def test_uncertain_links_are_rejected(case):
    endpoints = TrackEndpoints()
    add_track(endpoints, 1, 0, velocity=30 if case == "opposite_motion" else 0)
    options = {"x": 12}
    start = .2
    if case == "overlap":
        start = .04
    elif case == "long_gap":
        start = .7
    elif case == "far":
        options["x"] = 150
    elif case == "wrong_kit":
        options["histogram"] = [0.0, 1.0] + [0.0] * 30
    elif case == "scale":
        options["height"] = 10
    elif case == "short":
        options["count"] = 2
    elif case == "invalid_appearance":
        options["histogram"] = [np.nan] * 32
    elif case == "opposite_motion":
        options["velocity"] = -30
        options["x"] = 16
    add_track(endpoints, 2, start, **options)
    aliases, links = link_tracklets(endpoints)
    assert not links and aliases == {1: 1, 2: 2}


def test_ambiguous_same_kit_successors_are_not_guessed():
    endpoints = TrackEndpoints()
    add_track(endpoints, 1, 0)
    add_track(endpoints, 2, .2, x=11)
    add_track(endpoints, 3, .2, x=12)
    assert link_tracklets(endpoints)[1] == []


def test_complete_span_vetoes_a_track_that_reappears_after_an_apparent_gap():
    endpoints = TrackEndpoints()
    add_track(endpoints, 1, 0)
    add_track(endpoints, 2, .2)
    endpoints.add(1, .24, [10, 70], [5, 30, 15, 70], [1.0] + [0.0] * 31)
    assert link_tracklets(endpoints)[1] == []


@pytest.mark.parametrize("status,reliable,policy,reason", [
    ("moving", True, "conservative", "camera_unstable"),
    ("unknown", True, "conservative", "camera_unstable"),
    ("no_motion_detected", False, "conservative", "timestamps_unreliable"),
    ("no_motion_detected", True, "none", "disabled"),
])
def test_camera_and_timing_gates_disable_continuity(status, reliable, policy, reason):
    endpoints = TrackEndpoints()
    add_track(endpoints, 1, 0)
    add_track(endpoints, 2, .2)
    aliases, evidence = continuity_result(endpoints, status, reliable, policy)
    assert aliases == {1: 1, 2: 2} and evidence["status"] == reason and not evidence["links"]


def test_colour_features_have_no_face_or_identity_content():
    frame = np.full((100, 100, 3), (255, 0, 0), np.uint8)
    histogram = torso_histogram(frame, [10, 10, 40, 90])
    assert len(histogram) == 32 and np.linalg.norm(histogram) == pytest.approx(1)
    assert torso_histogram(frame, [0, 0, 1, 1]) is None
