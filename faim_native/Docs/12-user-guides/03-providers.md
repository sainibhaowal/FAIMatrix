# Providers user guide

## Dashboard

- `/dashboard/providers` manages provider-facing settings.
- `/dashboard/embedding-providers` manages embedding providers.

## API families

The current provider routes are mounted under `/api/v1`:

- `/api/v1/embedding-providers`
- `/api/v1/ocr-providers`
- `/api/v1/reranker`

Each provider family exposes list/status, activation or switching, and test
operations where supported. Provider availability depends on configured
credentials and installed runtime dependencies. A visible provider entry is
not evidence that its external endpoint is configured or healthy.
