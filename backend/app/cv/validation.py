"""Small, explicit validation metrics. No accuracy inference without labelled frames."""

from collections import Counter, defaultdict

import numpy as np


def iou(a, b):
    a, b = np.asarray(a), np.asarray(b)
    overlap = np.maximum(0, np.minimum(a[2:], b[2:]) - np.maximum(a[:2], b[:2]))
    intersection = float(np.prod(overlap))
    union = float(np.prod(a[2:] - a[:2]) + np.prod(b[2:] - b[:2]) - intersection)
    return intersection / union if union > 0 else 0.0


def evaluate_labels(frames, annotation, threshold=0.5):
    """Descending-IoU one-to-one matching in an exhaustively annotated ROI.

    Predictions whose box centres are outside the ROI are ignored, not false positives.
    Switch: a visible GT identity's matched prediction ID changes (including after a gap).
    Fragment: matched -> unmatched visible GT -> matched. Not the number of output IDs.
    These definitions apply only to the sampled labelled frames, not intervening frames.
    """
    indexed = {frame["frame"]: frame["detections"] for frame in frames}
    tp = fp = fn = switches = fragments = 0
    previous, interrupted = {}, set()
    per_identity = Counter()
    matched_identity = Counter()
    ground_errors = defaultdict(list)
    for label in annotation["frames"]:
        roi = label.get("roi", annotation.get("roi"))
        truth = label["objects"]
        predictions = indexed.get(label["frame"], [])
        if roi:
            predictions = [p for p in predictions if (
                roi[0] <= (p["box"][0] + p["box"][2]) / 2 <= roi[2]
                and roi[1] <= (p["box"][1] + p["box"][3]) / 2 <= roi[3]
            )]
        candidates = sorted(
            [(iou(t["box"], p["box"]), ti, pi)
             for ti, t in enumerate(truth) for pi, p in enumerate(predictions)], reverse=True
        )
        used_t, used_p, matches = set(), set(), {}
        for overlap, ti, pi in candidates:
            if overlap >= threshold and ti not in used_t and pi not in used_p:
                used_t.add(ti)
                used_p.add(pi)
                matches[ti] = predictions[pi]
        tp += len(matches)
        fp += len(predictions) - len(matches)
        fn += len(truth) - len(matches)
        for ti, item in enumerate(truth):
            identity = str(item["id"])
            per_identity[identity] += 1
            if ti not in matches:
                if identity in previous:
                    interrupted.add(identity)
                continue
            prediction = matches[ti]
            matched_identity[identity] += 1
            pid = prediction["id"]
            if identity in previous and pid != previous[identity]:
                switches += 1
            if identity in interrupted:
                fragments += 1
                interrupted.remove(identity)
            previous[identity] = pid
            if "ground" in item:
                for name, point in prediction.get("positions", {}).items():
                    if point is not None:
                        ground_errors[name].append(float(np.linalg.norm(np.asarray(point) - item["ground"])))
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {
        "labelled_frames": len(annotation["frames"]), "iou_threshold": threshold,
        "tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0,
        "id_switches": switches, "fragmentations": fragments,
        "identity_coverage": {k: matched_identity[k] / n for k, n in per_identity.items()},
        "ground_point_error_px": {k: {"n": len(v), "mean": float(np.mean(v)),
                                      "median": float(np.median(v))} for k, v in ground_errors.items()},
    }


def technical_metrics(frames):
    tracks = defaultdict(list)
    confidence = []
    for frame in frames:
        for detection in frame["detections"]:
            tracks[detection["id"]].append(frame["frame"])
            confidence.append(detection["confidence"])
    lengths = [len(v) for v in tracks.values()]
    gaps = [b - a - 1 for indices in tracks.values() for a, b in zip(indices, indices[1:]) if b > a + 1]
    counts = [len(f["detections"]) for f in frames]
    return {
        "frames": len(frames), "detections": sum(counts), "track_ids": len(tracks),
        "frames_with_detections": sum(n > 0 for n in counts),
        "frames_without_detections": sum(n == 0 for n in counts),
        "frame_detection_coverage": sum(n > 0 for n in counts) / len(frames) if frames else 0,
        "mean_detections_per_frame": float(np.mean(counts)) if counts else 0,
        "mean_track_observations": float(np.mean(lengths)) if lengths else 0,
        "median_track_observations": float(np.median(lengths)) if lengths else 0,
        "longest_track_observations": max(lengths, default=0),
        "short_tracks_lt10_observations": sum(n < 10 for n in lengths),
        "reacquired_same_id_gaps": len(gaps), "lost_frame_intervals": sum(gaps),
        "fragmentation_proxy_ids_per_100_frames": len(tracks) / len(frames) * 100 if frames else 0,
        "confidence_quantiles": np.quantile(confidence, [0, .25, .5, .75, 1]).tolist() if confidence else [],
    }
