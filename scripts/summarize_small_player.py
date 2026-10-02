"""Collect measured summaries; never derive claims from a smoke test."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def portable(value):
    if isinstance(value, str):
        return (
            value.replace(str(ROOT), "$REPO")
            .replace(ROOT.as_posix(), "$REPO")
            .replace("\\", "/")
        )
    if isinstance(value, dict):
        return {key: portable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [portable(item) for item in value]
    return value


def main():
    entries = []
    directory = ROOT / "test-artifacts/small-player"
    for name in (
        "baseline",
        "large-pose",
        "person",
        "highres",
        "tiles",
        "pitch",
        "person-pitch",
        "holdout-baseline",
        "holdout-selected",
        "selected-production",
        "normalization",
        "broadcast-regression",
    ):
        for run in sorted((directory / name).glob("*/summary.json")):
            metrics_file = run.parent / "publisher_metrics.json"
            if not metrics_file.exists():
                raise ValueError(f"Unscored run: {run}")
            summary = json.loads(run.read_text())
            metrics = json.loads(metrics_file.read_text())
            # Events/identity coverage are useful audit evidence, not extra headline scores.
            entries.append(
                {
                    "configuration": name,
                    "clip": run.parent.name,
                    "summary": summary,
                    "metrics": metrics,
                }
            )
    output = {
        "schema_version": 1,
        "baseline_main": "24a389bad4aa2b777f04eb8fe25c1b895e680b07",
        "candidate_freeze_commit": "821e4111042593ec5a311997c83850483d156631",
        "holdout_rounds": 1,
        "production_selection": "auto panoramic person; configured base pose for normal aspect ratios; no scene filter or tiling",
        "small_player_definition": "GT area at fixed1280px maximum-side reference <=1024px^2",
        "source_manifest": "validation/results/soccertrack-sources-2026-10-02.json",
        "cuda_status": "NOT TESTED; torch2.10.0+cpu",
        "physical_accuracy": "not_validated",
        "runs": entries,
    }
    target = ROOT / "validation/results/small-player-2026-10-02.json"
    target.write_text(json.dumps(portable(output), indent=2), encoding="utf-8")
    print(f"Collected {len(entries)} scored runs into {target.relative_to(ROOT)}")
    sources = ROOT / "validation/results/soccertrack-sources-2026-10-02.json"
    sources.write_text(
        json.dumps(portable(json.loads(sources.read_text())), indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
