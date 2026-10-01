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
    from app.cv.camera import CameraMotionMonitor

    processor = VideoProcessor(settings.model_weights)
    from app.cv.visualizer import AnnotationManager

    annotator = AnnotationManager()
    points, gallery, preview, annotated_preview = {}, {}, None, None
    count = 0
    camera = CameraMotionMonitor(job.video["fps"])
    track_frames = {}
    for index, timestamp, frame, detections, ankles in processor.process_video(
        path, settings.max_video_frames
    ):
        count += 1
        camera.update(index, frame, detections.xyxy)
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
                track_frames[tid] = track_frames.get(tid, 0) + 1
                point = ankles[i]
                if not np.isfinite(point).all():
                    continue
                # Persist <=10 samples/second per track; timestamps preserve correct units.
                samples = points.setdefault(tid, [])
                if not samples or timestamp - samples[-1][0] >= 0.1 - 1e-8:
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
        "track_frame_counts": track_frames,
        "camera_motion": camera.summary(),
        "timestamps_reliable": processor.timestamps_reliable,
    }, candidates


def report(job):
    tid = job.selected_player_id
    samples = job.tracks["points"].get(str(tid), [])
    if not samples:
        raise ValueError("Selected player has no movement observations")
    camera = job.tracks.get("camera_motion", {"status": "unknown"})
    calibration_provided = bool(job.calibration)
    calibrated = calibration_provided and (
        job.demo
        or (
            job.calibration.get("stationary_camera", False)
            and camera["status"] == "no_motion_detected"
            and job.tracks.get("timestamps_reliable", False)
        )
    )
    dimensions = [job.video["width"], job.video["height"]]
    warnings = []
    metrics = {"total_distance_m": None, "top_speed_kmh": None, "sprint_count": None}
    rejected = 0
    # Invalid/out-of-frame points and time gaps also split the image path.
    segments, segment, previous_time = [], [], None
    valid_samples, segment_start_times = [], set()
    for row in samples:
        if (
            len(row) != 3
            or not np.isfinite(row).all()
            or row[0] < 0
            or not 0 <= row[1] < dimensions[0]
            or not 0 <= row[2] < dimensions[1]
        ):
            previous_time = None
            if segment:
                segments.append(segment)
                segment = []
            continue
        if previous_time is not None and row[0] <= previous_time:
            continue
        if previous_time is not None and row[0] - previous_time > 0.5 and segment:
            segments.append(segment)
            segment = []
        if not segment:
            segment_start_times.add(row[0])
        segment.append(row[1:])
        valid_samples.append(row)
        previous_time = row[0]
    if segment:
        segments.append(segment)
    samples = valid_samples
    if len(samples) < 2:
        raise ValueError("Selected player needs at least two finite movement observations")
    movement = [point for segment in segments for point in segment]
    if calibrated:
        c = job.calibration
        dimensions = [c["field_length"], c["field_width"]]
        transformer = FieldTransformer(
            c["points"], *dimensions, frame_size=(job.video["width"], job.video["height"])
        )
        analytics = MatchAnalytics(job.video["fps"], *dimensions)
        accepted_samples = []
        for row in samples:
            if row[0] in segment_start_times:
                analytics.pending_break.add(int(tid))
            if transformer.contains(row[1:]):
                point = transformer.transform_points([row[1:]])[0]
                analytics.update_metrics(tid, point, row[0])
                accepted_samples.append(row)
            else:
                analytics.update_metrics(tid, [np.nan, np.nan], row[0])
        if len(accepted_samples) < 2:
            raise ValueError("Not enough observations inside the calibrated field. Check the corner points.")
        samples = accepted_samples
        movement = analytics.player_data[tid]
        segments = analytics.segments[tid]
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
        if calibration_provided:
            warnings.append(
                "Physical metrics unavailable: confirm a stationary camera and use a clip with "
                "no detected camera motion. The path remains in image coordinates."
            )
        else:
            warnings.append(
                "No field calibration: movement is in image pixels. Distance, speed and sprints are unavailable."
            )
    if not job.demo and camera["status"] != "no_motion_detected":
        warnings.append(
            "Camera motion detected."
            if camera["status"] == "moving"
            else "Camera stability could not be established; use a longer, textured fixed-camera clip."
        )
    if not job.demo and not job.tracks.get("timestamps_reliable", False):
        warnings.append("Decoder timestamps unavailable or non-monotonic; physical metrics are unavailable.")
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
    normalized_segments = [
        [
            [
                round(float(np.clip(x / dimensions[0], 0, 0.999)), 4),
                round(float(np.clip(y / dimensions[1], 0, 0.999)), 4),
            ]
            for x, y in segment
        ]
        for segment in segments
    ]
    step = max(1, math.ceil(len(normalized) / 1000))
    result = {
        "analysis_id": job.id,
        "player_id": tid,
        "demo": job.demo,
        "calibrated": calibrated,
        "calibration_provided": calibration_provided,
        "physical_metrics_status": "demo" if job.demo else "estimated" if calibrated else "unavailable",
        "physical_accuracy": "not_validated",
        "camera_motion": camera,
        "timestamp_basis": "synthetic"
        if job.demo
        else "decoder_pts"
        if job.tracks.get("timestamps_reliable")
        else "nominal_fps_fallback",
        "coordinate_space": "field" if calibrated else "image",
        "metrics": metrics,
        "movement": normalized[::step],
        # Preserve segment endpoints when thinning; never draw a line across a gap.
        "movement_segments": [
            segment[::step] + ([segment[-1]] if (len(segment) - 1) % step else [])
            for segment in normalized_segments
            if segment
        ],
        "heatmap": heatmap.tolist(),
        "observations": len(samples),
        "duration_seconds": job.video["duration_seconds"],
        "frames_processed": job.tracks["frames_processed"],
        "device": job.tracks["device"],
        "rejected_segments": rejected,
        "warnings": warnings,
        "annotated_preview": job.tracks.get("annotated_preview"),
        "tracking_quality": {
            "observed_frame_coverage": (
                job.tracks["track_frame_counts"].get(str(tid), 0) / job.tracks["frames_processed"]
            )
            if not job.demo and job.tracks.get("track_frame_counts")
            else None,
            "trajectory_segments": len(segments),
            "definition": "Selected ID detected frames / decoded frames; segments split at gaps >0.5s "
            "or invalid coordinates (also >45km/h jumps after calibration). Not accuracy.",
        },
    }
    if calibrated and not job.demo:
        from app.cv.visualizer import RadarVisualizer

        result["radar"] = jpeg(RadarVisualizer().draw_radar([movement[-1]], [tid], None, [], dimensions))
    return result
