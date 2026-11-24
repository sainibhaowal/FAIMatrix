# Third-party notices

FAIM-Native source code is licensed under the [Apache License 2.0](LICENSE) and original documentation/assets under [CC BY 4.0](LICENSE-DOCS.md). This project incorporates and interoperates with third-party open-source packages, lexical datasets, container images, and optional external providers, each of which remains governed by its own license terms.

This file summarizes the verified direct runtime dependencies, bundled lexical data, and container images defined in [`requirements.txt`](requirements.txt), [`faim-benchmarks/pyproject.toml`](faim-benchmarks/pyproject.toml), [`frontend/package.json`](frontend/package.json), [`Dockerfile`](Dockerfile), [`frontend/Dockerfile`](frontend/Dockerfile), and the Docker Compose files. For transitive dependency graphs, inspect the lockfiles ([`frontend/pnpm-lock.yaml`](frontend/pnpm-lock.yaml)) or generated Python/Node distribution metadata before redistributing binaries or hosted bundles.

---

## 1. Required data attribution: ConceptNet 5 (CC BY-SA 4.0)

`faim_native/lexical/data/conceptnet_synonyms.json.gz` is compiled from **ConceptNet 5.7.0** (`conceptnet-assertions-5.7.0.csv.gz`) via [`faim_native/lexical/conceptnet_builder.py`](faim_native/lexical/conceptnet_builder.py).

> This work includes data from ConceptNet 5, compiled by the Commonsense Computing Initiative. ConceptNet 5 is available under the **Creative Commons Attribution-ShareAlike 4.0 International License (CC BY-SA 4.0)**: <https://creativecommons.org/licenses/by-sa/4.0/>. Source project: <https://conceptnet.io>.
>
> ConceptNet 5 incorporates knowledge created by contributors to Commonsense Computing projects, Wikimedia projects, DBpedia, OpenCyc, Games with a Purpose, Princeton University's WordNet, Francis Bond's Open Multilingual WordNet, and Jim Breen's JMDict.

Citation: Robyn Speer, Joshua Chin, and Catherine Havasi (2017), *"ConceptNet 5.5: An Open Multilingual Graph of General Knowledge"*, AAAI-17.

Any redistributed derivative or remix of the compiled ConceptNet lexical data in `faim_native/lexical/data/` must remain licensed under **CC BY-SA 4.0**.

---

## 2. Copyleft and redistribution notices

Review these specific licenses before distributing binaries or operating a modified hosted service:

- **`PyMuPDF` (`pymupdf`):** Dual-licensed under **GNU AGPL-3.0 or Artifex Commercial License**. Hosted/commercial operators must either comply with AGPL-3.0, obtain an Artifex commercial license, or remove `pymupdf` and use permissive PDF parsers (`pypdf`, `pdfplumber`).
- **`psycopg` (`LGPL-3.0-only`) and `psycopg2-binary` (`LGPL with exceptions`):** Dynamic linking / unmodified redistribution obligations under LGPL apply when shipping combined distributions.
- **`orjson` (`MPL-2.0 AND (Apache-2.0 OR MIT)`):** Weak copyleft (MPL-2.0) or permissive dual option per upstream package metadata.

---

## 3. Python backend and benchmark dependencies

Direct runtime packages declared in [`requirements.txt`](requirements.txt) and [`faim-benchmarks/pyproject.toml`](faim-benchmarks/pyproject.toml) (licenses verified against installed distribution metadata):

| Package | License (Verified Metadata) | Component Role |
| :--- | :--- | :--- |
| `fastapi` | MIT | HTTP / OpenAPI / SSE API framework |
| `uvicorn` | BSD-3-Clause | ASGI server runtime |
| `SQLAlchemy` | MIT | PostgreSQL ORM and SQL toolkit |
| `pydantic` | MIT | Schema validation and settings |
| `psycopg` | LGPL-3.0-only | PostgreSQL driver (v3) |
| `psycopg2-binary` | LGPL with exceptions | PostgreSQL driver |
| `redis` | MIT | Redis client |
| `qdrant-client` | Apache-2.0 | Qdrant vector index client |
| `python-multipart` | Apache-2.0 | Multipart file upload parser |
| `httpx` | BSD-3-Clause | Async/sync HTTP client & benchmark client |
| `orjson` | MPL-2.0 AND (Apache-2.0 OR MIT) | Fast JSON serialization |
| `PyJWT` | MIT | JWT signing and verification |
| `argon2-cffi` | MIT | Argon2id password/API-key hashing |
| `cryptography` | Apache-2.0 OR BSD-3-Clause | AES-GCM envelope encryption and key primitives |
| `email-validator` | Unlicense | Email validation |
| `pillow` | MIT-CMU | Image processing |
| `defusedxml` | PSFL | XML entity-expansion defense |
| `pytesseract` | Apache License 2.0 | Tesseract OCR wrapper |
| `pymupdf` | GNU AGPL-3.0 OR Artifex Commercial | High-speed PDF extraction |
| `pdfplumber` | MIT | PDF text/table extraction |
| `pypdf` | BSD-3-Clause | Pure-Python PDF reader |
| `python-docx` | MIT | DOCX extraction |
| `openpyxl` | MIT | XLSX spreadsheet reader |
| `xlrd` | BSD | Legacy XLS spreadsheet reader |
| `python-pptx` | MIT | PPTX presentation reader |
| `psutil` | BSD-3-Clause | Host CPU/RAM inspection for autoscaling |
| `numpy` | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | Dense vector math and benchmark scoring |
| `torch` | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause | CPU/CUDA tensor execution |
| `transformers` | Apache-2.0 | Hugging Face model inference |
| `sentence-transformers` | Apache-2.0 | Optional dense embedding providers |
| `huggingface_hub` | Apache-2.0 | Optional model and dataset downloads |
| `datasets` | Apache-2.0 | Benchmark dataset loader |
| `nltk` | Apache-2.0 | Lexical utilities |
| `requests` | Apache-2.0 | HTTP requests |
| `paddlepaddle` | Apache Software License | Optional OCR runtime |
| `paddleocr` | Apache-2.0 | Optional OCR engine |
| `pytest` / `pytest-xdist` | MIT | Test runner and parallel execution |
| `pytest-asyncio` | Apache-2.0 | Async test support |

