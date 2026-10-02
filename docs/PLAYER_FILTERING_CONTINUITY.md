# Player filtering and continuity — results and experimental protocol

**Status: PARTIAL.** DEV continuity improved, but the independent sealed camera source did not confirm an improvement. ROI and kit filtering failed on DEV. All production settings/inference changes were restored to main; only offline experiments, scorer, deterministic tests and evidence are retained. The detector auto policy and original BoT-SORT remain the production defaults.

## Integration and baseline

PR #3 was open at `54f5c25428fc94af9945841a4a2d528bbe4e1d24`, base main, mergeable, with all three CI jobs successful in run 37039995800. Local 77 tests, Ruff and reachable-history artifact/credential scan passed. Authorized merge commit and updated main: `e423ae6dd4d8d046c58c17304fa0094100bd3151`. This branch starts at that commit.

Before changing CV code, the existing actual-VideoProcessor harness reran all three SoccerTrack and all three UVY windows. Full baseline, hashes, timing, RSS, ID coverage and events: [numeric baseline](../validation/results/player-filtering-baseline-2026-10-02.json).

| Window | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| SoccerTrack DEV 117093 | 1662 | 250 | 978 | .8692 | .6295 | .7302 |
| SoccerTrack DEV 118575 | 832 | 232 | 1808 | .7820 | .3152 | .4492 |
| SoccerTrack previously opened 118576 | 1003 | 316 | 1637 | .7604 | .3799 | .5067 |
| UVY steady | 1217 | 264 | 1650 | .8217 | .4245 | .5598 |
| UVY zoom | 53 | 571 | 387 | .0849 | .1205 | .0996 |
| UVY blur | 0 | 21 | 500 | 0 | 0 | 0 |

These are player-box agreement at IoU >= .5, not general football accuracy. 118576 and old UVY are regressions, never new sealed data.

## Preregistered sequence

1. Inspect baseline FP and switch/fragment events on DEV only. Publisher negative roles may be used where provided. Unmatched boxes without evidence remain unknown. Independently mark visible playable area from raw frames, before candidate results. Manual annotations require human review.
2. Reuse `validate_football_cv.py`, `evaluate_labels`, and existing scorers. No second benchmark framework. Test one optional polygon filter with the unchanged model/confidence/input-size/BoT-SORT. The ground point is confidence-qualified ankles or bbox bottom centre, never box centre. Include a small margin of .005 times maximum image dimension. No role-classification default without measured evidence.
3. Investigate one conservative within-video stitching policy if continuity remains a bottleneck: short nonoverlapping gaps, motion/scale/torso appearance agreement and unambiguous one-to-one matches. Never alter trajectory coordinates, synthesize missing samples or connect physical segments across existing gap gates. Reject if it adds a false identity merge or fails to improve DEV. No biometric or cross-match features.
4. Acquire a bounded official independent source, with publisher-declared license, source identifier/hash and first 120 frames chosen without candidate inspection. Entire new source family stays sealed until candidate/config/code freeze is committed. Raw-frame ROI annotation after freeze is permitted only as the required user input, before either baseline or candidate output is viewed; parameters cannot change. No holdout label tuning.
5. Freeze the selected candidate in Git. Then run only baseline and that candidate on the new sealed source. Reject production changes if direction fails, retain numeric evidence. A new experimental round needs another untouched source.
6. Verify old small-player/broadcast counts, movement gates, persistence, API guards, CPU costs, full browser/player/scout flow and responsive layout; commit/push/open a PR and leave it unmerged.

## Selection gates

An ROI candidate must reduce DEV FP by at least 10%, retain at least 98% of baseline raw TP in each DEV window, and avoid decreasing F1. The sealed source must contain measurable matched players, lower FP and retain at least 98% TP without lower F1. These gates are deliberately specified before ROI candidate results. No ROI keeps exact old behavior; ROI is optional and cannot authorize metric calibration. Moving-camera and timestamp/geometry safeguards remain unchanged.

Stitching requires fewer switches or fragments on DEV, no newly measured false merge, and no degradation on the sealed test. An experiment producing no merges is not an improvement. Role labels and stable personal identity will not be inferred from similar kits.

## Data research

