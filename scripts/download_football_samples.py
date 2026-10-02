"""Fetch only four CC BY 4.0 UVY soccer MP4 entries, never the full 3.3 GB ZIP.

The publisher's archive supports HTTP byte ranges. All requests must return 206
with the exact Content-Range. By default no annotations are downloaded: freeze
the independent manual subset before opting into publisher annotations.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import zlib
from pathlib import Path, PurePosixPath
from urllib.request import Request, urlopen

RECORD = "https://zenodo.org/records/21303900"
API = "https://zenodo.org/api/records/21303900"
LICENSE = "https://creativecommons.org/licenses/by/4.0/"
NETWORK_CAP = 200_000_000
SELECTION_CAP = 40_000_000
SOURCE_NAMES = {
    "UVY/soccer_V01/soccer_v01.mp4": "soccer_V01.mp4",
    "UVY/soccer_V02/soccer_V02.mp4": "soccer_V02.mp4",
    "UVY/soccer_V03/soccer_V03.mp4": "soccer_V03.mp4",
    "UVY/soccer_V04/vid__fkPwtg7ozU.mp4": "soccer_V04.mp4",
}
ANNOTATION_NAMES = {
    f"UVY/soccer_V0{sequence}/gt/{name}": f"soccer_V0{sequence}_{name}"
    for sequence in (1, 2, 4)
    for name in ("gt.txt", "labels.txt")
}


class BoundedHTTP:
    def __init__(self) -> None:
        self.network_bytes = 0

    def read(self, url: str, limit: int) -> bytes:
        if limit < 0 or self.network_bytes + limit > NETWORK_CAP:
            raise ValueError("Refusing request above the 200 MB network budget")
        with urlopen(Request(url), timeout=60) as response:
            data = response.read(limit + 1)
        self.network_bytes += len(data)
        if len(data) > limit or self.network_bytes > NETWORK_CAP:
            raise ValueError("Response exceeded the bounded network budget")
        return data

    def byte_range(self, url: str, start: int, length: int, archive_size: int) -> bytes:
        if start < 0 or length <= 0 or start + length > archive_size:
            raise ValueError("Invalid ZIP byte range")
        end = start + length - 1
        headers = {"Range": f"bytes={start}-{end}"}
        expected = f"bytes {start}-{end}/{archive_size}"
        if self.network_bytes + length > NETWORK_CAP:
            raise ValueError("Refusing request above the 200 MB network budget")
        with urlopen(Request(url, headers=headers), timeout=60) as response:
            if (
                response.status != 206
                or response.headers.get("Content-Range") != expected
            ):
                raise ValueError(
                    "Server did not honor the exact range; refusing full download"
                )
            data = response.read(length + 1)
        self.network_bytes += len(data)
        if len(data) != length or self.network_bytes > NETWORK_CAP:
            raise ValueError("Range response has unexpected length or exceeded budget")
        return data


def central_directory(http: BoundedHTTP, url: str, archive_size: int) -> list[dict]:
    tail_size = min(65_557, archive_size)
    tail = http.byte_range(url, archive_size - tail_size, tail_size, archive_size)
    position = tail.rfind(b"PK\x05\x06")
    if position < 0 or position + 22 > len(tail):
        raise ValueError("ZIP end-of-directory signature is missing")
    _, disk, cd_disk, on_disk, total, cd_size, cd_offset, comment_len = (
        struct.unpack_from("<4s4H2IH", tail, position)
    )
    if disk or cd_disk or on_disk != total or total == 65_535:
        raise ValueError("Multi-disk and ZIP64 archives are unsupported")
    if position + 22 + comment_len != len(tail) or not 0 < cd_size <= 10_000_000:
        raise ValueError("Unexpected ZIP central-directory size or comment")
    data = http.byte_range(url, cd_offset, cd_size, archive_size)
    entries = []
    offset = 0
    while offset < len(data):
        if data[offset : offset + 4] != b"PK\x01\x02" or offset + 46 > len(data):
            raise ValueError("Invalid central-directory entry")
        values = struct.unpack_from("<4s6H3I5H2I", data, offset)
        name_len, extra_len, entry_comment_len = values[10:13]
        name = data[offset + 46 : offset + 46 + name_len].decode("utf-8")
        entries.append(
            {
                "name": name,
                "flags": values[3],
                "compression": values[4],
                "crc32": values[7],
                "compressed_bytes": values[8],
                "uncompressed_bytes": values[9],
                "offset": values[-1],
            }
        )
        offset += 46 + name_len + extra_len + entry_comment_len
    if offset != len(data) or len(entries) != total:
        raise ValueError("Central-directory entry count or length differs")
    return entries


def selected_entries(
    entries: list[dict], include_annotations: bool = False
) -> list[dict]:
    selected = []
    for entry in entries:
        name = entry["name"]
        if (
            name in SOURCE_NAMES
            or re.fullmatch(
                r"UVY/soccer_V0[1-4]/(?:video_info\.txt|seqinfo\.ini)", name
            )
            or (include_annotations and name in ANNOTATION_NAMES)
        ):
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("Unsafe archive member path")
            if entry["flags"] & 1 or entry["compression"] not in (0, 8):
                raise ValueError("Encrypted or unsupported compressed entry")
            selected.append(entry)
    if {entry["name"] for entry in selected if entry["name"].endswith(".mp4")} != set(
        SOURCE_NAMES
    ):
        raise ValueError("The expected four source videos are absent or renamed")
    if include_annotations and {
        entry["name"] for entry in selected if entry["name"] in ANNOTATION_NAMES
    } != set(ANNOTATION_NAMES):
        raise ValueError("Expected publisher annotation members are absent or renamed")
    if sum(entry["compressed_bytes"] for entry in selected) > SELECTION_CAP:
        raise ValueError("Selected source entries exceed the 40 MB budget")
    if any(entry["uncompressed_bytes"] > SELECTION_CAP for entry in selected):
        raise ValueError("Archive member exceeds the decompression budget")
    return selected


def extract_entry(http: BoundedHTTP, url: str, size: int, entry: dict) -> bytes:
    header = http.byte_range(url, entry["offset"], 30, size)
    if header[:4] != b"PK\x03\x04":
        raise ValueError("ZIP local entry signature differs")
    values = struct.unpack("<4s5H3I2H", header)
    name_len, extra_len = values[-2:]
    if name_len + extra_len > 8_192:
        raise ValueError("Unexpected local ZIP header size")
    length = name_len + extra_len + entry["compressed_bytes"]
    data = http.byte_range(url, entry["offset"] + 30, length, size)
    if (
        data[:name_len].decode("utf-8") != entry["name"]
        or values[3] != entry["compression"]
    ):
        raise ValueError("Local and central ZIP headers disagree")
    compressed = data[name_len + extra_len :]
    if entry["compression"] == 8:
        decompressor = zlib.decompressobj(-15)
        result = decompressor.decompress(compressed, entry["uncompressed_bytes"] + 1)
        if not decompressor.eof or decompressor.unconsumed_tail:
            raise ValueError("Truncated or oversized compressed member")
    else:
        result = compressed
    if (
        len(result) != entry["uncompressed_bytes"]
        or zlib.crc32(result) & 0xFFFFFFFF != entry["crc32"]
    ):
        raise ValueError("Source entry failed its byte count or CRC32 check")
    return result


def inspect_video(path: Path, make_preview: bool) -> dict:
    import cv2

    capture = cv2.VideoCapture(str(path))
    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if not capture.isOpened() or fps <= 0 or frames <= 0:
            raise ValueError(f"Source video is undecodable: {path.name}")
        if make_preview:
            raw_frames = []
            for index in [0, frames // 2, frames - 1]:
                capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                ok, frame = capture.read()
                if not ok:
                    raise ValueError(f"Failed to decode raw source frame {index}")
                frame = cv2.resize(frame, (960, round(height * 960 / width)))
                cv2.putText(
                    frame,
                    f"{path.stem} raw frame {index}",
                    (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (255, 255, 255),
                    2,
                )
                raw_frames.append(frame)
            cv2.imwrite(
                str(path.with_name(f"{path.stem}_raw_contact.jpg")),
                cv2.vconcat(raw_frames),
            )
        return {
            "width": width,
            "height": height,
            "fps": fps,
            "frames": frames,
            "duration_seconds": frames / fps,
        }
    finally:
        capture.release()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("test-artifacts/football/source")
    )
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument(
        "--include-annotations",
        action="store_true",
        help="Fetch publisher gt.txt and labels.txt for V01/V02/V04 after freezing independent manual GT",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    http = BoundedHTTP()
    record = json.loads(http.read(API, 256_000))
    if record["metadata"]["license"]["id"] != "cc-by-4.0":
        raise ValueError("Publisher licence changed; source must be reviewed")
    archive = next(item for item in record["files"] if item["key"] == "UVY.zip")
    url, archive_size = archive["links"]["self"], archive["size"]
    entries = selected_entries(
        central_directory(http, url, archive_size), args.include_annotations
    )
    videos = []
    annotations = []
    for entry in entries:
        member = PurePosixPath(entry["name"])
        filename = SOURCE_NAMES.get(entry["name"]) or ANNOTATION_NAMES.get(
            entry["name"]
        )
        if filename is None:
            filename = f"{member.parent.name}_{member.name}"
        path = output / filename
        if path.parent != output:
            raise ValueError(
                "Output member must remain inside selected output directory"
            )
        cached = (
            path.read_bytes()
            if path.is_file() and path.stat().st_size <= SELECTION_CAP
            else b""
        )
        if (
            len(cached) == entry["uncompressed_bytes"]
            and zlib.crc32(cached) & 0xFFFFFFFF == entry["crc32"]
        ):
            data = cached
        else:
            data = extract_entry(http, url, archive_size, entry)
            temporary = path.with_suffix(path.suffix + ".part")
            try:
                temporary.write_bytes(data)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
        if path.suffix == ".mp4":
            video = {
                "name": path.stem,
                "file": filename,
                "source_entry": entry,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
                **inspect_video(path, not args.no_preview),
            }
            videos.append(video)
            print(json.dumps(video))
        elif entry["name"] in ANNOTATION_NAMES:
            annotations.append(
                {
                    "file": filename,
                    "source_entry": entry,
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
    manifest = {
        "source_record": RECORD,
        "doi": "10.5281/zenodo.21303900",
        "authors": ["Elton Alencar", "Rosiane de Freitas"],
        "license": "CC BY 4.0",
        "license_url": LICENSE,
        "archive_url": url,
        "archive_bytes": archive_size,
        "archive_publisher_checksum": archive["checksum"],
        "network_bytes_this_run": http.network_bytes,
        "full_archive_downloaded": False,
        "annotations_downloaded": args.include_annotations,
        "annotation_provenance": (
            "Publisher semi-automatic YOLO-World annotations with manual review and correction via CVAT; "
            "distinct from the independently drawn manual subset."
            if args.include_annotations
            else None
        ),
        "annotations": annotations,
        "notes": "Original MP4 bytes extracted and CRC checked. Contact sheets contain only raw frames and labels.",
        "videos": videos,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Network bytes this run: {http.network_bytes:,}; manifest: {output / 'manifest.json'}"
    )


if __name__ == "__main__":
    main()
