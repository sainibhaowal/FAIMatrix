# Third-party notices

FAIM-Native depends on open-source packages, container images, browser libraries, and optional provider integrations. This repository does not relicense those dependencies.

Their applicable licenses and notices are defined by their own distribution metadata and lockfiles, including:

- `requirements.txt` for Python packages;
- `package-lock.json`, `frontend/package-lock.json`, and `frontend/pnpm-lock.yaml` for JavaScript packages;
- `docker-compose.yml`, `docker-compose.test.yml`, and `docker-compose.vps.yml` for container images;
- provider-specific files and documentation for optional OCR, embedding, and infrastructure integrations.

Before redistributing a binary image, hosted bundle, or materially modified distribution, generate and ship a complete dependency notice report for the exact versions included in that artifact. Do not remove upstream copyright or license notices.

The project license applies only to FAIM-Native material that the project has the right to license. It does not grant rights to third-party names, logos, datasets, model weights, API services, or user-provided content.
