"""One frozen lightweight stitching experiment on existing outputs and raw video.

GT is read only after linking, for evaluation. Coordinates/timestamps/detections
are unchanged. Only within-video anonymous output IDs may be remapped.
"""

import argparse
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import sys
import time

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.continuity import POLICY, TrackEndpoints, link_tracklets, torso_histogram  # noqa: E402
from app.cv.validation import evaluate_labels, match_boxes, technical_metrics  # noqa: E402
from score_soccertrack import load_labels  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--gt", type=Path, required=True)
    args = parser.parse_args()
    tracked = json.loads((args.run / "tracks.json").read_text())
    indexed = {f["frame"]: f for f in tracked}
    endpoints = TrackEndpoints()
    capture = cv2.VideoCapture(str(args.video))
    started = time.perf_counter()
    try:
        for index in range(max(indexed) + 1):
            ok, frame = capture.read()
            if not ok:
                raise ValueError("Video stopped before saved track outputs")
            record = indexed[index]
            for p in record["detections"]:
                endpoints.add(p["id"], record["timestamp"], p["positions"]["mean"], p["box"], torso_histogram(frame, p["box"]))
    finally:
        capture.release()
    aliases, links = link_tracklets(endpoints)
    elapsed = time.perf_counter() - started
    after = copy.deepcopy(tracked)
    for frame in after:
        for p in frame["detections"]:
            p["id"] = aliases[p["id"]]
    annotation = load_labels(args.gt, list(indexed))
    identities = defaultdict(Counter)
    for frame in annotation["frames"]:
        for ti, p in match_boxes(frame["objects"], indexed[frame["frame"]]["detections"]).items():
            identities[p["id"]][frame["objects"][ti]["id"]] += 1
    false_merges, unverified = [], []
    for link in links:
        old, new = identities[link["old_id"]], identities[link["new_id"]]
        if not old or not new:
            unverified.append(link)
        elif old.most_common(1)[0][0] != new.most_common(1)[0][0]:
            false_merges.append({**link, "old_gt_support": dict(old), "new_gt_support": dict(new)})
    result = {"policy": POLICY, "links": links, "false_merges": false_merges, "unverified_links": unverified, "before": evaluate_labels(tracked, annotation), "after": evaluate_labels(after, annotation), "technical_after": technical_metrics(after), "processing_seconds": elapsed, "limitation": "False-merge check compares dominant IoU-matched GT identities at link endpoints. Unmatched or mixed-identity source tracks cannot establish correctness; output IDs are anonymous and detection gaps persist."}
    (args.run / "continuity_experiment.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"links": links, "false_merges": false_merges, "unverified_links": unverified, "before_switches": result["before"]["id_switches"], "after_switches": result["after"]["id_switches"], "fragments": result["after"]["fragmentations"], "seconds": elapsed}))


if __name__ == "__main__":
    main()
