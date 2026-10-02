"""Download one preregistered official MIT TeamTrack source without opening frames.

No CV model, decoded preview or GT metrics. Existing BoundedHTTP enforces a
200 MB request budget; this source and GT total less than 20 MB.
"""

import hashlib
import io
import json
from pathlib import Path
from urllib.parse import quote
import zipfile

from download_football_samples import BoundedHTTP

ROOT = Path(__file__).resolve().parents[1]
SEQUENCE = "F_20220220_1_1680_1710"
PREFIX = f"teamtrack-mot/teamtrack-mot/soccer_side/test/{SEQUENCE}"
API = "https://www.kaggle.com/api/v1/datasets"


def main():
    output = ROOT / "test-artifacts/player-filtering/sealed-teamtrack"
    output.mkdir(parents=True, exist_ok=True)
    http = BoundedHTTP()
    metadata_bytes = http.read(f"{API}/metadata/atomscott/teamtrack", 100_000)
    metadata = json.loads(metadata_bytes)["info"]
    if [item["name"] for item in metadata["licenses"]] != ["MIT"]:
        raise ValueError("Publisher license changed; review source before download")
    sources = []
    for member, filename, limit in [
        ("img1.mp4", "source.mp4", 17_000_000),
        ("gt/gt.txt", "gt.txt", 1_000_000),
        ("seqinfo.ini", "seqinfo.ini", 100_000),
    ]:
        name = f"{PREFIX}/{member}"
        url = f"{API}/download/atomscott/teamtrack?fileName={quote(name, safe='')}"
        target = output / filename
        downloaded = http.read(url, limit)
        if downloaded[:2] == b"PK":
            with zipfile.ZipFile(io.BytesIO(downloaded)) as archive:
                files = [item for item in archive.infolist() if not item.is_dir()]
                if len(files) != 1 or files[0].file_size > limit:
                    raise ValueError("Unexpected or oversized single-file response")
                data = archive.read(files[0])  # CRC checked; no archive paths extracted.
        else:
            data = downloaded
        if len(data) > limit:
            raise ValueError("Decoded source exceeds its bound")
        if target.exists() and target.read_bytes() != data:
            raise ValueError("Refusing to replace changed sealed source bytes")
        target.write_bytes(data)
        sources.append({
            "member": name, "url": url, "file": filename,
            "download_bytes": len(downloaded), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    manifest = {
        "dataset": "TeamTrack", "publisher": "Atom Scott et al.",
        "publisher_url": "https://www.kaggle.com/datasets/atomscott/teamtrack",
        "project_url": "https://atomscott.github.io/TeamTrack/",
        "license": "MIT", "license_provenance": f"{API}/metadata/atomscott/teamtrack",
        "license_metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "sequence": SEQUENCE, "split": "SEALED HOLDOUT",
        "selection": "First lexicographic official soccer_side/test video in catalogue; first 120 decoded frames, zero-based 0..119. Selected before viewing frames or GT.",
        "camera": "Publisher soccer_side fisheye Z CAM E2-F8; different camera system from SoccerTrack v2 panoramic footage",
        "venue": "Publisher identifies A University outdoor; exact venue difference not independently established",
        "independence": "No TeamTrack images or annotations used in this task's DEV tuning. Entire source family sealed. File-date tokens are identifiers, not independently verified match dates.",
        "network_bytes_this_run": http.network_bytes,
        "prior_partial_attempt_budget_upper_bound": 18_100_000,
        "files": sources,
        "opened_for_cv": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    evidence = ROOT / "validation/results/teamtrack-source-2026-10-02.json"
    evidence.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
