"""Opt-in bounded official model downloads. Never invoked by the server."""

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        choices=("yolo11n-pose.pt", "yolo11s-pose.pt", "yolo11n.pt"),
        default="yolo11n-pose.pt",
    )
    args = parser.parse_args()
    target = Path(__file__).resolve().parents[1] / "backend/weights" / args.model
    url = f"https://github.com/ultralytics/assets/releases/download/v8.3.0/{args.model}"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_suffix(".part")
        try:
            with urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 35_000_000:
                        raise RuntimeError(
                            "Unexpected model download size (over 35 MB)"
                        )
                    handle.write(chunk)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
    print(
        f"{target.name}: {target.stat().st_size:,} bytes, SHA256={hashlib.sha256(target.read_bytes()).hexdigest()}; source={url}"
    )


if __name__ == "__main__":
    main()
