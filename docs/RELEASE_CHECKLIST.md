# Portfolio v1 release checklist

Scope: finish the existing full-stack application; CV models, thresholds and research are frozen. This is the single continuation checklist. Current branch: `release/portfolio-v1`.

| Task | Status | Verification / evidence |
|---|---|---|
| Verify and merge PR4 | DONE | Head40351dd; Actions37045893830 backend/frontend/E2E success; merged445a400c77ce343f84ad4fc648c4bd6b633577e2 |
| Baseline before changes | PASS | 106 pytest, Ruff, frontend npm ci/lint/build; audit0; reachable-history scan0 |
| Privacy, server permissions, export | PASS | Default private, explicit sharing, open-page revocation and protected export in API/browser tests |
| Fresh/legacy SQLite migrations | PASS | Fresh/repeated upgrade, original rows/hashes/results preserved, missing constraints rejected, isolated backup/restore |
| History, onboarding, report/print, responsive UX | PASS | 1440/768/390 px browser checks; print rendering; five inspected DEMO screenshots |
| Native setup/start/stop/doctor | PASS | Clean OS-temp source copy, setup twice, DB/config preserved, ports/PID/lock/partial-failure checks; native run20261002T200742467874Z |
| Compose and production frontend | PASS LOCAL | Local build, three healthy services, full browser flow and restart row-digest preservation; CI job added |
| Full verification | PASS LOCAL | 117 pytest/0 skips, Ruff/compileall/build/lint; npm audit0; pip audit0 with two CPU-wheel skips; DEMO + panorama/broadcast REAL + CPU smoke; [evidence](../validation/results/portfolio-v1-2026-10-03.json) |
| README, portfolio, operations, changelog, notices | DONE | Research/provenance retained; relative file links checked; no local-user links; browser dependency notices generated |
| Publication rights | PENDING OWNER | Upstream lacks LICENSE; ai-scouter says All rights reserved. Clarification asked; engineering continues. No license assigned without confirmation |
| Final read-only review | DONE | Access/startup/license agents reviewed current diff; concrete findings fixed and rechecked; not human approval |
| Release PR and final-head CI | PUBLICATION HANDOFF | Push candidate as draft; actual final SHA/check links recorded in PR/release draft, not recursively embedded here |
| Merge, annotated tag, public release | HELD | No existing v1/tag at preflight. Owner rights/licensing confirmation required before advancing draft; no bypass |
| Handoff and closure | FINAL HANDOFF | OS-temp handoff references this checklist and actual remote state; finish bounded candidate work, no new CV phase |

Read-only initial reviews identified unrestricted scout access, missing migrations/export/history pagination, stale denied data in the UI, cleanup failure before job commit, and missing managed startup/production frontend. Baseline had no test failures. Agents edit no files.

Final design critique: actual desktop/mobile reports, entry, selection, tablet scouting and print capture inspected. Existing sports palette/layout retained; print muted text was darkened after visual inspection. New screenshots use generated imagery and explicitly synthetic accounts/metrics. No UI mockup substitutes for browser evidence.

Design plan: keep Segoe UI/system sans, left-aligned data and existing sports-report layout. Colors: navy `#080d19`, panel `#0b1425`, text `#eef4ff`, muted `#aab8cf`, cyan `#62e6eb`, violet `#a99aff`. Add a practical first-run explanation, visible publication state, compact chronological history and report actions. Preserve the pitch visualization as the main visual; no ornamental dashboard redesign. Reviewed against the brief: user decisions, real statuses and honest limitations take precedence over decorative metrics.

Layout: `sidebar | page title + primary action / profile & consent / chronological analyses`; report: `title + export/print / metrics / movement + metadata / warnings + preview`. At narrow widths use the existing stacked navigation/content pattern. Print removes navigation/actions and retains mode, warnings, trajectory, metadata and preview.
