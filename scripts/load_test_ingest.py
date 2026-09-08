#!/usr/bin/env python3
"""Bounded real-service ingestion load probe.

This intentionally talks to a running FAIM API and uploads the caller's real
documents.  It does not mock extraction, storage, Postgres, Redis, or Qdrant.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path


def _post(url: str, body: bytes, headers: dict[str, str]) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=300) as response:  # nosec B310
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+", type=Path)
    parser.add_argument("--base-url", default=os.getenv("FAIM_BASE_URL", "http://localhost:8000"))
    parser.add_argument("--tenant", default=os.getenv("FAIM_TENANT_ID", "default"))
    parser.add_argument("--api-key", default=os.getenv("FAIM_API_KEY", ""))
    parser.add_argument("--graph-id", default=f"load-{int(time.time())}")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()

    if not args.api_key:
        raise SystemExit("FAIM_API_KEY is required; this probe never uses a bypass key implicitly")
    documents = []
    for path in args.files:
        payload = path.read_bytes()
        documents.append((path, payload, hashlib.sha256(payload).hexdigest()))

    def upload(item):
        path, payload, source_hash = item
        started = time.perf_counter()
        body = json.dumps(
            {
                "graph_id": args.graph_id,
                "filename": path.name,
                "content_type": "application/pdf" if path.suffix.lower() == ".pdf" else "text/plain",
                "profile": "strict",
                "persist_mode": "strict",
                "bytes_base64": __import__("base64").b64encode(payload).decode("ascii"),
            }
        ).encode("utf-8")
        result = _post(
            f"{args.base_url.rstrip('/')}/api/v1/ingest",
            body,
            {
                "Content-Type": "application/json",
                "X-Tenant-Id": args.tenant,
                "X-Api-Key": args.api_key,
            },
        )
        return {
            "file": str(path),
            "sha256": source_hash,
            "status": result.get("status"),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "nodes_written": result.get("nodes_written", 0),
            "error": result.get("error"),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        results = list(pool.map(upload, documents))
    latencies = sorted(float(row["latency_ms"]) for row in results)
    p95_index = min(len(latencies) - 1, max(0, int(round(len(latencies) * 0.95)) - 1))
    summary = {
        "graph_id": args.graph_id,
        "files": len(results),
        "workers": max(1, args.workers),
        "p50_ms": latencies[len(latencies) // 2] if latencies else 0,
        "p95_ms": latencies[p95_index] if latencies else 0,
        "results": results,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if all(row["status"] in {"completed", "dedup_hit"} for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
