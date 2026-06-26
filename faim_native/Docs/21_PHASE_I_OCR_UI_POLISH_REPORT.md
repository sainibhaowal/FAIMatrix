# 21 - Phase I OCR Integration + UI Polish Report

Date: 2026-02-11

## Objective

Complete the approved Phase I scope:

1. real OCR integration for image/scanned uploads
2. supported-file coverage visibility in Storage UI
3. rounded storage card polish
4. docker/runtime readiness updates
5. regression-safe validation

## Implemented

## 1) OCR Backend Integration

Implemented OCR service:

- `faim_native/perception/extract/ocr_service.py`

Key behavior:

- OCR settings via env flags:
  - `FAIM_OCR_ENABLED`
  - `FAIM_OCR_ENGINE`
  - `FAIM_OCR_FAIL_CLOSED`
  - `FAIM_OCR_LANGS`
  - `FAIM_OCR_TIMEOUT_SECONDS`
  - `FAIM_OCR_MAX_IMAGE_PIXELS`
  - `FAIM_OCR_PDF_RENDER_DPI`
  - `FAIM_OCR_TESSERACT_CONFIG`
- image OCR path (`extract_text_from_image_bytes`)
- scanned PDF page OCR path (`extract_text_from_pdf_page`)
- fail-open vs fail-closed behavior controlled by flag

Extractor wiring:

- `faim_native/perception/extract/extractors_faim.py`
  - image uploads now attempt OCR first, fallback to `image_stub` when needed
  - image-only PDF pages now attempt OCR first, fallback to `image_stub` when needed

Encoding wiring:

- `faim_native/encoding/text_vectorizer.py`
  - explicit OCR-stub vector schema path for `image_stub` blocks

## 2) Supported File Coverage API

Added endpoint:

- `GET /api/v1/storage/supported-types`

File:

- `faim_native/api/routers/storage.py`

Response includes:

- max upload size
- total extensions + MIME types
- full extension + MIME lists
- category buckets
- extractor doc_type mapping counts
- OCR policy status and OCR-capable extension list

Contract freeze updated:

- `faim_native/api/contracts/storage_contract.py`
- `tests/unit/test_phase_a_storage_contract.py`

## 3) Storage UI Enhancements

File:

- `frontend/src/app/(app)/dashboard/storage/page.tsx`

Implemented:

- `Supported Files` button in upload panel
- supported-types side panel
- panel data fetch from `/api/v1/storage/supported-types`
- panel refresh/close behavior and keyboard close support
- storage card usage updated to rounded style

## 4) Rounded Card UI Polish

Files:

- `frontend/src/app/globals.css`
- `frontend/src/components/ui/Card.tsx`

Changes:

- centralized card radius variable
- `os-card` and `os-surface` rounded corners
- card inner border now inherits parent radius

## 5) Runtime and Docker Readiness

Dependencies:

- `requirements.txt`
  - `Pillow`
  - `pytesseract`
  - `pymupdf`
  - `pdfplumber`
  - `pypdf`
  - `python-docx`
  - `openpyxl`
  - `python-pptx`

Container updates:

- `Dockerfile`
- `Dockerfile.dev`
  - add `tesseract-ocr` and `tesseract-ocr-eng`

Compose/env wiring:

- `docker-compose.yml`
- `docker-compose.dev.yml`
- `env.template`
- `faim_native/runtime/config.py`
- `faim_native/runtime/feature_flags.py`

## Validation Evidence

## Python compile

- `python3 -m compileall faim_native` passed

## Backend tests

Command:

- `PYTHONPATH=faim_native pytest -q tests/unit/test_phase_a_storage_contract.py tests/unit/test_phase_a_feature_flags.py tests/unit/test_phase_i_ocr_extractor.py tests/acceptance/test_AT_P1_storage_api_surface.py tests/acceptance/test_AT_PI_storage_supported_types_surface.py tests/acceptance/test_AT_PF_storage_lifecycle_non_regression.py`

Result:

- `19 passed`

## Frontend targeted lint

Command:

- `cd frontend && npx eslint 'src/app/(app)/dashboard/storage/page.tsx' 'src/components/ui/Card.tsx' 'tests/e2e/storage-phase-f.spec.ts'`

Result:

- passed

## Frontend e2e (targeted)

Command:

- `cd frontend && npx playwright test tests/e2e/storage-phase-f.spec.ts --project=chromium --reporter=line`

Result:

- `2 passed`

Note:

- Full multi-project Playwright run reports Mobile Safari/WebKit missing browser binary in local environment unless `npx playwright install` is executed.

## Updated Documentation

- `faim_native/Docs/06_STORAGE_UI_AND_BACKEND_API_IMPLEMENTATION_REPORT.md`
- `faim_native/Docs/07_STORAGE_REMAINING_GAPS_AND_FUTURE_WORK_REPORT.md`
- `faim_native/Docs/20B_STORAGE_UI_RUNTIME_WORKFLOW_AND_MODES_GUIDE.md`
- `faim_native/Docs/README.md`

## Phase I Status

Phase I approved scope is implemented and validated with no contract break on existing storage routes.
