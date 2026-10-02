"""Evaluate released one-based TeamTrack MOT labels with existing metrics.

Keep publisher class-1 targets; no invented goalkeeper/referee/staff role labels.
Frame indexing differs from SoccerTrack v2's zero-based challenge format.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.validation import evaluate_labels, size_recall  # noqa: E402


def load_labels(gt, indices):
    indexed = {i: [] for i in indices}
    with Path(gt).open() as stream:
        for row in csv.reader(stream):
            frame = int(row[0]) - 1
            if frame not in indexed or int(float(row[6])) != 1 or int(float(row[7])) != 1:
                continue
            x, y, w, h = map(float, row[2:6])
            if not np.isfinite([x, y, w, h]).all() or min(w, h) <= 0:
                raise ValueError("Invalid publisher target box")
            indexed[frame].append({"id": int(row[1]), "box": [x, y, x + w, y + h]})
    return {"frames": [{"frame": i, "objects": indexed[i]} for i in sorted(indexed)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--gt", type=Path, required=True)
    args = parser.parse_args()
    tracks = json.loads((args.run / "tracks.json").read_text())
    raw = json.loads((args.run / "detections.json").read_text())
    summary = json.loads((args.run / "summary.json").read_text())
    labels = load_labels(args.gt, [f["frame"] for f in tracks])
    detection = evaluate_labels(raw, labels)
    result = {
        "provenance": "Official TeamTrack MOT-format class-1 target boxes and anonymous IDs; frame numbering starts at 1; detailed roles unavailable",
        "gt_sha256": hashlib.sha256(args.gt.read_bytes()).hexdigest(),
        "tracking": evaluate_labels(tracks, labels),
        "detection": {k: detection[k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")},
        "small_players": size_recall(raw, labels, [summary["metadata"]["width"], summary["metadata"]["height"]]),
        "gt_observations": sum(len(f["objects"]) for f in labels["frames"]),
    }
    (args.run / "publisher_metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"detection": result["detection"], "switches": result["tracking"]["id_switches"], "fragments": result["tracking"]["fragmentations"]}))


if __name__ == "__main__":
    main()
