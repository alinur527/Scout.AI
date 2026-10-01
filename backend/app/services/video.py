import math
from pathlib import Path

import cv2


def inspect_video(path: Path, settings):
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError("Video cannot be decoded. Use a valid MP4, MOV or AVI file.")
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        if not math.isfinite(fps) or fps <= 0 or fps > 240:
            raise ValueError("Video has invalid or unsupported FPS (expected 0 < FPS <= 240).")
        if not math.isfinite(count) or count < 1:
            raise ValueError("Video contains no readable frames.")
        if count > settings.max_video_frames or count / fps > settings.max_video_seconds:
            raise ValueError("Video exceeds the configured duration/frame limit. Trim the clip first.")
        ok, frame = cap.read()
        if not ok or frame is None:
            raise ValueError("The first video frame cannot be decoded.")
        if frame.shape[0] * frame.shape[1] > 3840 * 2160:
            raise ValueError("Video resolution exceeds 4K. Resize the video first.")
        return {"fps": fps, "frame_count": int(count), "duration_seconds": round(count / fps, 3),
                "width": frame.shape[1], "height": frame.shape[0]}
    finally:
        cap.release()
