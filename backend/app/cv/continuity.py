"""Conservative anonymous tracklet links within one video; no interpolation.

Only disjoint observed spans, short gaps, agreement of ground-point motion,
scale and torso colour, and unambiguous one-to-one links qualify. Same kit is
not identity proof. Link evidence is retained; physical gates remain downstream.
"""

from collections import defaultdict

import cv2
import numpy as np

POLICY = {
    "max_gap_seconds": .5,
    "max_displacement_heights": 1.25,
    "max_prediction_error_heights": .5,
    "min_direction_cosine": .5,
    "min_appearance_cosine": .90,
    "direction_deadband_heights_per_second": .5,
    "scale_ratio_min": .8,
    "scale_ratio_max": 1.25,
    "min_observations": 3,
    "endpoint_samples": 5,
}


def torso_histogram(frame, box):
    x1, y1, x2, y2 = np.asarray(box, dtype=float)
    w, h = x2 - x1, y2 - y1
    left, right = max(0, round(x1 + .2 * w)), min(frame.shape[1], round(x1 + .8 * w))
    top, bottom = max(0, round(y1 + .2 * h)), min(frame.shape[0], round(y1 + .55 * h))
    crop = frame[top:bottom, left:right]
    if crop.size < 24:
        return None
    hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [8, 4], [0, 180, 0, 256]).ravel()
    norm = np.linalg.norm(hist)
    return (hist / norm).tolist() if norm > 0 else None


class TrackEndpoints:
    def __init__(self):
        self.tracks = {}

    def add(self, identity, timestamp, point, box, histogram):
        identity = int(identity)
        record = {"time": float(timestamp), "point": np.asarray(point, dtype=float), "size": np.asarray(box[2:], dtype=float) - box[:2], "histogram": histogram}
        row = self.tracks.setdefault(identity, {"first": [], "last": [], "count": 0})
        row["count"] += 1
        if len(row["first"]) < POLICY["endpoint_samples"]:
            row["first"].append(record)
        row["last"].append(record)
        row["last"] = row["last"][-POLICY["endpoint_samples"]:]


def endpoint(records):
    histograms = [r["histogram"] for r in records if r["histogram"] is not None and np.asarray(r["histogram"]).shape == (32,) and np.isfinite(r["histogram"]).all()]
    if len(histograms) < POLICY["min_observations"]:
        histograms = []
    hist = np.mean(histograms, axis=0) if histograms else None
    if hist is not None:
        hist /= max(np.linalg.norm(hist), 1e-8)
    dt = records[-1]["time"] - records[0]["time"]
    velocity = (records[-1]["point"] - records[0]["point"]) / dt if dt > 0 else np.zeros(2)
    return hist, velocity


def link_tracklets(endpoints):
    """Offline full-span check prevents an earlier ID reappearing after a link."""
    rows = endpoints.tracks
    candidates = []
    for old, a in rows.items():
        if a["count"] < POLICY["min_observations"]:
            continue
        ah, av = endpoint(a["last"])
        last = a["last"][-1]
        for new, b in rows.items():
            if old == new or b["count"] < POLICY["min_observations"]:
                continue
            first = b["first"][0]
            gap = first["time"] - last["time"]
            if not 0 < gap <= POLICY["max_gap_seconds"]:
                continue
            bh, bv = endpoint(b["first"])
            if ah is None or bh is None or not np.isfinite([*av, *bv, *last["point"], *first["point"]]).all():
                continue
            ratio = first["size"] / np.maximum(last["size"], 1e-8)
            if (ratio < POLICY["scale_ratio_min"]).any() or (ratio > POLICY["scale_ratio_max"]).any():
                continue
            height = min(last["size"][1], first["size"][1])
            if height <= 0:
                continue
            displacement = np.linalg.norm(first["point"] - last["point"]) / height
            error = np.linalg.norm(first["point"] - last["point"] - av * gap) / height
            similarity = float(np.dot(ah, bh))
            if displacement > POLICY["max_displacement_heights"] or error > POLICY["max_prediction_error_heights"] or similarity < POLICY["min_appearance_cosine"]:
                continue
            if min(np.linalg.norm(av), np.linalg.norm(bv)) > POLICY["direction_deadband_heights_per_second"] * height:
                cosine = np.dot(av, bv) / (np.linalg.norm(av) * np.linalg.norm(bv))
                if cosine < POLICY["min_direction_cosine"]:
                    continue
            candidates.append({"old_id": old, "new_id": new, "gap_seconds": gap, "appearance_cosine": similarity, "displacement_heights": float(displacement), "prediction_error_heights": float(error)})
    # Accept only uniquely eligible endpoints. No nearest-neighbour guess among
    # several same-kit players, even if one distance is slightly smaller.
    outgoing, incoming = defaultdict(list), defaultdict(list)
    for candidate in candidates:
        outgoing[candidate["old_id"]].append(candidate)
        incoming[candidate["new_id"]].append(candidate)
    links = [c for c in candidates if len(outgoing[c["old_id"]]) == 1 and len(incoming[c["new_id"]]) == 1]
    links.sort(key=lambda c: rows[c["new_id"]]["first"][0]["time"])
    aliases = {identity: identity for identity in rows}
    evidence = []
    for link in links:
        old, new = link["old_id"], link["new_id"]
        root = aliases[old]
        # All members of a chain must have disjoint complete spans.
        first = rows[new]["first"][0]["time"]
        if any(rows[i]["last"][-1]["time"] >= first for i, canonical in aliases.items() if canonical == root):
            continue
        aliases[new] = root
        evidence.append(link)
    return aliases, evidence


def continuity_result(endpoints, camera_status, timestamps_reliable, policy):
    identities = {identity: identity for identity in endpoints.tracks}
    reason = "disabled" if policy == "none" else "camera_unstable" if camera_status != "no_motion_detected" else "timestamps_unreliable" if not timestamps_reliable else None
    if reason:
        return identities, {"policy": policy, "status": reason, "links": []}
    aliases, links = link_tracklets(endpoints)
    return aliases, {"policy": policy, "status": "evaluated", "links": links, "thresholds": POLICY.copy()}


def merge_track_data(points, gallery, counts, aliases):
    """Change only anonymous grouping; preserve every original time/coordinate."""
    merged_points, merged_counts, merged_gallery = {}, {}, {}
    for identity, samples in points.items():
        root = str(aliases.get(int(identity), int(identity)))
        merged_points.setdefault(root, []).extend(samples)
        merged_counts[root] = merged_counts.get(root, 0) + counts.get(identity, 0)
        if identity in gallery:
            previous = merged_gallery.get(root)
            if previous is None or counts.get(identity, 0) > previous[0]:
                merged_gallery[root] = (counts.get(identity, 0), {**gallery[identity], "id": int(root), "label": f"Player {root}"})
    for samples in merged_points.values():
        samples.sort(key=lambda sample: sample[0])
    return merged_points, {key: row[1] for key, row in merged_gallery.items()}, merged_counts
