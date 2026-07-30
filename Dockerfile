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
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (from root requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn[standard] psycopg2-binary redis qdrant-client

# Non-root user (security) - Create BEFORE copy to fix ownership
RUN useradd -m -u 1000 -s /bin/false faim

# Set essential environment variables
ENV PYTHONPATH=/app/faim_native:/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Pre-create raw file store directory so Docker volume inherits correct owner.
# Must be done as root BEFORE USER switch; volume will mount with uid 1000 owner.
RUN mkdir -p /var/lib/faim/raw/blobs && chown -R 1000:1000 /var/lib/faim

# Copy application context with CORRECT OWNERSHIP in one step (Zero Duplicate Layers)
COPY --chown=faim:faim . /app
USER faim

# Entrypoint gating
RUN chmod +x /app/scripts/entrypoint.sh
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/ready || exit 1

# Default command (imports 'api.app' which is in faim_native/)
CMD ["gunicorn", "api.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
