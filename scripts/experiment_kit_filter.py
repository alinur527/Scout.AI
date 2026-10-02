"""One DEV diagnostic: reject dark neutral torso crops; never a role assertion.

Ground truth is unchanged. Reject the heuristic if it loses players, because
kit colour alone cannot reliably identify referees or protect goalkeepers.
"""

import argparse
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.validation import evaluate_labels  # noqa: E402
from score_soccertrack import load_labels  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--gt", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads((args.run / "detections.json").read_text())
    filtered = []
    cap = cv2.VideoCapture(str(args.video))
    try:
        for record in raw:
            ok, frame = cap.read()
            if not ok:
                raise ValueError("Raw video stopped before saved detections")
            keep = []
            for p in record["detections"]:
                x1, y1, x2, y2 = p["box"]
                w, h = x2 - x1, y2 - y1
                left, right = max(0, round(x1 + .2 * w)), min(frame.shape[1], round(x1 + .8 * w))
                top, bottom = max(0, round(y1 + .2 * h)), min(frame.shape[0], round(y1 + .55 * h))
                crop = frame[top:bottom, left:right]
                dark = 0
                if crop.size >= 24:
                    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    dark = float(np.mean((hsv[:, :, 1] < 100) & (hsv[:, :, 2] < 100)))
                if dark < .6:
                    keep.append(p)
            filtered.append({**record, "detections": keep})
    finally:
        cap.release()
    labels = load_labels(args.gt, [f["frame"] for f in raw])
    result = {"experimental_only": True, "rule": "torso centre 20..80% width, 20..55% height; reject >=60% pixels HSV saturation<100 and value<100", "before": evaluate_labels(raw, labels), "after": evaluate_labels(filtered, labels), "limitation": "No referee labels. Dark neutral jersey is not a reliable role; goalkeeper or team kits may share it."}
    (args.run / "kit_filter_experiment.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: {k: result[name][k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")} for name in ("before", "after")}))


if __name__ == "__main__":
    main()
