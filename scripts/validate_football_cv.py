"""Offline real-model experiment; videos, weights and outputs stay outside Git.

Baseline mirrors e65bbfd VideoProcessor.track parameters exactly. CLI overrides are
experiments, never application defaults. Run --help; annotations must be frozen first.
"""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.validation import evaluate_labels, technical_metrics  # noqa: E402


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--model", type=Path, default=ROOT / "backend/weights/yolo11n-pose.pt")
    parser.add_argument("--tracker", default=str(ROOT / "backend/app/cv/botsort.yaml"))
    parser.add_argument("--conf", type=float, default=.3)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-every", type=int, default=25)
    args = parser.parse_args()
    if not args.model.is_file():
        parser.error("Supply local model weights; this script never downloads them")
    if not 0 <= args.conf <= 1 or args.start < 0 or args.save_every < 1:
        parser.error("Invalid confidence, frame range or save interval")
    args.output.mkdir(parents=True, exist_ok=True)
    import torch
    import ultralytics
    import psutil
    from ultralytics import YOLO
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = YOLO(str(args.model)).to(device)
    if model.task != "pose":
        parser.error("A local COCO pose model is required")
    labels = json.loads(args.annotations.read_text(encoding="utf-8")) if args.annotations else None
    if labels and labels["video_sha256"] != sha256(args.video):
        parser.error("Annotations belong to a different video")
    labelled_indices = {f["frame"] for f in labels["frames"]} if labels else set()
    capture = cv2.VideoCapture(str(args.video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        parser.error("Video FPS must be finite and positive")
    metadata = {"fps": fps, "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
                "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))}
    metadata["duration_seconds"] = metadata["frame_count"] / fps
    frames, raw_frames, failures = [], [], []
    process = psutil.Process()
    observed_peak_rss = process.memory_info().rss
    raw_detections = []

    def capture_raw(predictor):
        # Registered before model.track installs tracker callbacks: raw NMS detections.
        raw_detections.clear()
        result = predictor.results[0]
        for box, score in zip(result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy()):
            raw_detections.append({"id": 0, "box": box.tolist(), "confidence": float(score)})

    model.add_callback("on_predict_postprocess_end", capture_raw)
    started = time.perf_counter()
    try:
        index = 0
        while args.end is None or index < args.end:
            ok, frame = capture.read()
            if not ok:
                break
            if index < args.start:
                index += 1
                continue
            result = model.track(frame, persist=True, classes=[0], conf=args.conf, iou=.5,
                                 imgsz=args.imgsz, half=device == "cuda", device=device,
                                 tracker=args.tracker, verbose=False)[0]
            detections = []
            if result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.cpu().numpy().astype(int)
                scores = result.boxes.conf.cpu().numpy()
                keypoints = result.keypoints.xy.cpu().numpy()
                kp_conf = result.keypoints.conf.cpu().numpy()
                for box, tid, score, xy, confidence in zip(boxes, ids, scores, keypoints, kp_conf):
                    ankles = [xy[k] for k in (15, 16) if confidence[k] >= .4 and np.isfinite(xy[k]).all()]
                    bbox = np.array([(box[0] + box[2]) / 2, box[3]])
                    mean = np.mean(ankles, axis=0) if ankles else bbox
                    positions = {"left": xy[15].tolist() if confidence[15] >= .4 else None,
                                 "right": xy[16].tolist() if confidence[16] >= .4 else None,
                                 "mean": mean.tolist(), "bbox": bbox.tolist()}
                    detections.append({"id": int(tid), "box": box.tolist(), "confidence": float(score),
                                       "positions": positions, "keypoints": xy.tolist(),
                                       "keypoint_confidence": confidence.tolist()})
            frames.append({"frame": index, "timestamp": index / fps, "detections": detections})
            raw_frames.append({"frame": index, "detections": list(raw_detections)})
            observed_peak_rss = max(observed_peak_rss, process.memory_info().rss)
            if index % args.save_every == 0 or index in labelled_indices:
                cv2.imwrite(str(args.output / f"frame-{index:05d}.jpg"), result.plot())
            index += 1
    except Exception as error:
        failures.append(f"{type(error).__name__}: {error}")
        raise
    finally:
        capture.release()
        elapsed = time.perf_counter() - started
        summary = {"video": str(args.video.resolve()), "video_sha256": sha256(args.video),
                   "metadata": metadata, "model_sha256": sha256(args.model),
                   "ultralytics": ultralytics.__version__, "torch": torch.__version__,
                   "device": device, "config": {"tracker": args.tracker, "conf": args.conf,
                   "iou": .5, "imgsz": args.imgsz, "start": args.start, "end": args.end},
                   "technical": technical_metrics(frames), "processing_seconds": elapsed,
                   "processing_fps": len(frames) / elapsed if elapsed else 0,
                   "processing_to_video_duration": elapsed / (len(frames) / fps) if frames else None,
                   "failures": failures, "ground_truth": evaluate_labels(frames, labels) if labels else None}
        if labels:
            raw_metrics = evaluate_labels(raw_frames, labels)
            summary["detection_ground_truth"] = {k: raw_metrics[k] for k in (
                "labelled_frames", "iou_threshold", "tp", "fp", "fn", "precision", "recall", "f1")}
            summary["annotation_sha256"] = sha256(args.annotations)
        summary["raw_detections"] = sum(len(f["detections"]) for f in raw_frames)
        summary["observed_peak_rss_bytes"] = observed_peak_rss
        summary["memory_method"] = "psutil RSS sampled after each frame; includes model, not a continuous peak"
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (args.output / "tracks.json").write_text(json.dumps(frames), encoding="utf-8")
        (args.output / "detections.json").write_text(json.dumps(raw_frames), encoding="utf-8")
        with (args.output / "tracks.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerow(["frame", "timestamp", "id", "x1", "y1", "x2", "y2", "confidence"])
            for frame in frames:
                for detection in frame["detections"]:
                    writer.writerow([frame["frame"], frame["timestamp"], detection["id"],
                                     *detection["box"], detection["confidence"]])
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
