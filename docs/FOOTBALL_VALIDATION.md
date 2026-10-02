# Football CV validation — 2 October 2026

This is the historical PR#2 phase, now merged into main as `24a389bad4aa2b777f04eb8fe25c1b895e680b07`. The subsequent independent three-match DEV/HOLDOUT experiment and current panoramic detector policy are documented in [SMALL_PLAYER_EXPERIMENTS.md](SMALL_PLAYER_EXPERIMENTS.md). Its final automatic-policy reruns preserved all three raw/tracked counts below. Original evidence and unsuccessful experiments remain intact.

The validation work is complete; football reliability remains limited. HD input detail recovers useful player observations, while camera motion, distant people, crowd false positives and identity switches remain real failures. Physical distance/speed accuracy is **not validated**. This is a small correlated evaluation, not a production football benchmark.

## Environment and baseline integrity

PR [#1](https://github.com/alinur527/Scout.AI/pull/1) was checked before work: **open, not merged**, head `e65bbfd5d7d587fa3a935d713710563ab8bfcfad`. Clean `revive/scout-ai`, only origin `alinur527/Scout.AI`; new branch `cv/football-validation` starts there. Neither upstream repository was changed. No merge or force push.

Windows 11 Pro 10.0.26200, Intel i7-13650HX, 25,463,480,320 bytes OS-reported physical RAM; Python 3.12, Torch 2.10.0+cpu, TorchVision 0.25.0+cpu, Ultralytics 8.4.26, Supervision 0.27.0.post1, OpenCV 4.12.0.88, NumPy 2.2.6. Node 25.8.0, Vite 7.3.6, Playwright 1.58.0 / headless Chromium.

YOLO11n-pose SHA256 `869e83fcdffdc7371fa4e34cd8e51c838cc729571d1635e5141e3075e9319dc0`; existing local 6,255,593-byte checkpoint. No model or CUDA package was downloaded in this phase. CUDA **NOT TESTED**: installed Torch reports CUDA unavailable, despite an NVIDIA laptop GPU being present.

All regression checks ran **before production edits**, with logs under ignored `test-artifacts/football/baseline/`:

| Check | Before | After |
|---|---|---|
| pytest backend/tests | 16 PASS, 2.33 s | 58 PASS |
| Ruff backend/scripts | PASS | PASS |
| compileall backend/app + scripts | PASS | PASS |
| npm ci / lint / build | PASS / PASS / PASS | PASS / PASS / PASS |
| scripts/test_e2e.py | PASS | PASS |
| scripts/smoke_real.py | PASS, CPU, 24 frames / 4 people | PASS, CPU |
| Football browser flow | Not present | PASS, real mode, 200 football frames |

The Starlette TestClient deprecation warning existed before changes. Supervision deprecation warnings remain visible during real inference. No pre-existing regression failures were found.

## Data and rights

Source: [UVY / Zenodo record 21303900](https://zenodo.org/records/21303900), DOI [10.5281/zenodo.21303900](https://doi.org/10.5281/zenodo.21303900), Elton Alencar and Rosiane de Freitas. Publisher metadata identifies [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/); its description states the underlying YouTube videos were collected under CC BY. Source annotations were produced using YOLO-World with manual review/correction in CVAT. They are distinct from our independent visual subset.

`scripts/download_football_samples.py` fetched selected ZIP members with exact HTTP206/Content-Range checks, a per-invocation 200 MB network cap, 40 MB selected-member cap, safe member whitelist, sizes and CRC checks. The **3.274 GB archive was not downloaded**. Four original MP4s total **33,182,762 bytes**; three optional GT files plus class lists total about 0.98 MB uncompressed. Videos/GT/full outputs stay ignored. SHA256, original member names and decoded metadata are in the local source manifest. V03 was inspected for dataset selection but not run through the model.

| Source | Bytes | Resolution | Decoded FPS | Full duration | Tested source frame interval | Tested duration / frames | Condition |
|---|---:|---|---:|---:|---|---|---|
| soccer_V04 | 1,866,442 | 1280×720 | 29.97003 | 8.041 s | [0,200) | 6.673 s / 200 | Free kick, player overlaps, camera shake/pan; relatively steady opening |
| soccer_V02 | 10,141,212 | 1280×720 | 29.97003 | 36.203 s | [100,350) | 8.342 s / 250 | Wide view through strong zoom, near spectators |
| soccer_V01 | 4,433,566 | 636×360 | 29.97003 | 50.350 s | [600,850) | 8.342 s / 250 | Distant players, severe motion blur/shake |
| soccer_V03 | 16,741,542 | 1280×720 | 29.888 | 83.378 s | NOT TESTED | N/A | Shake/occlusion; inspected only |

The tested windows were selected from **raw footage before inference**, then encoded as MJPG at original resolution and nominal FPS by `prepare_football_clip.py`. Derived AVI reports 29.97 FPS. No synthetic/interpolated frames. Source-to-clip hashes and frame offsets are retained. V01's publisher `video_info.txt` incorrectly describes athletics; decoded video and hashes are authoritative. All clips depict the same Rio2016 event: three conditions, **not three independent matches**. No completely fixed full-pitch football camera sample was found. TeamTrack website previews were rejected because they already contain coloured boxes/IDs.

Source MP4 SHA256:

* V01: `2b68bc1a13a24c84cf0525f7258ce99f93448f2b688fafb97756c99aa83891f0`
* V02: `9b0e9244f4d3750c3d2c16e2df63554e9110b6dca2988b0bea8804ec3a9942d6`
* V04: `96e09e72789c60ad88bd89be3f942e325e026cb5eef05d5e55ddd14687b48d84`

## Measurement definitions

Detection and tracking are measured separately. A callback records raw person boxes after NMS **before** tracker filtering. Tracked output records only boxes with IDs, matching the application pipeline. The baseline uses the original `classes=[0], conf=.3, iou=.5, imgsz=640`, all decoded frames, original local BoT-SORT configuration. The after run uses the **actual production VideoProcessor**, including decoder timestamps and the camera veto.

Matching: descending-IoU greedy one-to-one assignment, **IoU ≥0.5**. This small explicit implementation is unit tested; it is **not MOTMetrics, MOTA, HOTA or IDF1**. P=TP/(TP+FP), R=TP/(TP+FN), F1=2PR/(P+R); zero denominator returns 0 by convention. Counts and scope must accompany the ratios.

Publisher evaluation positives are `player` and `goalkeeper`; referees, crew and spectators are not positive football players. Unmatched person detections count as task FP. The model is a COCO **person** detector, so these results evaluate its suitability for football-player selection, not general person detection accuracy. Publisher annotation completeness/precision was not independently re-audited.

ID switch: a labelled identity changes matched prediction ID, including across a gap. Fragmentation: matched → unmatched while labelled visible → matched. Counts are evaluated on every tested publisher frame, or only on the 50 sampled independent frames for the visual subset. A labelled identity's coverage is matched labelled frames / visible labelled frames.

Technical indicators are **not accuracy**: any-track frame coverage=frames with ≥1 tracked person / decoded frames; track length=count of observations; short track=<10 observations; same-ID reacquisition=nonconsecutive observations of an unchanged output ID; proxy fragmentation=output IDs per 100 decoded frames. No ground-truth identity interpretation is implied by these proxies.

## Baseline and actual production after

| Clip | Frames | Any-track frame coverage before→after | IDs before→after | Median track observations before→after | Longest before→after | Short tracks before→after | Same-ID gaps before→after |
|---|---:|---|---|---|---|---|---|
| V04 steady | 200 | 0% → 100% | 0 → 18 | 0 → 38.5 | 0 → 200 | 0 → 6 | 0 → 69 |
| V02 zoom | 250 | 0% → 42.8% | 0 → 25 | 0 → 21 | 0 → 43 | 0 → 6 | 0 → 33 |
| V01 blur | 250 | 2.4% → 2.4% | 2 → 2 | 3 → 3 | 5 → 5 | 2 → 2 | 1 → 1 |

More output IDs alone do not demonstrate better tracking. The improvement is recovery of **matched labelled player observations**, while the newly measurable identity errors remain failures.

Raw detection against publisher GT:

| Clip | Before TP/FP/FN | Before P/R/F1 | After TP/FP/FN | After P/R/F1 |
|---|---|---|---|---|
| V04 | 0/0/2867 | 0/0/0 | 1217/264/1650 | .8217/.4245/.5598 |
| V02 | 0/0/440 | 0/0/0 | 53/571/387 | .0849/.1205/.0996 |
| V01 | 0/21/500 | 0/0/0 | 0/21/500 | 0/0/0 |

Tracked boxes against the same GT:

| Clip | Before TP/FP/FN | After TP/FP/FN | After P/R/F1 | After ID switches | After fragmentation |
|---|---|---|---|---:|---:|
| V04 | 0/0/2867 | 1202/265/1665 | .8194/.4193/.5547 | 4 | 69 |
| V02 | 0/0/440 | 42/510/398 | .0761/.0955/.0847 | 0 | 13 |
| V01 | 0/6/500 | 0/6/500 | 0/0/0 | N/A | N/A |

Baseline identity continuity is **N/A** on all three clips: no matched GT observations. Zero counted switches when a detector misses all players is not evidence of stable identity. V02's zero switches accompanies only 42 matched observations and must not be generalized. V01 remains unusable despite producing a few spurious tracks.

Exact numeric results/configuration/hashes: [validation/results/football-2026-10-02.json](../validation/results/football-2026-10-02.json). All annotated frames/tracks/CSV/raw detections/full summaries are under ignored `test-artifacts/football/{baseline,experiments,after}/`.

## Independent visual subset

[steady-kicker.json](../validation/annotations/steady-kicker.json): one isolated yellow-shirt kicker, **50 evenly spaced frames** across the 200-frame V04 window, each with an independently chosen exhaustive local ROI, box, identity and coarse feet point. Created by Codex visually reviewing all five raw contact sheets, **before any football model output or publisher GT was opened**, frozen in commit `d035a83`. No interpolation or model-assisted boxes; labels were not adjusted after inference. This is agent visual annotation, **not human expert ground truth**; several-pixel uncertainty and kick-frame ambiguity remain. Expert review is needed before treating it as a benchmark.

| Measure | Original 640 | Production HD 1280 |
|---|---:|---:|
| Raw detection TP/FP/FN | 0/0/50 | 48/2/2 |
| Raw detection P/R/F1 | 0/0/0 | .96/.96/.96 |
| Tracked TP/FP/FN | 0/0/50 | 48/2/2 |
| Tracked P/R/F1 | 0/0/0 | .96/.96/.96 |
| ID switches / fragmentation | N/A | 1 / 1 |
| Matched identity coverage | 0% | 96% |

These are agreements with a **single-player ROI subset**, not 96% football accuracy. The kicker changes ID **4 →23** at sampled frame **162**, following unmatched/occluded kick frames; this failure remains. The broader publisher V04 recall (.4193 tracked) is much lower.

## Controlled tracker experiments and rejected changes

Same model, same complete windows, input 1280, NMS .5. Each experiment starts a fresh model/tracker; no cross-clip identity state. Configs under `validation/trackers/` are offline experiments, not runtime defaults.

| Tracker configuration | V04 tracked F1 / switches / fragments / short | V02 tracked F1 / switches / fragments / short | V01 matched TP / short |
|---|---|---|---|
| Original BoT-SORT, detector .3 | .5547 / 4 / 69 / 6 | .0847 / 0 / 13 / 6 | 0 / 3 |
| Original BoT-SORT, detector .1 | .5547 / 4 / 69 / 6 | .0847 / 0 / 13 / 6 | 0 / 3 |
| ByteTrack, matched .3/.1/.3 thresholds, detector .1 | .5490 / 7 / 58 / 11 | .0568 / 2 / 4 / 15 | 0 / 1 |
| BoT-SORT high/new .2, detector .1 | .6101 / 5 / 38 / 5 | .1349 / 0 / 6 / 3 | 0 / 6 |
| BoT-SORT high .2 / new .3, detector .1 | .6085 / 5 / 38 / 4 | .1341 / 0 / 6 / 4 | 0 / 3 |

ByteTrack reduced CPU cost (about 9.3–10 FPS in these experiments) but worsened identity switches and short tracks on both useful clips. Lowering only the detector threshold improved **raw** detection recall but left tracked outputs unchanged; it did not fix continuity. Lowering high/new association thresholds improved F1/fragmentation in two conditions but added an ID switch on V04; low-res performance remained useless. **None replaced the original tracker defaults.** No ReID/stitching was added: missing/distant detections and task false positives dominate, and available independent identity labels are too narrow to validate stitching reliably. No larger model was downloaded.

## Position stability experiments

Replay of identical 1280 pose outputs, matched to 48 independent labelled feet observations. MAE is an image-space, coarse visual-label comparison; not physical-position accuracy. Left/right policies use bbox fallback when that ankle is missing.

| Position policy | Feet MAE px | Median second difference px, 1325 contiguous output triples |
|---|---:|---:|
| Left ankle | 6.266 | 2.154 |
| Right ankle | 5.934 | 2.168 |
| Valid ankle mean + bbox fallback (retained) | 4.236 | 1.931 |
| Bbox bottom centre | 10.623 | 1.620 |
| Confidence-weighted ankle mean | 4.227 | 1.930 |
| Weighted mean with cached relative bbox offset fallback (.5 s) | 4.227 | 1.930 |
| Weighted mean + EMA tau .08 s | 6.125 | .563 |

EMA lowers an acceleration proxy but worsens feet agreement by about 45%; rejected. Confidence weighting's .010 px difference is below annotation uncertainty, and cached fallback had no measurable gain on this subset; neither justified replacing the mean. The original ground-point policy was extracted into a dependency-light helper and covered with missing/partial/malformed ankle tests. **No claim of improved physical coordinate accuracy.**

## Concrete failures and changes

| Evidence | Cause hypothesis | Change / outcome | Validation |
|---|---|---|---|
| V04/V02 at 640: zero detections; identical raw V04 first frame has 17 boxes at 1280 with probe conf .05 | Resizing discards small human/pose detail | Production uses native largest dimension rounded to 32, clipped to 640–1280; low-res stays 640 | Actual production rerun on all three clips; matched observations recovered on HD, low-res outputs unchanged |
| V02 frame100 detects foreground spectators while pitch players are missed | COCO person task + distance/zoom domain | Explicit gallery warning; no invented player-class confidence; remains unresolved | Publisher TP53/FP571/FN387 raw, representative image |
| V04 kicker ID4→23 after kick/overlap | Occlusion/pose/association; no appearance identity cue | Tracker alternatives rejected; remains unresolved | Frozen ROI identity comparison + frame162 |
| V01 severe blur: no matched football players | Insufficient source detail; upscaling cannot recreate it | No expensive default upscaling for 360p | Original and production identical detections/tracks; 1280 experiments also TP0 |
| Baseline NaN timestamp produces NaN distance/speeds | Time value never validated | Reject nonfinite/invalid samples and start a fresh segment | Deterministic regression tests |
| Baseline distance excludes a gap but SVG still joins its endpoints | One flattened path | Store/render separate movement segments | Math tests and report contract tests; browser Path layer |
| Baseline accepts an oversized field dimension when called directly | Safety existed only partly in API schema | Finite bounded dimensions, unique/ordered convex points, area/bounds, invertibility/conditioning, finite bounded transformed points | Deterministic positive/negative homography tests |
| A single first-frame homography on moving football footage would produce false movement | Homography assumes one camera pose | Background motion veto + explicit fixed-camera confirmation + reliable decoder timestamps; otherwise physical metrics null | All real clips classified moving; real browser deliberately supplied geometry fixture and false confirmation, backend still blocked metrics |

Representative evidence, resized and annotated by ScoutAI: [before](football/steady-before.jpg), [after](football/steady-after.jpg), [ID switch](football/kicker-switch.jpg), [spectators](football/spectator-false-positives.jpg), [blur](football/blur-missed-players.jpg), [mobile real report](football/report-mobile.png). Images derive from UVY / Alencar and de Freitas, [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), with resizing and overlays indicated here; no endorsement implied. Original full-resolution evidence remains ignored locally.

## Movement math and camera safety

VideoProcessor now uses monotonic OpenCV decoder timestamps (`POS_MSEC`) before subsampling. Unavailable/non-monotonic PTS falls back to nominal FPS for image visualization **and disables physical metrics**. No inference frames are skipped. Persistence keeps at most 10 observations/s per ID, retaining timestamp units. Synthetic variable-interval decoding tests cover both usable PTS and fallback; no real variable-frame-rate football accuracy claim.

Distance sums smoothed displacement only within continuous segments. Gaps **>.5 s**, invalid observations and raw speeds **>45 km/h** break calibrated segments; no speed/distance/sprint is added across the break. EMA tau=.15 s is time-based. Tests validate an exact unsmoothed irregular-time path (4 m, 7.2 km/h) and the closed-form EMA reference independently; smoothing has lag and is not asserted to reproduce true short-run physical distance.

Sprints remain events: speed **>21 km/h** for at least **.6 s** counts once until speed returns below the threshold or continuity breaks. Sustained sprint, two separated events, a shorter burst, missing observations, jump and short-track cases are deterministic tests. No per-frame sprint counter or unnecessary new sprint algorithm.

Camera veto: masked background sparse optical flow + RANSAC partial affine at about 5 Hz / max640 working width; moving if accumulated centre displacement >3 working pixels, scale change >2%, or rotation >1°. To return `no_motion_detected` requires ≥8 valid pairs and ≥60% valid sampled pairs. Otherwise `unknown`. It does **not** stabilize/compensate field coordinates. All three tested clips were moving: V04 about49.8px, V02 about180px/253% scale change, V01 about47.3px with only5/41 valid pairs. Fixed, translation, zoom and textureless synthetic cases are tested. False positives/negatives of this veto are **not benchmarked**; no-motion is not proof. Explicit user confirmation, valid calibration and reliable PTS are also required.

`physical_accuracy=not_validated` always. Physical distances/speeds/sprints are **unavailable for all real clips here**. Known field geometry, surveyed trajectories or timing/radar references are still needed to validate physical accuracy. Small ID-switch jumps below the rejection threshold can remain plausible movement; a track is not a verified identity.

## CPU performance

| Clip | Before seconds / FPS | Actual production seconds / FPS | Processing/video ratio after | Observed RSS before→after MiB |
|---|---|---|---:|---|
| V04 | 10.971 / 18.229 | 23.559 / 8.489 | 3.530 | 373.76 →493.84 |
| V02 | 13.481 / 18.545 | 30.136 / 8.296 | 3.613 | 374.82 →494.20 |
| V01 | 11.300 / 22.125 | 12.567 / 19.893 | 1.507 | 376.89 →418.04 |

Final production benchmark ran the clips **sequentially without concurrent inference**, and includes inference/tracking/camera/annotated-frame output; excludes model import/load, upload, DB writes and gallery JPEG creation. Baseline used the same save intervals; V04 additionally saved all50 annotated label frames. RSS is psutil memory sampled after every frame, including model/runtime; not a continuous hardware peak. One earlier 1280 blur experiment overlapped the beginning of a low-confidence run, so experiment timings are exploratory; only the separate final sequential production run is used for before/after performance. Quality counts are deterministic for the tested configs. HD costs more CPU and memory. No realtime or production-throughput claim. CUDA **NOT TESTED**.

## Real application and regression evidence

`webapp-testing`: helper read and --help checked; reviewed API factory/package scripts; actual helper launch with absolute Python/Node executables, then portable project wrapper with process-tree cleanup. Headless Chromium reconnaissance captured DOM before actions. One real-flow test-selector failure (`Player1` also matching `Player10`) was fixed with an exact nested label. The expanded demo test initially expected a real-only annotated preview; that check is now scoped to real mode. Both were test harness errors; production outputs/labels were not changed to satisfy them.

Successful real flow: register/login player → profile save/refresh → football AVI upload202/queued → actual REAL worker/YOLO → persisted gallery after refresh → selected longest track → manual geometry fixture → report completed → path/heatmap → refresh → scout register/login → directory/search/detail/report → role guard/404 → expected invalid JWT401. Selected ID1 had **200/200 observed frames, 67 stored samples**, CPU, a visible annotated preview and finite normalized image path. Test geometry was deliberately a whole-frame rectangle, **not measured pitch calibration**, to verify server motion rejection. `demo=false`, camera moving, calibration provided but rejected for physical metrics, all three metrics null. Happy path had zero page/console errors, zero HTTP≥400, no broken images, worker stayed alive, no stuck job. Screenshots/assertions at1440/768/390px; desktop/mobile and difficult frames visually reviewed.

Final local commands: `python -m pytest backend/tests -q` (58), `python -m ruff check backend scripts`, `python -m compileall -q backend/app scripts`, frontend `npm ci`, `npm run lint`, `npm run build`, `python scripts/test_e2e.py`, `python scripts/test_e2e.py --video test-artifacts/football/clips/steady/clip.avi`, `python scripts/smoke_real.py`. See [VALIDATION.md](VALIDATION.md) for final remote CI evidence. Ordinary CI installs no Torch/Ultralytics/weights: synthetic math, geometry, camera patterns and mocked detections run GPU-free.

## Reproduce

Requires existing CV dependencies/weights; source downloads and inference are opt-in. Freeze any new labels before inspecting predictions. From repository root, use `.venv/Scripts/python.exe` on Windows (or `.venv/bin/python` elsewhere):

```powershell
.\.venv\Scripts\python.exe scripts/download_football_samples.py --include-annotations
.\.venv\Scripts\python.exe scripts/prepare_football_clip.py test-artifacts/football/source/soccer_V04.mp4 --output test-artifacts/football/clips/steady --frames 200 --roi 60 270 480 660
.\.venv\Scripts\python.exe scripts/prepare_football_clip.py test-artifacts/football/source/soccer_V02.mp4 --output test-artifacts/football/clips/zoom --start 100 --frames 250 --samples 10
.\.venv\Scripts\python.exe scripts/prepare_football_clip.py test-artifacts/football/source/soccer_V01.mp4 --output test-artifacts/football/clips/blur --start 600 --frames 250 --samples 10
# Original baseline parameters are still the validation tool's default.
.\.venv\Scripts\python.exe scripts/validate_football_cv.py test-artifacts/football/clips/steady/clip.avi --annotations validation/annotations/steady-kicker.json --output test-artifacts/football/repro-baseline
# Actual current application processor, timestamps and camera veto:
.\.venv\Scripts\python.exe scripts/validate_football_cv.py test-artifacts/football/clips/steady/clip.avi --production --annotations validation/annotations/steady-kicker.json --output test-artifacts/football/repro-after
.\.venv\Scripts\python.exe scripts/score_uvy.py test-artifacts/football/repro-after --gt test-artifacts/football/source/soccer_V04_gt.txt --labels test-artifacts/football/source/soccer_V04_labels.txt
.\.venv\Scripts\python.exe scripts/compare_ground_positions.py test-artifacts/football/repro-after/tracks.json --annotations validation/annotations/steady-kicker.json --output test-artifacts/football/repro-after/positions.json
.\.venv\Scripts\python.exe scripts/test_e2e.py --video test-artifacts/football/clips/steady/clip.avi
```

For experiment runs use `--imgsz 1280`, `--conf .1` and `--tracker validation/trackers/<config>.yaml` **without** `--production`. Publisher scoring uses source offsets0/100/600. Local outputs preserve summary, failure list, raw detections, tracks JSON/CSV and annotated frames. Exact encoded hashes can depend on OpenCV/platform; the tool refuses labels for a different video hash, rather than silently applying them. Review source frame identity and re-encode/review provenance if reproducing elsewhere.

## Next step and limits

Acquire several independent fixed-camera and panning full-match windows with expert-checked all-player boxes/IDs and field reference points; retain a separate holdout before tuning. First improve small-player detection/field masking and resolve spectator/referee selection, then evaluate tracking/ID stitching against that holdout. Validate physical movement separately with known pitch geometry and measured reference trajectories. The current dataset does not justify global accuracy, physical accuracy, reliable camera classification, cross-video identity or a new model default.

Skills: `grill-me/grilling` checked experimental prerequisites and delegated dataset facts, with decisions already supplied by the user's brief; `webapp-testing` governed the real browser flow; `frontend-design` kept existing tokens/type/layout and used quiet report notes/warnings rather than a redesign; `handoff` writes a redacted OS-temp handoff referring to these artifacts.
