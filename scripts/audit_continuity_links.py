"""Audit frozen links against GT without recomputing or modifying the candidate."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.validation import match_boxes  # noqa: E402
from score_soccertrack import load_labels as soccertrack_labels  # noqa: E402
from score_teamtrack import load_labels as teamtrack_labels  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--format", choices=("soccertrack", "teamtrack"), default="soccertrack")
    args = parser.parse_args()
    tracked = json.loads((args.run / "tracker_tracks.json").read_text())
    summary = json.loads((args.run / "summary.json").read_text())
    indexed = {f["frame"]: f for f in tracked}
    annotation = (soccertrack_labels if args.format == "soccertrack" else teamtrack_labels)(args.gt, list(indexed))
    support = defaultdict(Counter)
    for frame in annotation["frames"]:
        for ti, p in match_boxes(frame["objects"], indexed[frame["frame"]]["detections"]).items():
            support[p["id"]][frame["objects"][ti]["id"]] += 1
    links = []
    for link in summary["continuity"]["links"]:
        old, new = support[link["old_id"]], support[link["new_id"]]
        old_ids, new_ids = set(old), set(new)
        status = "verified_same_gt" if len(old_ids) == len(new_ids) == 1 and old_ids == new_ids else "false_merge" if old_ids and new_ids and old_ids.isdisjoint(new_ids) else "indeterminate_mixed_or_unmatched"
        links.append({**link, "status": status, "old_gt_support": dict(old), "new_gt_support": dict(new)})
    result = {"links": links, "counts": dict(Counter(link["status"] for link in links)), "definition": "Every IoU>=.5 matched GT identity in both entire source tracklets must be the same single identity to verify a link. Disjoint nonempty support is a false merge; mixed/unmatched support is indeterminate, never counted as verified."}
    (args.run / "link_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
