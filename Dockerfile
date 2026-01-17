# FAIM-Native Production Dockerfile
# =============================================================================
# Multi-stage build for minimal image size and security.
#
# Features:
#   - Entrypoint gating (refuses to start with stale schema)
#   - Non-root user (security best practice)
#   - Healthcheck for K8s probes
# =============================================================================

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (from root requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn[standard] psycopg2-binary redis qdrant-client

# Copy ENTIRE application context (faim_native, scripts, config)
COPY . /app

# Set PYTHONPATH to include faim_native so modules (api, store) are importable
ENV PYTHONPATH=/app/faim_native:/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Non-root user (security)
RUN useradd -m -u 1000 -s /bin/false faim && chown -R faim:faim /app
USER faim

# Entrypoint gating
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/ready || exit 1

# Default command (imports 'api.app' which is in faim_native/)
CMD ["gunicorn", "api.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
