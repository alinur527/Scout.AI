"""Run a limited DEV matrix through the existing football harness/scorers.

HOLDOUT deliberately absent. Candidate freeze and held-out execution are separate.
No training, downloads, changes to weights or production defaults.
"""

import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "large-pose": ["--model", "backend/weights/yolo11s-pose.pt", "--imgsz", "0"],
    "person": ["--model", "backend/weights/yolo11n.pt", "--imgsz", "0"],
    "highres": ["--imgsz", "1920"],
    "tiles": ["--tiles", "--imgsz", "960"],
    "pitch": ["--imgsz", "0", "--scene-filter", "pitch"],
    "person-pitch": [
        "--model",
        "backend/weights/yolo11n.pt",
        "--imgsz",
        "0",
        "--scene-filter",
        "pitch",
    ],
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate", choices=list(CONFIGS), nargs="+", default=list(CONFIGS)
    )
    parser.add_argument(
        "--clips",
        choices=("117093", "118575", "steady", "zoom"),
        nargs="+",
        default=["117093", "118575"],
    )
    args = parser.parse_args()
    for name in args.candidate:
        for clip in args.clips:
            if clip in ("117093", "118575"):
                source = ROOT / f"test-artifacts/football/soccertrack/{clip}"
                video = source / "window/clip.avi"
                scorer = [
                    "scripts/score_soccertrack.py",
                    "--gt",
                    str(source / "gt.txt"),
                ]
            else:
                video = ROOT / f"test-artifacts/football/clips/{clip}/clip.avi"
                sequence, start = ("V04", "0") if clip == "steady" else ("V02", "100")
                scorer = [
                    "scripts/score_uvy.py",
                    "--gt",
                    f"test-artifacts/football/source/soccer_{sequence}_gt.txt",
                    "--labels",
                    f"test-artifacts/football/source/soccer_{sequence}_labels.txt",
                    "--source-start",
                    start,
                ]
            output = ROOT / "test-artifacts/small-player" / name / clip
            output.mkdir(parents=True, exist_ok=True)
            with (output / "run.log").open("w", encoding="utf-8") as log:
                subprocess.run(
                    [
                        sys.executable,
                        "scripts/validate_football_cv.py",
                        str(video),
                        "--experiment",
                        name,
                        "--output",
                        str(output),
                        *CONFIGS[name],
                    ],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
                subprocess.run(
                    [sys.executable, scorer[0], str(output), *scorer[1:]],
                    cwd=ROOT,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            summary = json.loads((output / "summary.json").read_text())
            metrics = json.loads((output / "publisher_metrics.json").read_text())
            print(
                json.dumps(
                    {
                        "candidate": name,
                        "clip": clip,
                        "detection": metrics["detection"],
                        "tracked_f1": metrics["tracking"]["f1"],
                        "switches": metrics["tracking"]["id_switches"],
                        "fragments": metrics["tracking"]["fragmentations"],
                        "fps": summary["processing_fps"],
                    }
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
