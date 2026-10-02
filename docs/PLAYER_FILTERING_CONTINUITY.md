# Player filtering and continuity — experimental protocol

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

TeamTrack is under consideration from its [official project](https://atomscott.github.io/TeamTrack/) and [publisher Kaggle distribution](https://www.kaggle.com/datasets/atomscott/teamtrack). The publisher API currently declares MIT. It contains fisheye/drone soccer views; exact source selection and camera/venue independence will be documented after file-catalogue inspection, before opening frames. SportsMOT was not selected because of its noncommercial/no-redistribution terms; SoccerTrack v1's unusual software-license declaration was not preferred. No weights or source videos are committed.

## DEV error evidence and rejected filters

The baseline error analyzer uses the same one-to-one matches as the scorer. 117093 FP: 187 unknown, 61 possible localization mismatches, 2 duplicate player boxes. 118575: 131 unknown, 101 possible localization mismatches. These low-IoU cases are hypotheses, not manually verified real-player boxes. Spectator/staff/background counts cannot be asserted from this publisher's player-only GT. UVY steady's negative publisher labels confirm 194 referee FP, 39 possible localization mismatches, 31 unknown. Visual examples include an official holding a flag on the near sideline, illustrating why an image-space pitch boundary cannot exclude every official while retaining edge players.

Two independently drawn raw-frame polygons (agent annotation, requires human review) were fixed before screening. Same .005 margin and existing raw boxes: 117093 TP1662/FP250/FN978 -> TP1662/FP249/FN978; 118575 TP832/FP232/FN1808 unchanged. The <1% FP reduction fails the preregistered 10% gate. **Rejected**: no production ROI API, persistence or UI is added. The polygon utility is isolated to the offline experiment and deterministic tests.

One dark-neutral torso heuristic (HSV saturation/value <100 for >=60% pixels in the central torso) removed no FP in either DEV, lost 2 TP in 118575, and was rejected. This does not establish referee classification. Team/GK/official kit ambiguity prevents an automatic kit-role default. No neural role/ReID or face model was downloaded.

## Continuity failure evidence and second bounded hypothesis

Baseline matched-to-unmatched transitions: 117093 75 raw misses/localization vs 4 raw matches lost by tracker; 118575 74 vs 1. This is evidence that detection remains the main fragmentation bottleneck. Switch pairs: in each clip 7 nonoverlapping tracklets and 1 coexisting pair, which must never be stitched. Evidence and frame/GT/ID spans are in [DEV experiments](../validation/results/player-filtering-dev-experiments-2026-10-02.json).

The first strict policy (.98 appearance, .75-height displacement, direction checked above .1-height/s) created 0 links; switches stayed 8/8. Retained failure diagnostics show real DEV transitions can have .914–.960 appearance similarity, and a .251-height/s near-stationary endpoint can reverse its jitter-derived direction. Before opening any TeamTrack frames, a single second hypothesis was tested: appearance >=.90, max displacement1.25 heights, velocity direction tested only above .5-height/s; other gates unchanged. This is a bounded DEV revision, not holdout tuning or a sweep.

Actual application-model/harness replay of this candidate gives switches 8->5 and 8->7, with identical raw/tracked TP/FP/FN, fragmentation72/68 and identity coverage. Full source-tracklet GT audit verifies all 4 links against the same single anonymous GT identity; 0 false merges, 0 indeterminate links. No missing observations or coordinates are generated. Original BoT-SORT stays unchanged. 105 deterministic backend tests and Ruff pass before freeze.

## Candidate freeze and sealed source

[Frozen configuration](../validation/configs/selected-continuity.json) selects only conservative continuity. Its containing Git commit freezes the candidate and code hashes before any TeamTrack frames or GT are opened for inference/analysis. The policy is bypassed for moving/unknown camera or unreliable timestamps; `CV_TRACK_CONTINUITY=none` reproduces original grouping. Endpoint data is bounded to first/last5 samples per original ID. No source spans may overlap and both endpoints must have exactly one eligible link, with sufficient torso observations, scale and motion agreement.

[Official source manifest](../validation/results/teamtrack-source-2026-10-02.json): first lexicographic soccer_side/test sequence `F_20220220_1_1680_1710`, first120 frames selected before inspection; source15,069,985 bytes, GT558,450 bytes, publisher MIT metadata. Successful bounded transfer15,643,861 bytes including metadata; prior interrupted attempt capped18,100,000 bytes, plus small catalogue/research requests, all well below200MB. No frames/GT from the TeamTrack family entered DEV. The paper identifies University of Tsukuba and Z CAM E2-F8 fisheye capture; exact venue independence is not established. File-date tokens are source identifiers and are not verified dates. GT is one-based MOT class1; detailed player/GK/referee roles are not invented. This is distinct from zero-based SoccerTrack v2 scoring.

Sealed evaluation, final regression, performance and final selection decision are pending. DEV improvement alone does not authorize a success claim.
