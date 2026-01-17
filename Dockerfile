# FAIM-Native Production Dockerfile
# =============================================================================
# Multi-stage build for minimal image size and security.
#
# Features:
#   - Entrypoint gating (refuses to start with stale schema)
#   - Non-root user (security best practice)
#   - Healthcheck for K8s probes
# =============================================================================

FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn[standard] psycopg2-binary redis qdrant-client

# Copy application code
COPY faim_native/ /app/

# Copy entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Non-root user (security)
RUN useradd -m -u 1000 -s /bin/false faim && chown -R faim:faim /app
USER faim

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/ready || exit 1

# Entrypoint for migration gating
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["gunicorn", "api.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
