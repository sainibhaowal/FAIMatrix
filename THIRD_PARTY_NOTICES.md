# Third-party notices

FAIM-Native source code is licensed under the [Apache License 2.0](LICENSE) and original documentation/assets under [CC BY 4.0](LICENSE-DOCS.md). This project incorporates and interoperates with third-party open-source packages, lexical datasets, container images, and optional external providers, each of which remains governed by its own license terms.

This file summarizes the verified direct runtime dependencies, bundled lexical data, and container images defined in [`requirements.txt`](requirements.txt), [`faim-benchmarks/pyproject.toml`](faim-benchmarks/pyproject.toml), [`frontend/package.json`](frontend/package.json), [`Dockerfile`](Dockerfile), [`frontend/Dockerfile`](frontend/Dockerfile), and the Docker Compose files. Every license name below links directly to its full license text copy; see also the [License texts index](#7-direct-license-texts-index). For transitive dependency graphs, inspect [`frontend/pnpm-lock.yaml`](frontend/pnpm-lock.yaml) or generated Python/Node distribution metadata before redistributing binaries or hosted bundles.

---

## 1. Required data attribution: ConceptNet 5 (CC BY-SA 4.0)

`faim_native/lexical/data/conceptnet_synonyms.json.gz` is compiled from **ConceptNet 5.7.0** (`conceptnet-assertions-5.7.0.csv.gz`) via [`faim_native/lexical/conceptnet_builder.py`](faim_native/lexical/conceptnet_builder.py).

> This work includes data from ConceptNet 5, compiled by the Commonsense Computing Initiative. ConceptNet 5 is available under the [CC BY-SA 4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html) license (<https://creativecommons.org/licenses/by-sa/4.0/>). Source project: <https://conceptnet.io>.
>
> ConceptNet 5 incorporates knowledge created by contributors to Commonsense Computing projects, Wikimedia projects, DBpedia, OpenCyc, Games with a Purpose, Princeton University's WordNet, Francis Bond's Open Multilingual WordNet, and Jim Breen's JMDict.

Citation: Robyn Speer, Joshua Chin, and Catherine Havasi (2017), *"ConceptNet 5.5: An Open Multilingual Graph of General Knowledge"*, AAAI-17.

Any redistributed derivative or remix of the compiled ConceptNet lexical data in `faim_native/lexical/data/` must remain licensed under [CC BY-SA 4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html).

---

## 2. Copyleft and redistribution notices

Review these specific licenses before distributing binaries or operating a modified hosted service:

- **`PyMuPDF` (`pymupdf`):** Dual-licensed under [GNU AGPL-3.0](https://spdx.org/licenses/AGPL-3.0-only.html) or the Artifex Commercial License (<https://artifex.com/licensing/>). Hosted/commercial operators must comply with AGPL-3.0, obtain an Artifex commercial license, or remove `pymupdf` and use permissive PDF parsers ([`pypdf`](https://spdx.org/licenses/BSD-3-Clause.html), [`pdfplumber`](https://spdx.org/licenses/MIT.html)).
- **`psycopg` ([LGPL-3.0-only](https://spdx.org/licenses/LGPL-3.0-only.html)) and `psycopg2-binary` ([LGPL with exceptions](https://spdx.org/licenses/LGPL-3.0-only.html)):** Dynamic linking / unmodified redistribution terms under LGPL apply when shipping combined distributions.
- **`orjson` ([MPL-2.0](https://spdx.org/licenses/MPL-2.0.html) AND ([Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) OR [MIT](https://spdx.org/licenses/MIT.html))):** Weak copyleft (MPL-2.0) or permissive dual option per upstream distribution metadata.

---

## 3. Python backend and benchmark dependencies

Direct runtime packages declared in [`requirements.txt`](requirements.txt) and [`faim-benchmarks/pyproject.toml`](faim-benchmarks/pyproject.toml) (licenses verified against installed distribution metadata):

| Package | License | Component Role |
| :--- | :--- | :--- |
| `fastapi` | [MIT](https://spdx.org/licenses/MIT.html) | HTTP / OpenAPI / SSE API framework |
| `uvicorn` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | ASGI server runtime |
| `SQLAlchemy` | [MIT](https://spdx.org/licenses/MIT.html) | PostgreSQL ORM and SQL toolkit |
| `pydantic` | [MIT](https://spdx.org/licenses/MIT.html) | Schema validation and settings |
| `psycopg` | [LGPL-3.0-only](https://spdx.org/licenses/LGPL-3.0-only.html) | PostgreSQL driver (v3) |
| `psycopg2-binary` | [LGPL with exceptions](https://spdx.org/licenses/LGPL-3.0-only.html) | PostgreSQL driver |
| `redis` | [MIT](https://spdx.org/licenses/MIT.html) | Redis client |
| `qdrant-client` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Qdrant vector index client |
| `python-multipart` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Multipart file upload parser |
| `httpx` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Async/sync HTTP client & benchmark client |
| `orjson` | [MPL-2.0](https://spdx.org/licenses/MPL-2.0.html) AND ([Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) OR [MIT](https://spdx.org/licenses/MIT.html)) | Fast JSON serialization |
| `PyJWT` | [MIT](https://spdx.org/licenses/MIT.html) | JWT signing and verification |
| `argon2-cffi` | [MIT](https://spdx.org/licenses/MIT.html) | Argon2id password/API-key hashing |
| `cryptography` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) OR [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | AES-GCM envelope encryption and key primitives |
| `email-validator` | [Unlicense](https://spdx.org/licenses/Unlicense.html) | Email validation |
| `pillow` | [MIT-CMU](https://spdx.org/licenses/MIT-CMU.html) | Image processing |
| `defusedxml` | [PSFL](https://spdx.org/licenses/Python-2.0.html) | XML entity-expansion defense |
| `pytesseract` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Tesseract OCR wrapper |
| `pymupdf` | [GNU AGPL-3.0](https://spdx.org/licenses/AGPL-3.0-only.html) OR Artifex Commercial | High-speed PDF extraction |
| `pdfplumber` | [MIT](https://spdx.org/licenses/MIT.html) | PDF text/table extraction |
| `pypdf` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Pure-Python PDF reader |
| `python-docx` | [MIT](https://spdx.org/licenses/MIT.html) | DOCX extraction |
| `openpyxl` | [MIT](https://spdx.org/licenses/MIT.html) | XLSX spreadsheet reader |
| `xlrd` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Legacy XLS spreadsheet reader |
| `python-pptx` | [MIT](https://spdx.org/licenses/MIT.html) | PPTX presentation reader |
| `psutil` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Host CPU/RAM inspection for autoscaling |
| `numpy` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) AND [0BSD](https://spdx.org/licenses/0BSD.html) AND [MIT](https://spdx.org/licenses/MIT.html) AND [Zlib](https://spdx.org/licenses/Zlib.html) AND [CC0-1.0](https://spdx.org/licenses/CC0-1.0.html) | Dense vector math and benchmark scoring |
| `torch` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) AND [Apache-2.0 WITH LLVM-exception](https://spdx.org/licenses/LLVM-exception.html) AND [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) AND [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | CPU/CUDA tensor execution |
| `transformers` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Hugging Face model inference |
| `sentence-transformers` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Optional dense embedding providers |
| `huggingface_hub` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Optional model and dataset downloads |
| `datasets` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Benchmark dataset loader |
| `nltk` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Lexical utilities |
| `requests` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | HTTP requests |
| `paddlepaddle` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Optional OCR runtime |
| `paddleocr` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Optional OCR engine |
| `pytest` / `pytest-xdist` | [MIT](https://spdx.org/licenses/MIT.html) | Test runner and parallel execution |
| `pytest-asyncio` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Async test support |

Static-analysis and formatting tools in [`requirements-quality.txt`](requirements-quality.txt) (`ruff`, `black`, `mypy`, `bandit`) are development/CI gates only and are not required in production runtime containers.

---

## 4. Frontend JavaScript dependencies (`frontend/package.json`)

Direct runtime dependencies defined in [`frontend/package.json`](frontend/package.json) (development/test tooling such as `vitest`, `playwright`, `eslint`, `prettier`, and `typescript` are dev-only):

| Package | License | Role |
| :--- | :--- | :--- |
| `next` | [MIT](https://spdx.org/licenses/MIT.html) | Next.js web framework |
| `react` / `react-dom` | [MIT](https://spdx.org/licenses/MIT.html) | UI component runtime |
| `next-auth` | [ISC](https://spdx.org/licenses/ISC.html) | Authentication session framework |
| `@next-auth/prisma-adapter` | [ISC](https://spdx.org/licenses/ISC.html) | Prisma adapter for NextAuth |
| `@prisma/client` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Database client for auth session persistence |
| `three` | [MIT](https://spdx.org/licenses/MIT.html) | WebGL 3D rendering engine |
| `react-force-graph-3d` | [MIT](https://spdx.org/licenses/MIT.html) | 3D graph visualization (`FIG View`) |
| `recharts` | [MIT](https://spdx.org/licenses/MIT.html) | Telemetry and metrics charts |
| `framer-motion` | [MIT](https://spdx.org/licenses/MIT.html) | UI motion and transitions |
| `lucide-react` | [ISC](https://spdx.org/licenses/ISC.html) | Icon library |
| `zustand` | [MIT](https://spdx.org/licenses/MIT.html) | Client state management |
| `pdfjs-dist` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Browser PDF inspection |
| `mammoth` | [BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) | DOCX preview conversion |
| `react-markdown` / `remark-gfm` | [MIT](https://spdx.org/licenses/MIT.html) | Markdown rendering |
| `react-syntax-highlighter` | [MIT](https://spdx.org/licenses/MIT.html) | Code block syntax highlighting |
| `jsonwebtoken` | [MIT](https://spdx.org/licenses/MIT.html) | Token utilities |
| `bcryptjs` | [BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) | Password hashing |
| `qrcode` | [MIT](https://spdx.org/licenses/MIT.html) | TOTP QR generation |
| `nodemailer` | [MIT-0](https://spdx.org/licenses/MIT-0.html) | SMTP transport |
| `resend` | [MIT](https://spdx.org/licenses/MIT.html) | Transactional email client |
| `@react-email/render` / `react-email` | [MIT](https://spdx.org/licenses/MIT.html) | Email templates |
| `clsx` / `tailwind-merge` / `tailwindcss-animate` | [MIT](https://spdx.org/licenses/MIT.html) | Styling utilities |
| `class-variance-authority` | [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) | Component variant utilities |

---

## 5. Container base and infrastructure images

Container images referenced in [`Dockerfile`](Dockerfile), [`frontend/Dockerfile`](frontend/Dockerfile), and `docker-compose*.yml`:

- **`python:3.11-slim`** and **`node:22-alpine`:** Official Python ([PSFL](https://spdx.org/licenses/Python-2.0.html)) and Node.js ([MIT](https://spdx.org/licenses/MIT.html)) base images; base OS packages in Debian/Alpine remain subject to their distribution licenses.
- **`pgvector/pgvector:pg15`:** PostgreSQL and `pgvector` extension ([PostgreSQL License](https://spdx.org/licenses/PostgreSQL.html)).
- **`redis:7-alpine`:** Redis server image on Alpine Linux (upstream Redis OSS / RSALv2 / SSPLv1 per upstream image tag terms; check the exact image tag before redistributing).
- **`qdrant/qdrant`:** Qdrant vector database ([Apache-2.0](https://spdx.org/licenses/Apache-2.0.html)).
- **`caddy:2-alpine`:** Caddy web server / reverse proxy ([Apache-2.0](https://spdx.org/licenses/Apache-2.0.html)) in [`docker-compose.vps.yml`](docker-compose.vps.yml).

---

## 6. Optional benchmarks, models, and external APIs

- **Benchmark datasets (`faim-benchmarks`):** External datasets such as `BeIR/SciFact`, `BeIR/NFCorpus`, `FiQA`, `TREC-COVID`, `ArguAna`, `LoCoMo`, and `LongMemEval` are downloaded only at benchmark execution time and remain governed by their original dataset licenses.
- **Model weights:** Optional embedding or OCR weights (such as `ibm-granite` or `BAAI/bge-m3`) are downloaded separately when configured and remain governed by their upstream model licenses.
- **External services:** Configured LLM, embedding, and email providers (such as OpenAI, Anthropic, Google, Ollama, or Resend) remain subject to their respective terms of service and billing agreements.

---

## 7. Direct license texts index

Use the links below to inspect the full verbatim text of every license referenced in this repository:

| License ID | Category | Full License Text |
| :--- | :--- | :--- |
| `Apache-2.0` | Permissive (with patent grant) | [Local `LICENSE`](LICENSE) / [SPDX Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) |
| `CC-BY-4.0` | Documentation / Media Attribution | [Local `LICENSE-DOCS.md`](LICENSE-DOCS.md) / [SPDX CC-BY-4.0](https://spdx.org/licenses/CC-BY-4.0.html) |
| `CC-BY-SA-4.0` | Share-Alike Data License | [SPDX CC-BY-SA-4.0](https://spdx.org/licenses/CC-BY-SA-4.0.html) |
| `MIT` | Permissive | [SPDX MIT](https://spdx.org/licenses/MIT.html) |
| `MIT-0` | Permissive (No Attribution) | [SPDX MIT-0](https://spdx.org/licenses/MIT-0.html) |
| `MIT-CMU` | Permissive | [SPDX MIT-CMU](https://spdx.org/licenses/MIT-CMU.html) |
| `ISC` | Permissive | [SPDX ISC](https://spdx.org/licenses/ISC.html) |
| `BSD-2-Clause` | Permissive | [SPDX BSD-2-Clause](https://spdx.org/licenses/BSD-2-Clause.html) |
| `BSD-3-Clause` | Permissive | [SPDX BSD-3-Clause](https://spdx.org/licenses/BSD-3-Clause.html) |
| `0BSD` | Permissive (Zero-Clause) | [SPDX 0BSD](https://spdx.org/licenses/0BSD.html) |
| `Zlib` | Permissive | [SPDX Zlib](https://spdx.org/licenses/Zlib.html) |
| `Unlicense` | Public Domain Equivalent | [SPDX Unlicense](https://spdx.org/licenses/Unlicense.html) |
| `CC0-1.0` | Public Domain Dedication | [SPDX CC0-1.0](https://spdx.org/licenses/CC0-1.0.html) |
| `Python-2.0` (`PSFL`) | Permissive | [SPDX Python-2.0](https://spdx.org/licenses/Python-2.0.html) |
| `PostgreSQL` | Permissive | [SPDX PostgreSQL](https://spdx.org/licenses/PostgreSQL.html) |
| `LLVM-exception` | Permissive License Exception | [SPDX LLVM-exception](https://spdx.org/licenses/LLVM-exception.html) |
| `MPL-2.0` | Weak Copyleft (File-Level) | [SPDX MPL-2.0](https://spdx.org/licenses/MPL-2.0.html) |
| `LGPL-3.0-only` | Weak Copyleft (Library) | [SPDX LGPL-3.0-only](https://spdx.org/licenses/LGPL-3.0-only.html) |
| `AGPL-3.0-only` | Strong Copyleft (Network) | [SPDX AGPL-3.0-only](https://spdx.org/licenses/AGPL-3.0-only.html) |
