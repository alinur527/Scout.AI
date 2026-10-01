"""Create a tiny valid, synthetic video to exercise DEMO mode. Not an accuracy dataset."""

from pathlib import Path
import cv2
import numpy as np


def make_video(path, frames=60):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 20, (320, 200))
    if not writer.isOpened():
        raise RuntimeError("MJPG video writer is unavailable")
    try:
        for i in range(frames):
            frame = np.full((200, 320, 3), (45, 85, 35), dtype=np.uint8)
            cv2.rectangle(frame, (10, 10), (310, 190), (220, 220, 220), 1)
            cv2.line(frame, (160, 10), (160, 190), (220, 220, 220), 1)
            cv2.circle(frame, (65 + i * 2, 100), 8, (220, 130, 130), -1)
            cv2.putText(
                frame,
                "DEMO FIXTURE",
                (85, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1,
            )
            writer.write(frame)
    finally:
        writer.release()
    return path


if __name__ == "__main__":
    print(make_video(Path(__file__).resolve().parents[1] / "test-artifacts/demo.avi"))
