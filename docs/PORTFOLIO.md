# ScoutAI for a portfolio

## Описание проекта

ScoutAI — локальное full-stack приложение для просмотра движения выбранного игрока на футбольном видео. Пользователь загружает ролик, выбирает анонимный track ID, получает траекторию, тепловую карту и сохранённый отчёт, экспортирует JSON или печатает страницу. Профиль приватен по умолчанию; игрок явно разрешает скаутам доступ и может отозвать его.

Проект восстановлен из командных React/CV-прототипов с сохранением авторства и истории происхождения. Режим DEMO показывает весь сценарий на синтетических данных; REAL использует готовые YOLO-модели и BoT-SORT на CPU. Это интеграция и инженерная доработка, а не обучение собственной нейросети. Публичный релиз ожидает подтверждения прав, описанного в [PROVENANCE.md](PROVENANCE.md).

## English description

ScoutAI is a local full-stack football video workspace. A player uploads a clip, selects an anonymous track, and explores a saved trajectory, heatmap and report with JSON export and browser printing. Profiles are private by default; players explicitly grant and revoke scout access.

The project restores and integrates team React/CV prototypes while retaining source attribution. DEMO exercises the full workflow with synthetic data; REAL uses pretrained YOLO models and BoT-SORT on CPU. The work concerns application integration, persistence, authorization, reproducible setup and validation—not training a proprietary neural network. Public release remains pending the documented source-rights confirmation.

## Three resume bullets

- Восстановление и интеграция командного React/FastAPI CV-приложения: отдельный worker, постоянная очередь в SQLite, восстановление статусов после restart и сохранённые отчёты.
- Приватность по умолчанию, серверные проверки владельца/роли/согласия, отзыв доступа и защищённый JSON-экспорт; Alembic-миграция прежней схемы с сохранением данных.
- Воспроизводимый Windows setup и Docker DEMO, проверки backend и браузерного player/scout-сценария, реальные CPU CV smoke/E2E и документированные ограничения измерений.

English equivalents:

- Restored and integrated a team React/FastAPI CV application with a separate worker, durable SQLite jobs, restart recovery and saved reports.
- Implemented private-by-default profiles, server-side ownership/role/consent checks, revocation, protected JSON export and a data-preserving Alembic upgrade.
- Built reproducible Windows setup and Docker DEMO workflows, backend/browser validation and actual CPU inference checks with explicit measurement limitations.

These bullets describe work in the repository. They do not claim sole authorship of inherited CV/frontend code, customers, club adoption, commercial impact or model training.

## 60–90 second demonstration

Use an isolated DEMO installation and two explicitly registered test accounts, player and scout. Keep a scout session in a second browser context. Do not use real player information or private footage.

| Time | Action and narration |
|---|---|
| 0–15 s | Show the entry screen: “This is a local football video workspace. DEMO is synthetic; REAL runs pretrained models. Physical accuracy is not validated.” Sign in as the test player. |
| 15–30 s | Show the private profile. Open Analyze a video, choose the built-in synthetic sample and upload. Point to queued/processing/selection stages. |
| 30–45 s | Select Demo player 1 and build the report. Switch Heatmap/Path; point to the DEMO warning and selected anonymous ID. |
| 45–60 s | Download JSON and open print preview. Return to history, refresh and reopen the saved report. |
| 60–75 s | Explicitly enable sharing in the player profile. In the scout context, search the test profile and open its saved report. |
| 75–90 s | Revoke sharing as the player. The open scout page clears its report on polling; a new export is denied. Finish with: “The full workflow is tested; these demo numbers are not measured player performance.” |

Screenshots are sufficient for a compact presentation; no edited video is needed. [Desktop report](screenshots/report-desktop.png), [entry screen](screenshots/login-desktop.png), [selection](screenshots/gallery-desktop.png), [mobile report](screenshots/report-mobile.png), [tablet scouting](screenshots/scouting-tablet.png) were captured from the running DEMO app.

## Architecture in an interview

“React calls FastAPI with an expiring JWT. The API validates input, ownership and publication consent, then persists a job in SQLite. One separate worker claims jobs, runs OpenCV/YOLO/BoT-SORT, and writes selection data and the final report back to the database. The browser polls real stages. This keeps inference outside API requests and makes refresh/restart behavior explicit. Alembic upgrades the schema; the operating profile deliberately stays single-host and single-worker.”

The [README diagram](../README.md#architecture) and [API contract](API.md) provide concrete follow-up references.

## Engineering decisions and difficult parts

- **Honest metrics:** image movement is not automatically metres. Physical estimates require supported field calibration, camera stability and timestamps; unavailable values stay null. Track coverage describes observation coverage, not accuracy.
- **Durable work:** waiting for player selection is persisted rather than held in an HTTP request. Interrupted inference becomes a clear failure. Source cleanup errors cannot erase terminal state or crash the worker on a locked orphan.
- **Consent across interfaces:** filtering the directory alone is insufficient; detail and export recheck publication. Open scout pages clear revoked data, and exports fetch from the server at click time.
- **Safe upgrades and local operation:** a migration makes all legacy profiles private; unknown schemas are rejected. Start/stop tracks process identity and rolls back partial starts without killing unrelated services. Clean repeat setup and isolated backups/restores are tested.
- **CV scope discipline:** existing negative experiments are retained. Rejected filters, stitching and tracker changes were not reintroduced to improve the portfolio narrative.

## Honest answer about CV accuracy

“The application runs actual inference, but I would not present its distance/speed as validated sports measurements. Evaluation covered short football windows with documented labels and limitations. Panoramic person detection helped some small-player cases, while the independent fisheye source still had low recall and identity continuity did not generalize. Occlusion, staff/spectators, camera motion and track fragmentation remain important limitations. DEMO proves application connectivity; CPU smoke proves inference execution. Neither proves football or physical accuracy.”

See [football evidence](FOOTBALL_VALIDATION.md), [small-player results](SMALL_PLAYER_EXPERIMENTS.md) and [rejected continuity experiments](PLAYER_FILTERING_CONTINUITY.md). No mandatory new research phase is part of portfolio v1.

## Project-list Markdown

```markdown
### [ScoutAI](https://github.com/alinur527/Scout.AI)
Local football video workspace built with React, FastAPI, SQLite and a persistent Python CV worker. Private profiles, player-selected trajectories/heatmaps, saved reports, consent-based scouting and protected export. Includes synthetic DEMO, pretrained YOLO/BoT-SORT CPU inference, migrations, reproducible setup and browser tests. Restored from attributed team prototypes; physical accuracy is not validated. Public v1 release is pending source-rights confirmation.
```

Other repositories and the owner's profile README were not modified.
