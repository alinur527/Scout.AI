"""Score the released SoccerTrack v2 Drive challenge's zero-based 22-player GT.

Its -1 fields are placeholders, not confidence/visibility/class. Generic one-based
MOT documentation describes a different file format and must not be applied here.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.cv.validation import evaluate_labels, size_recall  # noqa: E402


def load_labels(gt_file, indices):
    indexed = {index: [] for index in indices}
    with Path(gt_file).open(encoding="utf-8") as stream:
        for row in csv.reader(stream):
            index, identity = int(row[0]), int(row[1])
            if index not in indexed:
                continue
            x, y, width, height = map(float, row[2:6])
            if not np.isfinite([x, y, width, height]).all() or min(width, height) <= 0:
                raise ValueError("Invalid publisher box")
            indexed[index].append(
                {"id": identity, "box": [x, y, x + width, y + height]}
            )
    return {"frames": [{"frame": i, "objects": indexed[i]} for i in sorted(indexed)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--gt", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.run / "summary.json").read_text())
    tracks = json.loads((args.run / "tracks.json").read_text())
    raw = json.loads((args.run / "detections.json").read_text())
    labels = load_labels(args.gt, [frame["frame"] for frame in tracks])
    detection = evaluate_labels(raw, labels)
    result = {
        "provenance": "SoccerTrack v2 released MOT challenge GT; 0-based, players/GK only; human box review protocol not specified",
        "gt_sha256": hashlib.sha256(args.gt.read_bytes()).hexdigest(),
        "positive_classes": ["player", "goalkeeper"],
        "tracking": evaluate_labels(tracks, labels),
        "detection": {
            key: detection[key]
            for key in ("tp", "fp", "fn", "precision", "recall", "f1")
        },
        "small_players": size_recall(
            raw, labels, [summary["metadata"]["width"], summary["metadata"]["height"]]
        ),
        "gt_observations": sum(len(frame["objects"]) for frame in labels["frames"]),
    }
    (args.run / "publisher_metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
