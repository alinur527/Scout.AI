import base64
import math

import cv2
import numpy as np

from app.cv.analytics import MatchAnalytics
from app.cv.calibration import FieldTransformer


def jpeg(frame, width=640):
    h, w = frame.shape[:2]
    resized = cv2.resize(frame, (min(width, w), max(1, round(h * min(width, w) / w))))
    ok, encoded = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, 75])
    if not ok:
        raise ValueError("Could not create video preview")
    return "data:image/jpeg;base64," + base64.b64encode(encoded).decode("ascii")


def detect(job, settings, progress):
    path = settings.upload_dir / job.stored_filename
    if job.demo:
        cap = cv2.VideoCapture(str(path))
        try:
            ok, frame = cap.read()
            if not ok:
                raise ValueError("Demo input is no longer readable")
        finally:
            cap.release()
        # Explicit deterministic fixtures, never used by real mode.
        tracks = {}
        for tid in (1, 2):
            tracks[str(tid)] = [
                [
                    i / 10,
                    (0.25 + i / 1000) * job.video["width"],
                    (0.4 + 0.1 * math.sin(i / 12 + tid)) * job.video["height"],
                ]
                for i in range(100)
            ]
        progress(75)
        return {"points": tracks, "preview": jpeg(frame), "device": "demo", "frames_processed": 100}, [
            {"id": tid, "thumbnail": None, "observations": 100, "label": f"Demo player {tid}"}
            for tid in (1, 2)
        ]

    from app.cv.processor import VideoProcessor

    processor = VideoProcessor(settings.model_weights)
    from app.cv.visualizer import AnnotationManager

    annotator = AnnotationManager()
    points, gallery, preview, annotated_preview = {}, {}, None, None
    count = 0
    for index, frame, detections, ankles in processor.process_video(path, settings.max_video_frames):
        count += 1
        if preview is None:
            preview = jpeg(frame)
        if detections.tracker_id is not None:
            if len(points) > 250:
                raise ValueError("Too many fragmented tracks. Use a shorter, steady-camera clip.")
            if annotated_preview is None and len(detections):
                annotated_preview = jpeg(
                    annotator.annotate_frame(
                        frame, detections, [f"ID {int(tid)}" for tid in detections.tracker_id]
                    )
                )
            for i, track in enumerate(detections.tracker_id):
                tid = str(int(track))
                point = ankles[i]
                if not np.isfinite(point).all():
                    continue
                # Persist <=10 samples/second per track; timestamps preserve correct units.
                samples = points.setdefault(tid, [])
                timestamp = index / job.video["fps"]
                if not samples or timestamp - samples[-1][0] >= 0.095:
                    samples.append(
                        [round(timestamp, 4), round(float(point[0]), 2), round(float(point[1]), 2)]
                    )
                if tid not in gallery:
                    x1, y1, x2, y2 = map(int, detections.xyxy[i])
                    crop = frame[max(0, y1) : min(frame.shape[0], y2), max(0, x1) : min(frame.shape[1], x2)]
                    if crop.size:
                        gallery[tid] = {
                            "id": int(tid),
                            "thumbnail": jpeg(crop, 120),
                            "label": f"Player {tid}",
                        }
        if index % max(1, int(job.video["fps"])) == 0:
            progress(min(75, 5 + int(70 * count / job.video["frame_count"])))
    if count < job.video["frame_count"] * 0.9:
        raise ValueError("Video decoding stopped early; the file may be truncated or corrupted")
    candidates = [
        dict(value, observations=len(points[tid])) for tid, value in gallery.items() if len(points[tid]) >= 2
    ]
    if not candidates:
        raise ValueError("No trackable people found. Try a clearer, longer clip with visible players.")
    return {
        "points": points,
        "preview": preview,
        "annotated_preview": annotated_preview,
        "device": processor.device,
        "frames_processed": count,
    }, candidates


def report(job):
    tid = job.selected_player_id
    samples = job.tracks["points"].get(str(tid), [])
    if not samples:
        raise ValueError("Selected player has no movement observations")
    calibrated = bool(job.calibration)
    dimensions = [job.video["width"], job.video["height"]]
    movement = [[row[1], row[2]] for row in samples]
    warnings = []
    metrics = {"total_distance_m": None, "top_speed_kmh": None, "sprint_count": None}
    rejected = 0
    if calibrated:
        c = job.calibration
        dimensions = [c["field_length"], c["field_width"]]
        transformer = FieldTransformer(c["points"], *dimensions)
        samples = [row for row in samples if transformer.contains(row[1:])]
        if len(samples) < 2:
            raise ValueError("Not enough observations inside the calibrated field. Check the corner points.")
        movement = transformer.transform_points([row[1:] for row in samples]).tolist()
        analytics = MatchAnalytics(job.video["fps"], *dimensions)
        for row, point in zip(samples, movement):
            analytics.update_metrics(tid, point, row[0])
        movement = analytics.player_data[tid]
        rejected = analytics.rejected[tid]
        metrics = {
            "total_distance_m": round(analytics.get_total_distance(tid), 2),
            "top_speed_kmh": round(max(analytics.player_speeds[tid], default=0), 2),
            "sprint_count": analytics.sprint_count[tid],
        }
        warnings.append(
            "Estimates depend on manual field calibration and a static camera; tracking IDs may fragment."
        )
    else:
        warnings.append(
            "No field calibration: movement is in image pixels. Distance, speed and sprints are unavailable."
        )
    if job.demo:
        # Independent of video content: deliberate fixture numbers, labelled in every response.
        metrics = {"total_distance_m": 1240.5 + tid * 10, "top_speed_kmh": 24.8, "sprint_count": 4}
        warnings = ["DEMO: synthetic trajectories and sample metrics. No model inference was performed."]
    heatmap = np.zeros((12, 20), dtype=int)
    normalized = []
    for x, y in movement:
        nx, ny = float(np.clip(x / dimensions[0], 0, 0.999)), float(np.clip(y / dimensions[1], 0, 0.999))
        heatmap[int(ny * 12), int(nx * 20)] += 1
        normalized.append([round(nx, 4), round(ny, 4)])
    step = max(1, math.ceil(len(normalized) / 1000))
    result = {
        "analysis_id": job.id,
        "player_id": tid,
        "demo": job.demo,
        "calibrated": calibrated,
        "coordinate_space": "field" if calibrated else "image",
        "metrics": metrics,
        "movement": normalized[::step],
        "heatmap": heatmap.tolist(),
        "observations": len(samples),
        "duration_seconds": job.video["duration_seconds"],
        "frames_processed": job.tracks["frames_processed"],
        "device": job.tracks["device"],
        "rejected_segments": rejected,
        "warnings": warnings,
        "annotated_preview": job.tracks.get("annotated_preview"),
    }
    if calibrated and not job.demo:
        from app.cv.visualizer import RadarVisualizer

        result["radar"] = jpeg(RadarVisualizer().draw_radar([movement[-1]], [tid], None, [], dimensions))
    return result
