# Evidence provenance

`football-2026-10-02.json` contains numeric summaries of executed local runs, not video/model assets. Original baseline: `e65bbfd`; independent visual labels frozen before football inference in `d035a83`. Baseline and production after metrics, five controlled input/tracker configurations, timestamps, frame counts, CPU duration/RSS, model/video hashes, ground-truth scopes and coordinate comparisons are separate.

Publisher GT source: UVY by Elton Alencar and Rosiane de Freitas, [Zenodo](https://zenodo.org/records/21303900), [CC BY4.0](https://creativecommons.org/licenses/by/4.0/). Ground-truth counts/identity comparisons were derived by ScoutAI; annotations were originally YOLO-World assisted with manual CVAT correction. Our independent50-frame single-player ROI labels are agent visual estimates awaiting expert review. No original video/large GT files are committed.

Detailed formulas, source frames, reproduction and limits: [FOOTBALL_VALIDATION.md](../../docs/FOOTBALL_VALIDATION.md). Full local outputs remain ignored in `test-artifacts/football/`. Processing timings are device-specific; experiment timing caveats are documented. No physical accuracy, global football accuracy, standard MOT score or CUDA validation is implied.
