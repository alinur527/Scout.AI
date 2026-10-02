"""Run the production camera veto on raw video, independent of tracking."""

import argparse
import json
from pathlib import Path
import sys

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.cv.camera import CameraMotionMonitor  # noqa: E402

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("video", type=Path)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
cap = cv2.VideoCapture(str(args.video))
monitor = CameraMotionMonitor(cap.get(cv2.CAP_PROP_FPS))
index = 0
try:
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        monitor.update(index, frame)
        index += 1
finally:
    cap.release()
args.output.write_text(json.dumps(monitor.summary(), indent=2), encoding="utf-8")
print(json.dumps(monitor.summary(), indent=2))
