"""Screen a independently annotated ROI on cached baseline boxes, no inference.

This is a post-filter diagnostic only: it cannot measure effects on BoT-SORT.
The production candidate must be rerun through actual VideoProcessor afterwards.
"""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.pitch_roi import PitchArea  # noqa: E402
from app.cv.validation import evaluate_labels  # noqa: E402
from score_soccertrack import load_labels  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--roi", type=Path, required=True)
    parser.add_argument("--gt", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads((args.run / "summary.json").read_text())
    raw = json.loads((args.run / "detections.json").read_text())
    area = PitchArea(json.loads(args.roi.read_text()), (summary["metadata"]["width"], summary["metadata"]["height"]))
    filtered = []
    for frame in raw:
        preds = [p for p in frame["detections"] if area.contains(((p["box"][0] + p["box"][2]) / 2, p["box"][3]))]
        filtered.append({**frame, "detections": preds})
    annotation = load_labels(args.gt, [f["frame"] for f in raw])
    result = {"diagnostic_only": True, "before": evaluate_labels(raw, annotation), "after": evaluate_labels(filtered, annotation)}
    (args.run / "roi_screen.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({name: {k: result[name][k] for k in ("tp", "fp", "fn", "precision", "recall", "f1")} for name in ("before", "after")}))


if __name__ == "__main__":
    main()
