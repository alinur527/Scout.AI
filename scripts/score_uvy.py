"""Score saved outputs against opt-in UVY MOT labels without running a model.

Positive classes: player and goalkeeper. Referees/camera operators are not
football players; detections of them are task false positives. This evaluates
COCO person outputs for a football-player task, not general person accuracy.
Publisher labels were YOLO-World assisted and manually corrected in CVAT.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.cv.validation import evaluate_labels  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--labels", type=Path, required=True)
    parser.add_argument("--source-start", type=int, default=0)
    args = parser.parse_args()
    labels = args.labels.read_text(encoding="utf-8").splitlines()
    classes = {
        i + 1
        for i, label in enumerate(labels)
        if label.strip() in ("player", "goalkeeper")
    }
    tracked_frames = json.loads((args.run / "tracks.json").read_text())
    indexed = {frame["frame"]: [] for frame in tracked_frames}
    with args.gt.open(encoding="utf-8") as stream:
        for row in csv.reader(stream):
            frame, identity = int(row[0]) - 1 - args.source_start, int(row[1])
            if (
                frame not in indexed
                or int(float(row[6])) != 1
                or int(float(row[7])) not in classes
            ):
                continue
            x, y, width, height = map(float, row[2:6])
            indexed[frame].append(
                {"id": identity, "box": [x, y, x + width, y + height]}
            )
    annotation = {"frames": [{"frame": i, "objects": v} for i, v in indexed.items()]}
    result = {
        "provenance": "UVY publisher YOLO-World assisted / manual CVAT correction",
        "source_start_frame": args.source_start,
        "positive_classes": ["player", "goalkeeper"],
        "gt_sha256": hashlib.sha256(args.gt.read_bytes()).hexdigest(),
        "tracking": evaluate_labels(tracked_frames, annotation),
    }
    raw = evaluate_labels(
        json.loads((args.run / "detections.json").read_text()), annotation
    )
    result["detection"] = {
        k: raw[k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")
    }
    (args.run / "publisher_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
