"""Bounded opt-in three-match CC BY SoccerTrack v2 windows, not full videos.

Fetch first200 encoded samples and moov via exact HTTP ranges; create an explicitly
partial decode cache, then a valid first120-frame AVI. Never upload the decode cache.
The paired challenge GT is zero-based with -1 placeholders, unlike generic MOT docs.
"""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys

from download_football_samples import BoundedHTTP

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "test-artifacts/football/soccertrack"
LICENSE = "https://github.com/AtomScott/SoccerTrack-v2/blob/6f5c47cd3a5c38b074c44e9c98dfba48daa230d3/LICENSE-DATA"
MATCHES = [
    (
        "117093",
        "DEV",
        "B1 vs B2",
        "1qcOv7Ub9ju5qXzx_9FeIY3jkmrFWQyZ8",
        "1BHUMvKZWzJyX0uQ73_7A-e4HtXjUk5p7",
        304980773,
        304764342,
        216431,
        10785908,
        6221412,
    ),
    (
        "118575",
        "DEV",
        "C1 vs C2",
        "11Hy7QN9cI7N0fKRNjX_SYeCMnK_lXyb0",
        "16Gro5nViH_D8H71RagNUDD1sSFqxpDlt",
        287015664,
        286833901,
        181763,
        9177824,
        6122283,
    ),
    (
        "118576",
        "HOLDOUT",
        "D1 vs D2",
        "132fWwtSBIRuKVigIDK1odzQjz2mLXl3M",
        "1FxOiI9wz8EobXtuXYr7xCgihqg50NxYL",
        298409129,
        298189566,
        219563,
        10313323,
        6231376,
    ),
]


def drive_url(identity):
    return f"https://drive.usercontent.google.com/download?id={identity}&export=download&confirm=t"


def write_window(http, target, video_id, size, moov_offset, moov_size, prefix_end):
    if target.exists():
        content = target.read_bytes()
        if (
            len(content) != prefix_end + moov_size
            or content[prefix_end + 4 : prefix_end + 8] != b"moov"
        ):
            raise ValueError("Invalid existing partial cache")
        prefix = bytearray(content[:prefix_end])
        struct.pack_into(">I", prefix, 40, moov_offset - 40)
        return {
            "cached": True,
            "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
            "moov_sha256": hashlib.sha256(content[prefix_end:]).hexdigest(),
        }
    url = drive_url(video_id)
    prefix = bytearray(http.byte_range(url, 0, prefix_end, size))
    moov = http.byte_range(url, moov_offset, moov_size, size)
    if prefix[4:8] != b"ftyp" or prefix[44:48] != b"mdat" or moov[4:8] != b"moov":
        raise ValueError("Publisher MP4 layout changed")
    if (
        struct.unpack_from(">I", prefix, 40)[0] != moov_offset - 40
        or moov_offset + moov_size != size
    ):
        raise ValueError("Publisher atom sizes changed")
    hashes = {
        "prefix_sha256": hashlib.sha256(prefix).hexdigest(),
        "moov_sha256": hashlib.sha256(moov).hexdigest(),
    }
    struct.pack_into(">I", prefix, 40, prefix_end - 40)
    target.write_bytes(prefix + moov)
    return hashes | {"cached": False}


def main():
    http = BoundedHTTP()
    records = []
    for (
        match,
        split,
        event,
        vid,
        gt,
        size,
        moov_offset,
        moov_size,
        prefix_end,
        gt_size,
    ) in MATCHES:
        directory = SOURCE / match
        directory.mkdir(parents=True, exist_ok=True)
        cache = directory / "partial.decode-cache.mp4"
        ranges = write_window(
            http, cache, vid, size, moov_offset, moov_size, prefix_end
        )
        gt_file = directory / "gt.txt"
        if not gt_file.exists():
            gt_file.write_bytes(http.byte_range(drive_url(gt), 0, gt_size, gt_size))
        if gt_file.stat().st_size != gt_size:
            raise ValueError("Existing GT has unexpected size")
        clip = directory / "window/clip.avi"
        if not clip.exists():
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/prepare_football_clip.py"),
                    str(cache),
                    "--output",
                    str(clip.parent),
                    "--frames",
                    "120",
                    "--samples",
                    "12",
                ],
                check=True,
            )
        metadata = json.loads((clip.parent / "metadata.json").read_text())
        if (
            metadata["frames"] != 120
            or (metadata["width"], metadata["height"]) != (4096, 1080)
            or metadata["fps"] != 25
        ):
            raise ValueError("Window does not match the fixed selection protocol")
        record = {
            "match": match,
            "split": split,
            "event": event,
            "license": LICENSE,
            "video_url": drive_url(vid),
            "original_video_bytes": size,
            "gt_url": drive_url(gt),
            "gt_bytes": gt_size,
            "video_ranges": [[0, prefix_end], [moov_offset, moov_offset + moov_size]],
            "ranges_end_exclusive": True,
            "range_hashes": ranges,
            "partial_cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
            "gt_sha256": hashlib.sha256(gt_file.read_bytes()).hexdigest(),
            "clip": str(clip.relative_to(ROOT)),
            "gt": str(gt_file.relative_to(ROOT)),
            "metadata": metadata,
            "cache_warning": "First200 encoded samples only; future sample table entries lack payload. Valid derived AVI contains first120 decoded frames, not a complete original MP4.",
        }
        (directory / "source.json").write_text(
            json.dumps(record, indent=2), encoding="utf-8"
        )
        records.append(record)
        print(f"{match}: {split}, {event}, valid120-frame4096x1080 AVI")
    manifest = {"network_bytes_this_run": http.network_bytes, "records": records}
    (SOURCE / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"Downloaded {http.network_bytes:,} bytes; full MP4s were not downloaded")


if __name__ == "__main__":
    main()
