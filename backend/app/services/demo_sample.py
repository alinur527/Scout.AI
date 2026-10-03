"""Synthetic local fixture. No people, source footage, model or account data."""

from functools import lru_cache
from pathlib import Path
import tempfile

import cv2
import numpy as np


@lru_cache(maxsize=1)
def sample_bytes():
    with tempfile.TemporaryDirectory(prefix="scoutai-sample-") as temporary:
        path = Path(temporary) / "synthetic-demo.avi"
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20, (320, 200))
        if not writer.isOpened():
            raise RuntimeError("Synthetic sample encoder is unavailable")
        try:
            for index in range(60):
                frame = np.full((200, 320, 3), (45, 85, 35), dtype=np.uint8)
                cv2.rectangle(frame, (10, 10), (310, 190), (220, 220, 220), 1)
                cv2.line(frame, (160, 10), (160, 190), (220, 220, 220), 1)
                cv2.circle(frame, (65 + index * 2, 100), 8, (220, 130, 130), -1)
                cv2.putText(frame, "SYNTHETIC DEMO", (85, 25), cv2.FONT_HERSHEY_SIMPLEX, .4, (255, 255, 255), 1)
                writer.write(frame)
        finally:
            writer.release()
        return path.read_bytes()
