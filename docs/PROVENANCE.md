# Source provenance

Target history begins with `df73a01a44304317326956abbc959b52ff91043a` (initial README), preserved as an ancestor.

Imported from read-only source snapshots:

* [Isaksend/ai-scouter](https://github.com/Isaksend/ai-scouter), commit `fe0a3d612385ac4301c3f266dad34ecea69395d0`: `src/*` imported as `backend/app/cv/*`. The Streamlit gallery algorithm is integrated into the new CV service. The old FastAPI/database modules were audited, not copied: they contain hardcoded credentials and fake inference. Original source remains available at the pinned commit.
* [Isaksend/scout_ai_front](https://github.com/Isaksend/scout_ai_front), commit `5faa616c70b237c623b42caf217fe1ae2c76a674`: React source and Vite/package configuration imported into `frontend/`, then repaired and redesigned.

The import commit is a reviewable baseline, not a runnable release. No nested Git directories, upstream history containing credentials, weights, or videos were imported. Neither source repository was modified or pushed to. Only the target origin is configured.

## Publication status

**Public v1 release pending rights confirmation.** Neither pinned source snapshot supplies a source license. The [backend README at the imported revision](https://github.com/Isaksend/ai-scouter/blob/fe0a3d612385ac4301c3f266dad34ecea69395d0/README.md) states “© 2026 ScoutAI Project. All rights reserved.” No permission covering publication and applicable licensing of these imported contributions has been documented in this release process. This does not establish that the project owner lacks a private permission or ownership agreement.

The owner must confirm rights from all relevant contributors and an applicable [Ultralytics licensing path](https://www.ultralytics.com/license) before public release. The pinned [Ultralytics 8.4.26 license](https://github.com/ultralytics/ultralytics/blob/v8.4.26/LICENSE) is AGPL-3.0; its terms cannot be replaced with a blanket MIT label for this project. No license has been assigned to the imported source on the owner's behalf. Attribution alone does not grant redistribution rights. Engineering work can be reviewed as a release candidate while publication remains held.

## Assets and dependency notices

Current portfolio screenshots are captured from an isolated, explicitly synthetic DEMO with generated imagery and test accounts. They contain no private player footage or credentials. Historical football images/evidence retain their original source and attribution in the research documents: [UVY](FOOTBALL_VALIDATION.md), [SoccerTrack v2](SMALL_PLAYER_EXPERIMENTS.md), [TeamTrack](PLAYER_FILTERING_CONTINUITY.md).

No model weights, raw videos, real database, `.env` or runtime logs are included in source/release attachments. Official weight downloads remain explicit and retain upstream ownership. Runtime package notices and the frontend build's generated license file are described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
