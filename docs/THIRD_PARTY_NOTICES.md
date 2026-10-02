# Third-party source and runtime notices

This inventory does not assign a license to ScoutAI or replace the original license texts. The imported team source and publication hold are documented in [PROVENANCE.md](PROVENANCE.md). The current candidate is not presented as an MIT-licensed combined work.

## Frontend distribution

`npm run build` copies the installed license texts verbatim into `dist/third-party-licenses.txt`, served as `/third-party-licenses.txt` in native preview and Compose. The generator fails if a selected notice is missing. It includes React, React DOM, Scheduler, React Router, React Router DOM, cookie, set-cookie-parser and Axios. Versions come from installed package metadata under the committed npm lockfile. React Router's declared dependencies are included conservatively even if tree-shaken from a particular build. Axios browser builds omit its Node-only adapters; this is not a claim that the complete Node dependency tree is embedded in the browser.

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