Static-analysis and formatting tools in [`requirements-quality.txt`](requirements-quality.txt) (`ruff`, `black`, `mypy`, `bandit`) are development/CI gates only and are not required in production runtime containers.

---

## 4. Frontend JavaScript dependencies (`frontend/package.json`)

Direct runtime dependencies defined in [`frontend/package.json`](frontend/package.json) (development/test tooling such as `vitest`, `playwright`, `eslint`, `prettier`, and `typescript` are dev-only):

| Package | License (Verified Metadata) | Role |
| :--- | :--- | :--- |
| `next` | MIT | Next.js web framework |
| `react` / `react-dom` | MIT | UI component runtime |
| `next-auth` | ISC | Authentication session framework |
| `@next-auth/prisma-adapter` | ISC | Prisma adapter for NextAuth |
| `@prisma/client` | Apache-2.0 | Database client for auth session persistence |
| `three` | MIT | WebGL 3D rendering engine |
| `react-force-graph-3d` | MIT | 3D graph visualization (`FIG View`) |
| `recharts` | MIT | Telemetry and metrics charts |
| `framer-motion` | MIT | UI motion and transitions |
| `lucide-react` | ISC | Icon library |
| `zustand` | MIT | Client state management |
| `pdfjs-dist` | Apache-2.0 | Browser PDF inspection |
| `mammoth` | BSD-2-Clause | DOCX preview conversion |
| `react-markdown` / `remark-gfm` | MIT | Markdown rendering |
| `react-syntax-highlighter` | MIT | Code block syntax highlighting |
| `jsonwebtoken` | MIT | Token utilities |
| `bcryptjs` | BSD-3-Clause | Password hashing |
| `qrcode` | MIT | TOTP QR generation |
| `nodemailer` | MIT-0 | SMTP transport |
| `resend` | MIT | Transactional email client |
| `@react-email/render` / `react-email` | MIT | Email templates |
| `clsx` / `tailwind-merge` / `tailwindcss-animate` | MIT | Styling utilities |
| `class-variance-authority` | Apache-2.0 | Component variant utilities |

---

## 5. Container base and infrastructure images

Container images referenced in [`Dockerfile`](Dockerfile), [`frontend/Dockerfile`](frontend/Dockerfile), and `docker-compose*.yml`:

- **`python:3.11-slim`** and **`node:22-alpine`:** Official Python and Node.js base images (base OS packages in Debian/Alpine remain subject to their distribution licenses).
- **`pgvector/pgvector:pg15`:** PostgreSQL (PostgreSQL License) with `pgvector` extension (PostgreSQL License).
- **`redis:7-alpine`:** Redis server image on Alpine Linux (upstream Redis OSS / RSALv2 / SSPLv1 per upstream tag terms; check the exact image tag before redistributing).
- **`qdrant/qdrant`:** Qdrant vector database (Apache License 2.0).
- **`caddy:2-alpine`:** Caddy web server / reverse proxy (Apache License 2.0) in [`docker-compose.vps.yml`](docker-compose.vps.yml).

---

## 6. Optional benchmarks, models, and external APIs

- **Benchmark datasets (`faim-benchmarks`):** External datasets such as `BeIR/SciFact`, `BeIR/NFCorpus`, `FiQA`, `TREC-COVID`, `ArguAna`, `LoCoMo`, and `LongMemEval` are downloaded only at benchmark execution time and remain governed by their original dataset licenses.
- **Model weights:** Optional embedding or OCR weights (such as `ibm-granite` or `BAAI/bge-m3`) are downloaded separately when configured and remain governed by their upstream model licenses.
- **External services:** Configured LLM, embedding, and email providers (such as OpenAI, Anthropic, Google, Ollama, or Resend) remain subject to their respective terms of service and billing agreements.
