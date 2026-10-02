"""COCO person detection/optional pose, BoT-SORT and image-space ground points."""

from pathlib import Path
import math

import cv2
import numpy as np

from app.cv.ground import ground_point


def inference_size_for_frame(frame):
    # Do not discard HD detail or upscale already low-resolution footage beyond 640.
    # Selected after controlled 640/1280 experiments; cap CPU/GPU work at 1280.
    return min(1280, max(640, math.ceil(max(frame.shape[:2]) / 32) * 32))


class VideoProcessor:
    def __init__(self, model_weights):
        if not Path(model_weights).is_file():
            raise ValueError(f"Model weights are missing: {Path(model_weights).name}. Download the configured local model with scripts/download_model.py --model, or correct its weights path.")
        try:
            import torch
            import supervision as sv
            from ultralytics import YOLO
        except ImportError as error:
            raise ValueError(
                "Real CV dependencies are missing. Install backend/requirements-cv.txt."
            ) from error
        self.sv = sv
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(str(model_weights)).to(self.device)
        if self.model.task not in ("detect", "pose") or self.model.names.get(0) != "person":
            raise ValueError("MODEL_WEIGHTS must be a COCO person detection or pose model")
        self.ground_position_method = "bbox_bottom_center" if self.model.task == "detect" else "ankle_mean_with_bbox_fallback"

    def process_video(self, source_path, max_frames=54000):
        cap = cv2.VideoCapture(str(source_path))
        try:
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not math.isfinite(fps) or fps <= 0:
                raise ValueError("Video FPS must be finite and positive")
            self.timestamps_reliable = True
            previous_timestamp = None
            index = 0
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                if index >= max_frames:
                    raise ValueError("Decoded video exceeds the frame limit")
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                if (
                    not math.isfinite(timestamp)
                    or timestamp < 0
                    or (previous_timestamp is not None and timestamp <= previous_timestamp)
                ):
                    self.timestamps_reliable = False
                    timestamp = max(index / fps, (previous_timestamp or 0) + 1 / fps)
                previous_timestamp = timestamp
                results = self.model.track(
                    frame,
                    persist=True,
                    classes=[0],
                    conf=0.3,
                    iou=0.5,
                    imgsz=inference_size_for_frame(frame),
                    half=self.device == "cuda",
                    device=self.device,
                    tracker=str(Path(__file__).with_name("botsort.yaml")),
                    verbose=False,
                )
                result = results[0]
                detections = self.sv.Detections.from_ultralytics(result)
                if detections.tracker_id is None:
                    yield index, timestamp, frame, self.sv.Detections.empty(), []
                    index += 1
                    continue
                ankles = []
                keypoints = result.keypoints
                for i, box in enumerate(detections.xyxy):
                    xy = conf = None
                    if keypoints is not None and keypoints.xy.shape[1] >= 17:
                        xy = keypoints.xy[i].cpu().numpy()
                        conf = keypoints.conf[i].cpu().numpy() if keypoints.conf is not None else np.zeros(17)
                    ankles.append(ground_point(box, xy, conf))
                yield index, timestamp, frame, detections, ankles
                index += 1
            if index == 0:
                raise ValueError("No frames could be decoded")
        finally:
            cap.release()
