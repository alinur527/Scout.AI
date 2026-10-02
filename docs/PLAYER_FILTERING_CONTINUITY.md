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

## Outstanding evidence

FP breakdown, ROI experiments, role decisions, continuity experiments, selected changes, new sealed results, performance, limitations and final regressions are pending. This protocol is not a success claim.
