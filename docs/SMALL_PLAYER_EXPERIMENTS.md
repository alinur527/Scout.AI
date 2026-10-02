# Small-player experiment protocol (2026-10-02)

## Integration baseline

PR #1 was open, mergeable, targeted main and had successful run36928035973 at e65bbfd. It was merged using a merge commit d03a2700317c751ea50bbb050a584801fd215d77. PR #2 was retargeted from revive/scout-ai to main without rewriting commits; the diff remained five commits /39 files. Its hypothetical merge tree equalled its existing head tree. After retargeting, 58 pytest tests, Ruff, compileall, frontend ci/lint/build, demo E2E, real CPU smoke and all three opt-in football reruns passed. Raw/tracked TP/FP/FN matched the previous report exactly. Successful CI run36933062448 remained associated with its unchanged head. PR #2 was merged as24a389bad4aa2b777f04eb8fe25c1b895e680b07. Main was clean and identical in content to44c4558; historical branches were retained.

New work is on cv/small-player-detection from main24a389b. See existing FOOTBALL_VALIDATION.md for the previous stage, including rejected tracker/ankle changes and movement safety.

## Preregistered split and selection

Before any new-match inference: SoccerTrackv2 challenge clips117093 (B1 vsB2) and118575 (C1 vsC2) are DEV;118576 (D1 vsD2) is HOLDOUT. The publisher identifies these as different university matches; dates are unavailable. First120 decoded frames of each are selected by a fixed rule, without consulting model output. Existing UVY steady/zoom are previously seen DEV diagnostics for pan/zoom/crowd tradeoffs; they are never holdout. No training/fine-tuning is planned.

Score raw player detection separately from tracker-confirmed boxes at IoU>=.5 using the existing scorer. Primary criterion: DEV football-player F1, checking each clip's recall and FP counts, small-player recall, runtime and identity continuity. A precision increase that discards players, or recall increase with excessive FP, does not qualify. Do not invent a composite score. Freeze the candidate configuration before opening HOLDOUT metrics; run only baseline and that frozen candidate on HOLDOUT, with no retuning afterwards. Failure of HOLDOUT rejects the production change and is retained as evidence.

Small-player reference: GT area scaled to a1280px maximum image dimension <=32^2 pixels (fixed reference resolution independent of candidate imgsz). Report matched TP/FN/recall, not small-player precision: unmatched predictions do not have a reliable GT size category. Publisher challenge GT is0-based with22player/GK identities and -1 placeholders; no referee/ball positives. Inspect alignment on raw frames before inference. Human expertise/completeness uncertainty must be disclosed.

## Limited matrix

Baseline: current YOLO11n-pose, native640..1280 policy, conf.3, NMS.5, original BoT-SORT, no ROI.

DEV alternatives: (A) YOLO11s-pose at the same input; (B) YOLO11n person detector at the same input, bbox ground fallback for evaluation; (C) original pose at1920; (D) original pose with2x2 overlapping960px tiles and global NMS; (E) original pose plus conservative grass-envelope pitch filtering; (F) best viable detector/resolution plus the filter, if E's TP-loss tradeoff warrants it. These are opt-in harness configs, not active application defaults. Maximum two new weight files; no new CUDA packages. Reuse original BoT-SORT to measure how detector changes affect continuity, without repeating previously rejected tracker parameter searches. Stitching is conditional on identity errors becoming the dominant failure, and requires adequate identity GT.

Physical metrics remain subject to all existing timing, gap, calibration and camera gates. No compensation or new physical accuracy claim.

Sources, exact ranges/hashes, counts, selected/rejected options, performance, HOLDOUT result and final regressions will be appended from observed outputs. Protocol choices above are frozen before new-match predictions.
