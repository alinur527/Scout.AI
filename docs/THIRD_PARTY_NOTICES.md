# Third-party source and runtime notices

ScoutAI project source is licensed under **AGPL-3.0-only**; see [LICENSE](../LICENSE) and [NOTICE](../NOTICE). The owner's confirmation of permission for the imported team source is recorded in [PROVENANCE.md](PROVENANCE.md). This inventory preserves independent upstream terms; it does not replace original license texts or claim ownership of third-party work.

## Frontend distribution

`npm run build` copies the installed license texts verbatim into `dist/third-party-licenses.txt`, served as `/third-party-licenses.txt` in native preview and Compose. The generator fails if a selected notice is missing. It includes React, React DOM, Scheduler, React Router, React Router DOM, cookie, set-cookie-parser and Axios. Versions come from installed package metadata under the committed npm lockfile. React Router's declared dependencies are included conservatively even if tree-shaken from a particular build. Axios browser builds omit its Node-only adapters; this is not a claim that the complete Node dependency tree is embedded in the browser.

Development and production builds also include unaltered project `LICENSE.txt`, `NOTICE.txt`, this inventory as `THIRD_PARTY_NOTICES.txt`, and `SOURCE.txt`. The visible UI notice links to copyright/no-warranty/redistribution information and the complete [v1.0.0 corresponding source](https://github.com/alinur527/Scout.AI/tree/v1.0.0). Build/run instructions, dependency declarations, migrations and configuration templates are in that source. Backend images carry LICENSE, NOTICE and this inventory under `/app`; installed package licenses/metadata are retained. Modified deployments must publish and offer the source of their actual running version, updating `frontend/src/release.js` and NOTICE before building.

## Models and dataset/image assets (separate licenses)

- **Ultralytics models/code:** upstream ownership remains with Ultralytics and its contributors. ScoutAI uses the publisher's AGPL-3.0 route, including its applicable model terms. Model weights are downloaded explicitly from upstream and are not committed or attached to this release; ScoutAI does not grant its own license to those weights. See the [official policy](https://www.ultralytics.com/license) and [versioned software license](https://github.com/ultralytics/ultralytics/blob/v8.4.26/LICENSE).
- **UVY research figures** in `docs/football/` (excluding the SoccerTrack subdirectory): Elton Alencar and Rosiane de Freitas, **CC BY 4.0**. Source links, credit, resizing/overlay changes and research context remain in [FOOTBALL_VALIDATION.md](FOOTBALL_VALIDATION.md).
- **SoccerTrack v2 figures** in `docs/football/small-player/`: Atom Scott, Ikuma Uchida, Kento Kuroda, Yufi Kim and Keisuke Fujii, **CC BY 4.0** under the publisher's LICENSE-DATA. Attribution and changes remain in [SMALL_PLAYER_EXPERIMENTS.md](SMALL_PLAYER_EXPERIMENTS.md).
- **TeamTrack evaluation inputs:** publisher metadata records MIT; source/license records remain in [PLAYER_FILTERING_CONTINUITY.md](PLAYER_FILTERING_CONTINUITY.md) and its source manifest. No raw footage is distributed here.
- **Portfolio screenshots** in `docs/screenshots/`: captured locally from ScoutAI's explicitly synthetic DEMO, with no private player footage.

These independent assets retain their original licenses. The project's AGPL grant does not purport to relicense them. Retain their attribution and modification disclosures when redistributing figures.

## Selected direct/transitive runtime inventory

Verified against installed metadata during release preparation. This is a selected inventory, not a full legal-compliance certification. Exact package license files and bundled component notices govern.

| Scope | Components | License metadata |
|---|---|---|
| Browser direct | React / React DOM 19.2.3; React Router DOM 7.18.4; Axios 1.20.0 | MIT |
| Browser transitive | Scheduler 0.27.0; React Router 7.18.4; cookie 1.1.1; set-cookie-parser 2.7.2 | MIT |
| API/database | FastAPI 0.135.1; SQLAlchemy 2.0.48; Alembic 1.20.0; Pydantic 2.13.5; pydantic-settings 2.15.0; PyJWT 2.15.1; pwdlib 0.3.0; filelock 3.25.0 | MIT |
| API/process | Uvicorn 0.41.0; Starlette 1.7.0; psutil 7.2.2 | BSD-3-Clause |
| Upload | python-multipart 0.0.32 | Apache-2.0 |
| Optional PostgreSQL driver | psycopg / psycopg-binary 3.3.3 | LGPL-3.0-only |
| Vision | opencv-python 4.12.0.88; Docker uses opencv-python-headless 4.12.0.88 | Apache-2.0 plus bundled component notices |
| CV | Ultralytics 8.4.26; ultralytics-thop 2.2.2 | AGPL-3.0 |
| CV/numerics | Torch 2.10.0+cpu; TorchVision 0.25.0+cpu; NumPy 2.2.6; SciPy 1.17.1; lap 0.5.13 | BSD-family; exact component/bundled terms apply |
| CV | Supervision 0.27.0.post1 | MIT |
| Selected transitives | certifi 2026.7.22; tqdm 4.70.1 | MPL-2.0; MPL-2.0 AND MIT |
| Selected transitives | requests 2.34.2; packaging 26.3; Pillow 12.3.0 | Apache-2.0; Apache-2.0 OR BSD-2-Clause; MIT-CMU |
| Selected transitives | typing-extensions 4.16.0; greenlet 3.5.6 | PSF-2.0; MIT AND PSF-2.0 |

Direct Python requirements are pinned; transitive resolutions can vary by platform/date. Native virtual environments and Docker images retain distribution metadata and installed license files. In particular, NumPy, SciPy, OpenCV and PyTorch contain bundled components with additional notices; a single top-level label is not a substitute. The DEMO Docker image does not contain the optional Torch/Ultralytics CV stack. Base Python, Node and Nginx container images retain their upstream terms as distributed.

References: [Ultralytics pinned license](https://github.com/ultralytics/ultralytics/blob/v8.4.26/LICENSE), [Ultralytics publisher policy](https://www.ultralytics.com/license), [OpenCV headless package metadata](https://pypi.org/project/opencv-python-headless/4.12.0.88/). Weights and datasets are not ScoutAI-owned assets; follow their original terms and the attribution in the research reports.
