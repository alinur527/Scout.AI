"""Explicitly download the small official YOLO11n pose model. Never invoked by the server."""

from pathlib import Path
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
target = root / "backend/weights/yolo11n-pose.pt"
url = "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.pt"
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists():
    print(f"Already exists: {target}")
else:
    temporary = target.with_suffix(".part")
    try:
        with urlopen(url, timeout=60) as response, temporary.open("wb") as handle:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 30 * 1024 * 1024:
                    raise RuntimeError("Unexpected model download size (over 30 MB)")
                handle.write(chunk)
        temporary.replace(target)
        print(f"Downloaded {target.name}: {total:,} bytes")
    finally:
        temporary.unlink(missing_ok=True)
