"""Replay frozen pose outputs to compare ground-point policies without re-inference.

MAE uses independent visual feet labels; acceleration is only a stability proxy,
not accuracy. No policy is automatically installed into the application.
"""

import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.cv.validation import evaluate_labels  # noqa: E402


def compare(frames):
    previous, offsets, accelerations = {}, {}, {}
    for frame in frames:
        for detection in frame["detections"]:
            tid, positions = detection["id"], detection["positions"]
            box = np.array(detection["box"])
            bottom = np.array(positions["bbox"])
            xy, confidence = (
                np.array(detection["keypoints"]),
                np.array(detection["keypoint_confidence"]),
            )
            valid = [
                k for k in (15, 16) if confidence[k] >= 0.4 and np.isfinite(xy[k]).all()
            ]
            weighted = (
                np.average(xy[valid], axis=0, weights=confidence[valid])
                if valid
                else bottom
            )
            timestamp = frame["timestamp"]
            height = max(1, box[3] - box[1])
            if valid:
                offsets[tid] = (timestamp, (weighted - bottom) / height)
            offset_time, offset = offsets.get(tid, (-10, np.zeros(2)))
            fallback = (
                weighted
                if valid
                else bottom + offset * height
                if timestamp - offset_time <= 0.5
                else bottom
            )
            old = previous.get(tid)
            alpha = 1 - np.exp(-(timestamp - old[0]) / 0.08) if old else 1
            ema = (
                weighted
                if not old or timestamp - old[0] > 0.5
                else alpha * weighted + (1 - alpha) * old[1]
            )
            positions.update(
                weighted=weighted.tolist(),
                offset_fallback=fallback.tolist(),
                ema=ema.tolist(),
            )
            for key in ("left", "right"):
                if positions[key] is None:
                    positions[key] = bottom.tolist()
            previous[tid] = (timestamp, ema)
            for name, point in positions.items():
                accelerations.setdefault(name, {}).setdefault(tid, []).append(
                    (frame["frame"], point)
                )
    stability = {}
    for name, tracks in accelerations.items():
        values = []
        for points in tracks.values():
            for (a, pa), (b, pb), (c, pc) in zip(points, points[1:], points[2:]):
                if b == a + 1 and c == b + 1:
                    values.append(
                        float(np.linalg.norm(np.array(pc) - 2 * np.array(pb) + pa))
                    )
        stability[name] = {
            "n": len(values),
            "median_second_difference_px": float(np.median(values)) if values else None,
        }
    return stability


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tracks", type=Path)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    frames = json.loads(args.tracks.read_text(encoding="utf-8"))
    result = {"stability_proxy": compare(frames)}
    if args.annotations:
        annotation = json.loads(args.annotations.read_text(encoding="utf-8"))
        result["visual_ground_error_px"] = evaluate_labels(frames, annotation)[
            "ground_point_error_px"
        ]
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
