# FAIM-Native Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system libs (Postgres, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies (Minimal for Native)
COPY requirements.txt .
# Ensure we have essential prod servers
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn[standard] psycopg2-binary redis qdrant-client

# Copy Code
COPY faim_native/ /app/

# Environment
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Non-root user
RUN useradd -m -u 1000 -s /bin/false faim && chown -R faim:faim /app
USER faim

# Healthcheck (Native path)
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/ready || exit 1

# Run (Native Entrypoint)
CMD ["gunicorn", "api.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
