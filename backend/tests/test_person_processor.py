import sys
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np
import pytest

from app.cv.processor import VideoProcessor
from app.cv.detector_policy import select_model_weights


@pytest.mark.parametrize(
    "task, label, accepted",
    [
        ("detect", "person", True),
        ("pose", "person", True),
        ("segment", "person", False),
        ("detect", "car", False),
    ],
)
def test_processor_accepts_only_person_models_without_ml_imports(
    monkeypatch, tmp_path, task, label, accepted
):
    model = Mock(task=task, names={0: label})
    model.to.return_value = model
    monkeypatch.setitem(
        sys.modules, "torch", SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
    )
    monkeypatch.setitem(sys.modules, "supervision", SimpleNamespace())
    monkeypatch.setitem(sys.modules, "ultralytics", SimpleNamespace(YOLO=lambda _: model))
    path = tmp_path / "local.pt"
    path.write_bytes(b"mock-local-weights")
    if not accepted:
        with pytest.raises(ValueError, match="person detection or pose"):
            VideoProcessor(path)
    else:
        processor = VideoProcessor(path)
        assert processor.device == "cpu"
        assert processor.ground_position_method == (
            "bbox_bottom_center" if task == "detect" else "ankle_mean_with_bbox_fallback"
        )


def test_person_without_pose_produces_finite_bbox_ground_points(monkeypatch):
    processor = VideoProcessor.__new__(VideoProcessor)
    processor.device = "cpu"
    processor.model = Mock()
    processor.model.track.return_value = [SimpleNamespace(keypoints=None)]
    detection = SimpleNamespace(tracker_id=np.array([7]), xyxy=np.array([[10, 20, 30, 60]], dtype=float))
    processor.sv = SimpleNamespace(Detections=SimpleNamespace(from_ultralytics=lambda _: detection))
    cap = Mock()
    cap.get.side_effect = lambda prop: 25 if prop == cv2.CAP_PROP_FPS else 0
    cap.read.side_effect = [(True, np.zeros((100, 100, 3), np.uint8)), (False, None)]
    monkeypatch.setattr(cv2, "VideoCapture", lambda _: cap)
    observations = list(processor.process_video("fixture"))
    assert observations[0][4][0].tolist() == [20, 60]
    assert processor.timestamps_reliable and cap.release.called


@pytest.mark.parametrize(
    "width,height,profile",
    [
        (4096, 1080, "panoramic_person"),
        (1280, 720, "configured_base"),
        (3840, 2160, "configured_base"),
        (1900, 600, "configured_base"),
        (2000, 0, "configured_base"),
    ],
)
def test_auto_scope_does_not_replace_broadcast_detector(width, height, profile):
    settings = SimpleNamespace(
        cv_detector_policy="auto", model_weights="pose.pt", person_model_weights="person.pt"
    )
    path, selected = select_model_weights(settings, {"width": width, "height": height})
    assert selected == profile
    assert path == ("person.pt" if profile == "panoramic_person" else "pose.pt")


def test_explicit_policies_allow_rollback_and_opt_in():
    settings = SimpleNamespace(
        cv_detector_policy="pose", model_weights="pose.pt", person_model_weights="person.pt"
    )
    assert select_model_weights(settings, {"width": 4096, "height": 1080}) == ("pose.pt", "configured_base")
    settings.cv_detector_policy = "person"
    assert select_model_weights(settings, {"width": 1280, "height": 720}) == ("person.pt", "explicit_person")