TeamTrack was selected from its [official project](https://atomscott.github.io/TeamTrack/) and [publisher Kaggle distribution](https://www.kaggle.com/datasets/atomscott/teamtrack). The [publisher metadata](https://www.kaggle.com/api/v1/datasets/metadata/atomscott/teamtrack) declares MIT for the dataset; this is not inferred from the repository's code license. The [paper](https://arxiv.org/html/2404.13868v1) documents University of Tsukuba soccer, Z CAM E2-F8 fisheye capture and Labelbox annotations with interpolation/manual inspection. The selected soccer_side source uses that fisheye system; [SoccerTrack v2](https://atomscott.github.io/SoccerTrack-v2/) documents BePro/three-camera panoramic systems. Camera system and geometry differ, but a different venue is **not established**. SportsMOT was not selected because of its noncommercial/no-redistribution terms; SoccerTrack v1's unusual software-license declaration was not preferred. No weights or source videos are committed.

## DEV error evidence and rejected filters

The baseline error analyzer uses the same one-to-one matches as the scorer. 117093 FP: 187 unknown, 61 possible localization mismatches, 2 duplicate player boxes. 118575: 131 unknown, 101 possible localization mismatches. These low-IoU cases are hypotheses, not manually verified real-player boxes. Spectator/staff/background counts cannot be asserted from this publisher's player-only GT. UVY steady's negative publisher labels confirm 194 referee FP, 39 possible localization mismatches, 31 unknown. Visual examples include an official holding a flag on the near sideline, illustrating why an image-space pitch boundary cannot exclude every official while retaining edge players.

Two independently drawn raw-frame polygons (agent annotation, requires human review) were fixed before screening. Same .005 margin and existing raw boxes: 117093 TP1662/FP250/FN978 -> TP1662/FP249/FN978; 118575 TP832/FP232/FN1808 unchanged. The <1% FP reduction fails the preregistered 10% gate. **Rejected**: no production ROI API, persistence or UI is added. The polygon utility is isolated to the offline experiment and deterministic tests.

One dark-neutral torso heuristic (HSV saturation/value <100 for >=60% pixels in the central torso) removed no FP in either DEV, lost 2 TP in 118575, and was rejected. This does not establish referee classification. Team/GK/official kit ambiguity prevents an automatic kit-role default. No neural role/ReID or face model was downloaded.

## Continuity failure evidence and second bounded hypothesis

Baseline matched-to-unmatched transitions: 117093 75 raw misses/localization vs 4 raw matches lost by tracker; 118575 74 vs 1. This is evidence that detection remains the main fragmentation bottleneck. Switch pairs: in each clip 7 nonoverlapping tracklets and 1 coexisting pair, which must never be stitched. Evidence and frame/GT/ID spans are in [DEV experiments](../validation/results/player-filtering-dev-experiments-2026-10-02.json).

The first strict policy (.98 appearance, .75-height displacement, direction checked above .1-height/s) created 0 links; switches stayed 8/8. Retained failure diagnostics show real DEV transitions can have .914–.960 appearance similarity, and a .251-height/s near-stationary endpoint can reverse its jitter-derived direction. Before opening any TeamTrack frames, a single second hypothesis was tested: appearance >=.90, max displacement1.25 heights, velocity direction tested only above .5-height/s; other gates unchanged. This is a bounded DEV revision, not holdout tuning or a sweep.

Actual application-model/harness replay of this candidate gives switches 8->5 and 8->7, with identical raw/tracked TP/FP/FN, fragmentation72/68 and identity coverage. Full source-tracklet GT audit verifies all 4 links against the same single anonymous GT identity; 0 false merges, 0 indeterminate links. No missing observations or coordinates are generated. Original BoT-SORT stays unchanged. 105 deterministic backend tests and Ruff passed before freeze; the final scorer regression brings the total to106.

## Candidate freeze and sealed source

[Frozen configuration](../validation/configs/selected-continuity.json), committed in `6dbf40104b6cb7453a10fb2a975e70b3526c3126`, records the historical conservative candidate and code hashes before any TeamTrack frames or GT were opened for inference/analysis. The policy bypasses moving/unknown cameras or unreliable timestamps. Endpoint data is bounded to first/last5 samples per original ID. No source spans may overlap and both endpoints must have exactly one eligible link, with sufficient torso observations, scale and motion agreement. The frozen core SHA256 remains `da37df21fdc7385c9bd3a8ff771f72886dd550cbb90d8eafac757ac8a60937cc`. Historical production-integration hashes in the freeze intentionally differ from final restored production files. There is no new application environment option; `--continuity conservative` is an explicit **offline harness diagnostic** only. Default `--continuity none` preserves original IDs.

[Official source manifest](../validation/results/teamtrack-source-2026-10-02.json): first lexicographic soccer_side/test sequence `F_20220220_1_1680_1710`, first120 frames selected before inspection; source15,069,985 bytes, GT558,450 bytes, publisher MIT metadata. Successful bounded transfer15,643,861 bytes including metadata; prior interrupted attempt capped18,100,000 bytes, plus small catalogue/research requests, all well below200MB. No frames/GT from the TeamTrack family entered DEV. File-date tokens are source identifiers and are not verified dates. Native source is6500x1000,25FPS,750frames/30s; window0..119 is4.8s, re-encoded to native-size MJPG without frame interpolation. Video SHA256 `8a3d50042b958863c996396107041c624ff74e03487b57104fa335e5de12edd5`, GT `6afeb37050a62d612e5eddcae363dbe11e42bcc6c3f161cef16bfd1b98108110`, window `5374d382f6f1cee23afd6e3b9f469322cba41552755d8adf70f459663e264d40`.

The released MOT rows use one-based frame numbers, zero-based persistent IDs, confidence1 and `-1` placeholders for class/visibility/world coordinates. All23 publisher targets/frame are retained; detailed player/GK/referee roles are unavailable. The first scorer incorrectly required class1, producing zero GT: that result is **invalid and discarded**. Only the parser was corrected and regression-tested, then saved baseline/candidate outputs were rescored. No inference rerun, candidate/parameter change or further tuning occurred. The source manifest's `opened_for_cv=false` records its pre-freeze state; the holdout evidence records the subsequent evaluation.

## DEV candidate and sealed evaluation

| Window / metric | Original | Frozen candidate |
|---|---:|---:|
| DEV117093 raw TP/FP/FN; P/R/F1 |1662/250/978; .8692/.6295/.7302|1662/250/978; .8692/.6295/.7302|
| DEV117093 tracked TP/FP/FN; P/R/F1 |1591/224/1049; .8766/.6027/.7143|1591/224/1049; .8766/.6027/.7143|
| DEV117093 IDs / switches / fragments |32 /8 /72|29 /5 /72|
| DEV118575 raw TP/FP/FN; P/R/F1 |832/232/1808; .7820/.3152/.4492|832/232/1808; .7820/.3152/.4492|
| DEV118575 tracked TP/FP/FN; P/R/F1 |804/208/1836; .7945/.3045/.4403|804/208/1836; .7945/.3045/.4403|
| DEV118575 IDs / switches / fragments |22 /8 /68|21 /7 /68|
| TeamTrack sealed raw TP/FP/FN; P/R/F1 |213/243/2547; .4671/.0772/.1325|213/243/2547; .4671/.0772/.1325|
| TeamTrack sealed tracked TP/FP/FN; P/R/F1 |194/234/2566; .4533/.0703/.1217|194/234/2566; .4533/.0703/.1217|
| TeamTrack IDs / median / short<10 |10 /21 /4|10 /21 /4|
| TeamTrack switches / fragments / links |2 /20 /0|2 /20 /0|

Sealed camera/timestamp gates passed, but there were no eligible links and no improvement. Zero false merges with zero links is not validation of identity continuity. **Rejected for production**, even though DEV switches fell25% overall (16->12). Both full-span DEV link audits and the empty holdout audit are retained. Saved candidate evidence: [DEV replay](../validation/results/player-filtering-candidate-dev-2026-10-02.json), [sealed evaluation](../validation/results/player-filtering-holdout-2026-10-02.json), [final decision](../validation/configs/continuity-decision.json).

## Final regression and CPU cost

Final production replay exactly matches baseline raw **and tracked** TP/FP/FN/P/R/F1, identity coverage, ID counts, switches/fragments and small-player bins on all six clips. Small-player recall remains62.95%/31.52%/37.99% for117093/118575/118576; old UVY raw counts remain1217/264/1650,53/571/387,0/21/500. Detailed per-identity coverage/events and executed browser results: [final regression evidence](../validation/results/player-filtering-regression-2026-10-02.json). At least one match for19/22,13/22,14/22 GT identities in the three SoccerTrack windows does not imply reliable full-match identity.

| Window | Baseline seconds / FPS / RSS MiB | Final seconds / FPS / RSS MiB |
|---|---|---|
|117093|14.613 /8.212 /471.29|16.977 /7.068 /472.73|
|118575|14.142 /8.486 /456.46|15.617 /7.684 /458.01|
|118576|14.257 /8.417 /458.35|15.260 /7.864 /458.84|
|UVY steady|24.781 /8.071 /499.94|23.390 /8.551 /500.15|
|UVY zoom|29.990 /8.336 /499.45|30.454 /8.209 /500.23|
|UVY blur|12.257 /20.396 /424.11|15.715 /15.908 /426.61|
|TeamTrack baseline vs frozen candidate|21.058 /5.698 /452.88|19.376 /6.193 /452.08|

Sequential CPU execution on i7-13650HX, Torch2.10.0+cpu, Ultralytics8.4.26, OpenCV4.12, Supervision.27. Includes decoding/tracking/camera/output, excludes imports/model load and application DB/gallery writes. Final harness additionally saves native tracker JSON for auditing, so timing variation is not a production speed change or optimization result. RSS is sampled after frames, not a continuous peak. CUDA unavailable and **NOT TESTED**. No new model/CUDA package downloaded.

## Application, safety and tests

106 backend tests, Ruff and compileall PASS. Frontend npm ci/lint/build/audit PASS,0 vulnerabilities. Demo, real panoramic117093 and real UVY steady full browser flows PASS; real CPU smoke PASS. Player register/login/profile/save/refresh, upload202/queued/processing/gallery/selection, saved report/path/heatmap/preview/refresh, scout register/login/search/detail/saved report, guards/404 all exercised with actual API/frontend/worker and temporary SQLite. Happy-path console/page/HTTP/image errors0; the intentional invalid-JWT check produces two expected profile401 responses, recorded separately. Overflow checks1440/768/390 passed; preserved panoramic390 and broadcast1440 screenshots inspected. Shared real-E2E artifacts overwrite earlier runs; the portable record discloses this limitation.

Production config/inference are byte-identical to merged main. Timestamp validation/decoder timing, invalid coordinates, gaps>0.5s, calibrated jumps>45km/h, camera-motion veto, fixed-camera confirmation, calibration/homography sanity and sprint events>21km/h for>=0.6s remain intact. Broadcast reports keep physical metrics unavailable even with synthetic calibration because camera motion is detected; panorama without calibration also remains unavailable. Synthetic movement tests are math checks; **physical accuracy NOT VALIDATED**.

## Reproduce and next round

```powershell
.\.venv\Scripts\python.exe scripts/download_teamtrack_holdout.py
.\.venv\Scripts\python.exe scripts/prepare_football_clip.py test-artifacts/player-filtering/sealed-teamtrack/source.mp4 --start 0 --frames 120 --samples 20 --output test-artifacts/player-filtering/sealed-teamtrack/window
# Use the recorded native-size120-frame window; no holdout retuning:
.\.venv\Scripts\python.exe scripts/validate_football_cv.py test-artifacts/player-filtering/sealed-teamtrack/window/clip.avi --production --continuity none --output test-artifacts/player-filtering/repro-none
.\.venv\Scripts\python.exe scripts/score_teamtrack.py test-artifacts/player-filtering/repro-none --gt test-artifacts/player-filtering/sealed-teamtrack/gt.txt
.\.venv\Scripts\python.exe scripts/validate_football_cv.py test-artifacts/player-filtering/sealed-teamtrack/window/clip.avi --production --continuity conservative --output test-artifacts/player-filtering/repro-candidate
.\.venv\Scripts\python.exe scripts/score_teamtrack.py test-artifacts/player-filtering/repro-candidate --gt test-artifacts/player-filtering/sealed-teamtrack/gt.txt
```

Future tuning needs a **new untouched source**; TeamTrack here and118576/UVY are now opened regressions. Prioritize expert-reviewed detection/localization and labelled on-/off-pitch roles across multiple camera domains: DEV raw misses dominate fragmentation and TeamTrack recall is7.72%. Similar-kit ambiguity, single-homography fisheye/panorama limitations, short windows and missing physical references remain unresolved. No broad football accuracy or stable identity claim follows from these experiments.

Skills considered: grill-me/grilling were read; the requested user interview was superseded by explicit autonomous decisions. Webapp-testing guided existing Playwright/server/console/layout checks; frontend-design was considered but no UI was changed after ROI rejection. Handoff is saved in OS temp, references this report and Git/PR evidence, and contains no credentials.
