"""Classify saved baseline errors with existing matching and publisher labels.

Unlabelled roles remain unknown. Low-IoU agreement is a localization hypothesis,
not proof that an unmatched detection is a real player. No CV inference or tuning.
"""

import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.validation import evaluate_labels, iou, match_boxes  # noqa: E402
from score_soccertrack import load_labels  # noqa: E402


def uvy_labels(gt, labels, indices, source_start):
    names = Path(labels).read_text().splitlines()
    positive, negative = {i: [] for i in indices}, {i: [] for i in indices}
    with Path(gt).open() as stream:
        for row in csv.reader(stream):
            frame = int(row[0]) - 1 - source_start
            if frame not in positive or int(float(row[6])) != 1:
                continue
            name = names[int(float(row[7])) - 1].strip()
            x, y, w, h = map(float, row[2:6])
            item = {"id": int(row[1]), "box": [x, y, x + w, y + h], "role": name}
            if name in ("player", "goalkeeper"):
                positive[frame].append(item)
            elif name in ("referee", "pcamera"):
                negative[frame].append(item)
    return {"frames": [{"frame": i, "objects": positive[i]} for i in indices]}, negative


def analyze(raw, tracked, annotation, negative):
    fp_classes, examples = Counter(), defaultdict(list)
    raw_index = {f["frame"]: f["detections"] for f in raw}
    track_index = {f["frame"]: f["detections"] for f in tracked}
    truth_index = {f["frame"]: f["objects"] for f in annotation["frames"]}
    for frame, truth in truth_index.items():
        preds = raw_index[frame]
        matches = match_boxes(truth, preds)
        matched_objects = {id(p) for p in matches.values()}
        for prediction in preds:
            if id(prediction) in matched_objects:
                continue
            role = max(negative.get(frame, []), key=lambda p: iou(p["box"], prediction["box"]), default=None)
            overlap = max((iou(t["box"], prediction["box"]) for t in truth), default=0)
            if role and iou(role["box"], prediction["box"]) >= .5:
                kind = "referee" if role["role"] == "referee" else "publisher_camera_person"
            elif overlap >= .5:
                kind = "duplicate_player_box"
            elif overlap >= .1:
                kind = "possible_localization_iou_mismatch"
            else:
                kind = "unknown_requires_visual_review"
            fp_classes[kind] += 1
            if len(examples[kind]) < 10:
                examples[kind].append({"frame": frame, "box": prediction["box"], "max_player_iou": overlap})
    metrics = evaluate_labels(tracked, annotation)
    spans = defaultdict(list)
    for frame in tracked:
        for detection in frame["detections"]:
            spans[detection["id"]].append(frame["frame"])
    switch_hypotheses = Counter()
    switch_evidence = []
    for event in metrics["events"]:
        if event["kind"] != "id_switch":
            continue
        old, new = event["previous_id"], event["new_id"]
        overlap = bool(set(spans[old]) & set(spans[new]))
        kind = "coexisting_ids_cannot_stitch" if overlap else "nonoverlapping_tracklets"
        switch_hypotheses[kind] += 1
        switch_evidence.append({**event, "hypothesis": kind, "old_span": [min(spans[old]), max(spans[old])], "new_span": [min(spans[new]), max(spans[new])]})
    lost = Counter()
    previous_match = {}
    loss_examples = []
    for frame, truth in truth_index.items():
        tm, rm = match_boxes(truth, track_index[frame]), match_boxes(truth, raw_index[frame])
        for ti, item in enumerate(truth):
            identity = item["id"]
            if ti not in tm and previous_match.get(identity, False):
                kind = "raw_detector_miss_or_localization" if ti not in rm else "raw_match_lost_by_tracker"
                lost[kind] += 1
                if len(loss_examples) < 15:
                    loss_examples.append({"frame": frame, "gt_id": identity, "hypothesis": kind})
            previous_match[identity] = ti in tm
    return {
        "fp_total": sum(fp_classes.values()), "fp_classes": dict(fp_classes),
        "examples": dict(examples), "switch_hypotheses": dict(switch_hypotheses),
        "switch_evidence": switch_evidence, "matched_to_unmatched_transitions": dict(lost),
        "loss_examples": loss_examples,
        "limitations": "Hypotheses based on box agreement and ID overlap. Unknown boxes cannot establish spectator/staff/background roles. Occlusion, uniforms and camera causes require visual evidence; no inferred publisher roles.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--gt", type=Path, required=True)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--source-start", type=int, default=0)
    args = parser.parse_args()
    raw = json.loads((args.run / "detections.json").read_text())
    tracked = json.loads((args.run / "tracks.json").read_text())
    indices = [f["frame"] for f in raw]
    annotation, negative = uvy_labels(args.gt, args.labels, indices, args.source_start) if args.labels else (load_labels(args.gt, indices), {})
    result = analyze(raw, tracked, annotation, negative)
    (args.run / "error_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("examples", "switch_evidence", "loss_examples")}))


if __name__ == "__main__":
    main()
