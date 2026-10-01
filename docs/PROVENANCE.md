# Source provenance

Target history begins with `df73a01a44304317326956abbc959b52ff91043a` (initial README), preserved as an ancestor.

Imported from read-only source snapshots:

* [Isaksend/ai-scouter](https://github.com/Isaksend/ai-scouter), commit `fe0a3d612385ac4301c3f266dad34ecea69395d0`: `src/*` imported as `backend/app/cv/*`. The Streamlit gallery algorithm is integrated into the new CV service. The old FastAPI/database modules were audited, not copied: they contain hardcoded credentials and fake inference. Original source remains available at the pinned commit.
* [Isaksend/scout_ai_front](https://github.com/Isaksend/scout_ai_front), commit `5faa616c70b237c623b42caf217fe1ae2c76a674`: React source and Vite/package configuration imported into `frontend/`, then repaired and redesigned.

The import commit is a reviewable baseline, not a runnable release. No nested Git directories, upstream history containing credentials, weights, or videos were imported. Neither source repository was modified or pushed to. Only the target origin is configured.

Neither source snapshot provides a LICENSE. No license for third-party source is invented here. Ownership/redistribution terms must be resolved by the project owner before wider distribution. Ultralytics has its own license terms; review them for your deployment.
