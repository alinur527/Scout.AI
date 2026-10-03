# Source provenance

Target history begins with `df73a01a44304317326956abbc959b52ff91043a` (initial README), preserved as an ancestor.

Imported from read-only source snapshots:

* [Isaksend/ai-scouter](https://github.com/Isaksend/ai-scouter), commit `fe0a3d612385ac4301c3f266dad34ecea69395d0`: `src/*` imported as `backend/app/cv/*`. The Streamlit gallery algorithm is integrated into the new CV service. The old FastAPI/database modules were audited, not copied: they contain hardcoded credentials and fake inference. Original source remains available at the pinned commit.
* [Isaksend/scout_ai_front](https://github.com/Isaksend/scout_ai_front), commit `5faa616c70b237c623b42caf217fe1ae2c76a674`: React source and Vite/package configuration imported into `frontend/`, then repaired and redesigned.

The import commit is a reviewable baseline, not a runnable release. No nested Git directories, upstream history containing credentials, weights, or videos were imported. Neither source repository was modified or pushed to. Only the target origin is configured.

## Publication status

**Team-source publication permission confirmed by the project owner on 2026-10-03.** ScoutAI was a joint hackathon project. The owner confirmed permission from the relevant co-authors to publish, modify, distribute and deploy the shared ScoutAI code, and authorized the compatible open-source licensing route for this release. This record contains the owner's confirmation only; no private correspondence or personal proof is published.

Neither pinned source snapshot supplied a source license. The [backend README at the imported revision](https://github.com/Isaksend/ai-scouter/blob/fe0a3d612385ac4301c3f266dad34ecea69395d0/README.md) states “© 2026 ScoutAI Project. All rights reserved.” That historical notice and attribution are preserved in [NOTICE](../NOTICE); the owner's confirmed permission resolves the publication restriction for the imported project contributions.

ScoutAI project source is now **AGPL-3.0-only**, with the full text in [LICENSE](../LICENSE). The official [Ultralytics policy](https://www.ultralytics.com/license), [AGPL terms](https://www.ultralytics.com/legal/agpl-3-0-software-license) and pinned [Ultralytics 8.4.26 license](https://github.com/ultralytics/ultralytics/blob/v8.4.26/LICENSE) were rechecked on 2026-10-03. Their public, fully open-source application route fits this release; no closed-source or Enterprise grant is claimed. Complete source, migrations, configuration templates and build/run scripts are published together. The UI offers the corresponding v1.0.0 source, license, no-warranty notice and third-party notices without authentication. Modified deployments must update that offer to their own running source.

The imported prototypes were modified during restoration and release preparation through 2026-10-03. [NOTICE](../NOTICE), [CHANGELOG.md](../CHANGELOG.md) and Git history record the integration, safety, application, test, documentation and packaging changes. Original authorship is retained; ScoutAI does not claim ownership of Ultralytics code or models.

## Assets and dependency notices

Current portfolio screenshots are captured from an isolated, explicitly synthetic DEMO with generated imagery and test accounts. They contain no private player footage or credentials. Historical football images/evidence retain their original source and attribution in the research documents: [UVY](FOOTBALL_VALIDATION.md), [SoccerTrack v2](SMALL_PLAYER_EXPERIMENTS.md), [TeamTrack](PLAYER_FILTERING_CONTINUITY.md).

No model weights, raw videos, real database, `.env`, credentials, runtime logs or private permission proof are included in source/release attachments. Official weight downloads remain explicit and retain upstream ownership and terms. The project's AGPL grant does not relicense independent datasets, research images, model weights or third-party code. Their original licenses, attribution and change disclosures remain in the linked reports. Runtime package notices and generated distribution license files are described in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
