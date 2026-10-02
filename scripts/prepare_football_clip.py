"""Trim a reproducible raw clip and create contact sheets BEFORE model inference."""

import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--frames", type=int, default=250)
    parser.add_argument("--roi", type=int, nargs=4)
    parser.add_argument("--samples", type=int, default=50)
    args = parser.parse_args()
    if args.frames < 1 or args.start < 0 or args.samples < 1:
        parser.error("Frame counts must be positive")
    args.output.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(args.source))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width, height = (
        int(cap.get(prop))
        for prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT)
    )
    if not np.isfinite(fps) or fps <= 0 or not width or not height:
        parser.error("Source cannot be decoded")
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.start)
    target = args.output / "clip.avi"
    writer = cv2.VideoWriter(
        str(target), cv2.VideoWriter_fourcc(*"MJPG"), fps, (width, height)
    )
    samples = set(map(int, np.linspace(0, args.frames - 1, args.samples, dtype=int)))
    tiles, actual = [], 0
    try:
        for index in range(args.frames):
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(frame)
            actual += 1
            if index in samples:
                cv2.imwrite(str(args.output / f"raw-{index:05d}.png"), frame)
                if args.roi:
                    x1, y1, x2, y2 = args.roi
                    frame = frame[y1:y2, x1:x2]
                tile = cv2.resize(frame, (400, 225))
                cv2.putText(
                    tile,
                    f"frame {index}",
                    (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),
                    3,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    tile,
                    f"frame {index}",
                    (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                tiles.append(tile)
    finally:
        writer.release()
        cap.release()
    for offset in range(0, len(tiles), 10):
        batch = tiles[offset : offset + 10]
        batch += [np.zeros_like(tiles[0])] * (10 - len(batch))
        sheet = np.vstack([np.hstack(batch[:5]), np.hstack(batch[5:])])
        cv2.imwrite(str(args.output / f"contact-{offset // 10}.png"), sheet)
    with args.source.open("rb") as stream:
        source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    with target.open("rb") as stream:
        clip_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    (args.output / "metadata.json").write_text(
        json.dumps(
            {
                "source": str(args.source),
                "source_sha256": source_hash,
                "video_sha256": clip_hash,
                "source_start_frame": args.start,
                "frames": actual,
                "fps": fps,
                "width": width,
                "height": height,
                "sampled_frames": sorted(samples),
                "roi": args.roi,
                "derivation": "OpenCV MJPG, original resolution/FPS; no generated or interpolated frames",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
