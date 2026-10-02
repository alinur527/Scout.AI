"""Offline real-model experiment; videos, weights and outputs stay outside Git.

Baseline mirrors e65bbfd VideoProcessor.track parameters exactly. CLI overrides are
experiments, never application defaults. Run --help; annotations must be frozen first.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import time

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.cv.validation import evaluate_labels, technical_metrics  # noqa: E402
from app.cv.pitch import pitch_box_selection  # noqa: E402
from app.cv.tiles import nms_indices, tile_windows  # noqa: E402
from app.cv.continuity import TrackEndpoints, continuity_result, torso_histogram  # noqa: E402


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tiled_result(model, tracker, frame, args, device, torch):
    """Four overlapping crops, global coordinates/NMS, then one tracker update."""
    from ultralytics.engine.results import Results

    boxes, keypoints = [], []
    for x1, y1, x2, y2 in tile_windows(frame.shape[1], frame.shape[0]):
        prediction = model.predict(
            frame[y1:y2, x1:x2],
            classes=[0],
            conf=args.conf,
            iou=0.5,
            imgsz=args.imgsz,
            device=device,
            half=device == "cuda",
            verbose=False,
        )[0]
        data = prediction.boxes.data.cpu().numpy().copy()
        data[:, [0, 2]] += x1
        data[:, [1, 3]] += y1
        boxes.extend(data)
        if prediction.keypoints is not None:
            kp = prediction.keypoints.data.cpu().numpy().copy()
            kp[:, :, 0] += x1
            kp[:, :, 1] += y1
            keypoints.extend(kp)
    data = np.asarray(boxes, dtype=np.float32).reshape(-1, 6)
    keep = nms_indices(data[:, :4], data[:, 4])
    data = data[keep]
    kp = (
        np.asarray(keypoints, dtype=np.float32).reshape(-1, 17, 3)[keep]
        if model.task == "pose"
        else None
    )
    raw_count = len(data)
    info = {"status": "disabled"}
    if args.scene_filter == "pitch":
        keep, info = pitch_box_selection(frame, data[:, :4])
        data = data[keep]
        if kp is not None:
            kp = kp[keep]
    result = Results(
        frame,
        "tiles",
        model.names,
        boxes=torch.as_tensor(data),
        keypoints=torch.as_tensor(kp) if kp is not None else None,
    )
    raw = [
        {"id": 0, "box": row[:4].tolist(), "confidence": float(row[4])} for row in data
    ]
    tracks = tracker.update(result.boxes.cpu().numpy(), frame)
    if len(tracks):
        result = result[tracks[:, -1].astype(int)]
        result.update(boxes=torch.as_tensor(tracks[:, :-1]))
    return result, raw, raw_count, info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument(
        "--model",
        type=Path,
        help="Explicit local weights; production default follows the scene policy",
    )
    parser.add_argument("--tracker", default=str(ROOT / "backend/app/cv/botsort.yaml"))
    parser.add_argument("--conf", type=float, default=0.3)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--scene-filter", choices=("none", "pitch"), default="none")
    parser.add_argument(
        "--tiles",
        action="store_true",
        help="Experimental 2x2 crops with 15%% overlap and global NMS",
    )
    parser.add_argument("--experiment", default="unspecified")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int)
    parser.add_argument("--annotations", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-every", type=int, default=25)
    parser.add_argument("--continuity", choices=("none", "conservative"), help="Production default or explicit anonymous continuity diagnostic")
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run actual VideoProcessor and camera veto; full clip only",
    )
    args = parser.parse_args()
    if args.continuity is None:
        from app.core.config import Settings

        args.continuity = Settings.model_fields["cv_track_continuity"].default if args.production else "none"
    production_profile = "explicit_model" if args.model else None
    if args.model is None and args.production:
        from types import SimpleNamespace
        from app.core.config import Settings
        from app.cv.detector_policy import select_model_weights

        probe = cv2.VideoCapture(str(args.video))
        try:
            video_size = {
                "width": probe.get(cv2.CAP_PROP_FRAME_WIDTH),
                "height": probe.get(cv2.CAP_PROP_FRAME_HEIGHT),
            }
        finally:
            probe.release()
        defaults = SimpleNamespace(
            cv_detector_policy=Settings.model_fields["cv_detector_policy"].default,
            model_weights=ROOT
            / "backend"
            / Settings.model_fields["model_weights"].default,
            person_model_weights=ROOT
            / "backend"
            / Settings.model_fields["person_model_weights"].default,
        )
        args.model, production_profile = select_model_weights(defaults, video_size)
    args.model = args.model or ROOT / "backend/weights/yolo11n-pose.pt"
    if not args.model.is_file():
        parser.error("Supply local model weights; this script never downloads them")
    if not 0 <= args.conf <= 1 or args.start < 0 or args.save_every < 1:
        parser.error("Invalid confidence, frame range or save interval")
    if (args.imgsz != 0 and args.imgsz < 32) or (
        args.end is not None and args.end <= args.start
    ):
        parser.error(
            "Image size must be 0 (native production policy) or >=32; invalid frame range"
        )
    if args.tiles and args.imgsz == 0:
        parser.error("Tiling needs an explicit per-tile image size")
    args.output.mkdir(parents=True, exist_ok=True)
    run_started_utc = datetime.now(timezone.utc).isoformat()
    run_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    run_dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    harness_hash = sha256(Path(__file__))
    processor_hash = sha256(ROOT / "backend/app/cv/processor.py")
    import torch
    import ultralytics
    import psutil
    from ultralytics import YOLO

    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = None
    if args.production:
        if (
            args.start
            or args.end is not None
            or args.conf != 0.3
            or args.imgsz != 640
            or args.tracker != str(ROOT / "backend/app/cv/botsort.yaml")
            or args.tiles
            or args.scene_filter != "none"
        ):
            parser.error(
                "--production uses application defaults and the entire clip; remove experiment overrides"
            )
        from app.cv.processor import VideoProcessor
        from app.cv.camera import CameraMotionMonitor

        processor = VideoProcessor(args.model)
        model = processor.model
    else:
        model = YOLO(str(args.model)).to(device)
    if model.task not in ("pose", "detect") or model.names.get(0) != "person":
        parser.error("A local COCO person detection or pose model is required")
    tile_tracker = None
    if args.tiles:
        from ultralytics.trackers.bot_sort import BOTSORT
        from ultralytics.utils import YAML, IterableSimpleNamespace

        tracker_config = YAML.load(args.tracker)
        if tracker_config["tracker_type"] != "botsort" or tracker_config.get(
            "with_reid"
        ):
            parser.error("Tile experiment requires BoT-SORT without ReID")
        tile_tracker = BOTSORT(IterableSimpleNamespace(**tracker_config), frame_rate=30)
        tile_tracker.reset()
    labels = (
        json.loads(args.annotations.read_text(encoding="utf-8"))
        if args.annotations
        else None
    )
    if labels and labels["video_sha256"] != sha256(args.video):
        parser.error("Annotations belong to a different video")
    labelled_indices = {f["frame"] for f in labels["frames"]} if labels else set()
    capture = cv2.VideoCapture(str(args.video))
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not np.isfinite(fps) or fps <= 0:
        parser.error("Video FPS must be finite and positive")
    metadata = {
        "fps": fps,
        "frame_count": int(capture.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    metadata["duration_seconds"] = metadata["frame_count"] / fps
    production_stream = iter(processor.process_video(args.video)) if processor else None
    camera = CameraMotionMonitor(fps) if processor else None
    if processor:
        capture.release()
    frames, raw_frames, failures = [], [], []
    process = psutil.Process()
    observed_peak_rss = process.memory_info().rss
    raw_detections = []
    endpoints = TrackEndpoints()
    prefilter_counts, filter_statuses = [], []

    def capture_raw(predictor):
        # Registered before model.track installs tracker callbacks: raw NMS detections.
        raw_detections.clear()
        result = predictor.results[0]
        prefilter_counts.append(len(result.boxes))
        info = {"status": "disabled"}
        if args.scene_filter == "pitch":
            keep, info = pitch_box_selection(
                result.orig_img, result.boxes.xyxy.cpu().numpy()
            )
            result = result[keep]
            predictor.results[0] = result
        filter_statuses.append(info)
        for box, score in zip(
            result.boxes.xyxy.cpu().numpy(), result.boxes.conf.cpu().numpy()
        ):
            raw_detections.append(
                {"id": 0, "box": box.tolist(), "confidence": float(score)}
            )

    if not args.tiles:
        model.add_callback("on_predict_postprocess_end", capture_raw)
    started = time.perf_counter()
    try:
        index = 0
        while args.end is None or index < args.end:
            if production_stream:
                try:
                    index, timestamp, frame, tracked, ground = next(production_stream)
                except StopIteration:
                    break
                result = model.predictor.results[0]
                camera.update(index, frame, tracked.xyxy)
            else:
                ok, frame = capture.read()
                if not ok:
                    break
                timestamp = index / fps
            if index < args.start:
                index += 1
                continue
            if not processor:
                if args.tiles:
                    result, raw, before, info = tiled_result(
                        model, tile_tracker, frame, args, device, torch
                    )
                    raw_detections[:] = raw
                    prefilter_counts.append(before)
                    filter_statuses.append(info)
                else:
                    from app.cv.processor import inference_size_for_frame

                    result = model.track(
                        frame,
                        persist=True,
                        classes=[0],
                        conf=args.conf,
                        iou=0.5,
                        imgsz=args.imgsz or inference_size_for_frame(frame),
                        half=device == "cuda",
                        device=device,
                        tracker=args.tracker,
                        verbose=False,
                    )[0]
            detections = []
            if result.boxes.id is not None:
                boxes = result.boxes.xyxy.cpu().numpy()
                ids = result.boxes.id.cpu().numpy().astype(int)
                scores = result.boxes.conf.cpu().numpy()
                keypoints = (
                    result.keypoints.xy.cpu().numpy()
                    if result.keypoints is not None
                    else np.zeros((len(boxes), 17, 2))
                )
                kp_conf = (
                    result.keypoints.conf.cpu().numpy()
                    if result.keypoints is not None
                    else np.zeros((len(boxes), 17))
                )
                for box, tid, score, xy, confidence in zip(
                    boxes, ids, scores, keypoints, kp_conf
                ):
                    ankles = [
                        xy[k]
                        for k in (15, 16)
                        if confidence[k] >= 0.4 and np.isfinite(xy[k]).all()
                    ]
                    bbox = np.array([(box[0] + box[2]) / 2, box[3]])
                    mean = np.mean(ankles, axis=0) if ankles else bbox
                    positions = {
                        "left": xy[15].tolist() if confidence[15] >= 0.4 else None,
                        "right": xy[16].tolist() if confidence[16] >= 0.4 else None,
                        "mean": mean.tolist(),
                        "bbox": bbox.tolist(),
                    }
                    if args.continuity != "none":
                        endpoints.add(int(tid), timestamp, mean, box, torso_histogram(frame, box))
                    detections.append(
                        {
                            "id": int(tid),
                            "box": box.tolist(),
                            "confidence": float(score),
                            "positions": positions,
                            "keypoints": xy.tolist(),
                            "keypoint_confidence": confidence.tolist(),
                        }
                    )
            frames.append(
                {"frame": index, "timestamp": timestamp, "detections": detections}
            )
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
        # Retain native tracker output for link auditing. The exact same linking
        # function and camera/timestamp gates are used by the application service.
        (args.output / "tracker_tracks.json").write_text(json.dumps(frames), encoding="utf-8")
        aliases, continuity = continuity_result(
            endpoints, camera.summary()["status"] if camera else "unknown",
            processor.timestamps_reliable if processor else False, args.continuity,
        )
        for frame_record in frames:
            for detection in frame_record["detections"]:
                detection["id"] = aliases.get(detection["id"], detection["id"])
        elapsed = time.perf_counter() - started
        summary = {
            "video": str(args.video.resolve()),
            "video_sha256": sha256(args.video),
            "metadata": metadata,
            "model_sha256": sha256(args.model),
            "ultralytics": ultralytics.__version__,
            "torch": torch.__version__,
            "device": device,
            "experiment": args.experiment,
            "timestamp_utc": run_started_utc,
            "git_commit": run_commit,
            "git_dirty": run_dirty,
            "harness_sha256": harness_hash,
            "processor_sha256": processor_hash,
            "model": str(args.model.resolve()),
            "model_task": model.task,
            "config": {
                "continuity": args.continuity,
                "tracker": args.tracker,
                "conf": args.conf,
                "iou": 0.5,
                "imgsz": args.imgsz,
                "start": args.start,
                "end": args.end,
                "scene_filter": args.scene_filter,
                "tiling": {"grid": [2, 2], "overlap": 0.15, "global_nms_iou": 0.5}
                if args.tiles
                else None,
                "production_profile": production_profile if args.production else None,
            },
            "technical": technical_metrics(frames),
            "processing_seconds": elapsed,
            "processing_fps": len(frames) / elapsed if elapsed else 0,
            "processing_to_video_duration": elapsed / (len(frames) / fps)
            if frames
            else None,
            "failures": failures,
            "ground_truth": evaluate_labels(frames, labels) if labels else None,
        }
        if labels:
            raw_metrics = evaluate_labels(raw_frames, labels)
            summary["detection_ground_truth"] = {
                k: raw_metrics[k]
                for k in (
                    "labelled_frames",
                    "iou_threshold",
                    "tp",
                    "fp",
                    "fn",
                    "precision",
                    "recall",
                    "f1",
                )
            }
            summary["annotation_sha256"] = sha256(args.annotations)
        summary["raw_detections"] = sum(len(f["detections"]) for f in raw_frames)
        summary["scene_filter"] = {
            "input_boxes": sum(prefilter_counts),
            "accepted_boxes": summary["raw_detections"],
            "available_frames": sum(
                info["status"] == "available" for info in filter_statuses
            ),
            "unknown_frames": sum(
                info["status"] == "unknown" for info in filter_statuses
            ),
        }
        if processor:
            summary["config"]["imgsz"] = (
                "native max dimension, rounded to 32, clipped 640..1280"
            )
            summary["camera_motion"] = camera.summary()
            summary["timestamps_reliable"] = processor.timestamps_reliable
            summary["actual_video_processor"] = True
        summary["observed_peak_rss_bytes"] = observed_peak_rss
        summary["continuity"] = continuity
        summary["continuity_code_sha256"] = sha256(ROOT / "backend/app/cv/continuity.py")
        summary["memory_method"] = (
            "psutil RSS sampled after each frame; includes model, not a continuous peak"
        )
        (args.output / "summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        (args.output / "tracks.json").write_text(json.dumps(frames), encoding="utf-8")
        (args.output / "detections.json").write_text(
            json.dumps(raw_frames), encoding="utf-8"
        )
        with (args.output / "tracks.csv").open(
            "w", newline="", encoding="utf-8"
        ) as stream:
            writer = csv.writer(stream)
            writer.writerow(
                ["frame", "timestamp", "id", "x1", "y1", "x2", "y2", "confidence"]
            )
            for frame in frames:
                for detection in frame["detections"]:
                    writer.writerow(
                        [
                            frame["frame"],
                            frame["timestamp"],
                            detection["id"],
                            *detection["box"],
                            detection["confidence"],
                        ]
                    )
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
