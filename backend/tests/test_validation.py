from app.cv.validation import evaluate_labels, technical_metrics, size_recall


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


def test_small_player_bins_use_fixed_reference_and_full_scene_assignment():
    labels = {
        "frames": [
            {
                "frame": 0,
                "objects": [
                    {"id": "small", "box": [0, 0, 20, 20]},
                    {"id": "large", "box": [50, 50, 150, 150]},
                ],
            }
        ]
    }
    frames = [{"frame": 0, "detections": [{"id": 1, "box": [0, 0, 20, 20]}]}]
    sizes = size_recall(frames, labels, [1280, 720])
    assert sizes["bins"]["small"] == {"tp": 1, "fn": 0, "recall": 1}
    assert sizes["bins"]["other"] == {"tp": 0, "fn": 1, "recall": 0}
    assert size_recall([], labels, [1280, 720])["bins"]["small"]["recall"] is None


def test_soccertrack_challenge_zero_based_placeholders_are_not_dropped(tmp_path):
    import runpy
    from pathlib import Path

    loader = runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts/score_soccertrack.py"))[
        "load_labels"
    ]
    path = tmp_path / "gt.txt"
    path.write_text("0,1,10,20,30,40,-1,-1,-1,-1\n1,1,11,21,30,40,-1,-1,-1,-1\n")
    labels = loader(path, [0])
    assert labels["frames"] == [{"frame": 0, "objects": [{"id": 1, "box": [10, 20, 40, 60]}]}]
