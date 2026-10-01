from app.cv.validation import evaluate_labels, technical_metrics


def test_roi_matching_does_not_count_outside_people_or_double_match():
    labels = {
        "roi": [0, 0, 20, 20],
        "frames": [
            {
                "frame": 0,
                "objects": [{"id": "a", "box": [0, 0, 10, 10]}, {"id": "b", "box": [10, 10, 20, 20]}],
            }
        ],
    }
    frames = [
        {
            "frame": 0,
            "detections": [
                {"id": 1, "box": [0, 0, 10, 10]},
                {"id": 2, "box": [0, 0, 10, 10]},
                {"id": 3, "box": [30, 30, 40, 40]},
            ],
        }
    ]
    result = evaluate_labels(frames, labels)
    assert (result["tp"], result["fp"], result["fn"]) == (1, 1, 1)
    assert result["precision"] == result["recall"] == result["f1"] == 0.5


def test_switch_and_fragment_have_distinct_definitions():
    labels = {"frames": [{"frame": i, "objects": [{"id": "a", "box": [0, 0, 10, 10]}]} for i in range(4)]}
    frames = [
        {"frame": i, "detections": [{"id": pid, "box": [0, 0, 10, 10]}] if pid else []}
        for i, pid in enumerate([1, 2, None, 2])
    ]
    result = evaluate_labels(frames, labels)
    assert result["id_switches"] == result["fragmentations"] == 1
    assert result["identity_coverage"] == {"a": 0.75}


def test_empty_and_reacquired_technical_metrics():
    assert technical_metrics([])["frame_detection_coverage"] == 0
    frames = [{"frame": i, "detections": [{"id": 1, "confidence": 0.8}] if i != 1 else []} for i in range(3)]
    metrics = technical_metrics(frames)
    assert metrics["reacquired_same_id_gaps"] == metrics["lost_frame_intervals"] == 1
    assert metrics["track_ids"] == 1
    assert metrics["frame_detection_coverage"] == 2 / 3


def test_annotation_frames_outside_tested_range_are_not_counted_as_misses():
    labels = {"frames": [{"frame": i, "objects": [{"id": "a", "box": [0, 0, 10, 10]}]} for i in range(3)]}
    frames = [{"frame": 1, "detections": []}]
    result = evaluate_labels(frames, labels)
    assert result["labelled_frames"] == result["fn"] == 1
