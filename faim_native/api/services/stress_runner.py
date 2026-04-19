"""Progressive stress testing with REAL ingest operations.

Runs actual document ingestion under increasing concurrency to measure
real latency, throughput, and find saturation points.
"""

from __future__ import annotations

import time
import uuid
import threading
from dataclasses import dataclass
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session


@dataclass
class StressResult:
    """Single load level result."""
    concurrency: int
    document_count: int
    total_docs_ingested: int
    ingest_latency_p50_ms: float
    ingest_latency_p95_ms: float
    ingest_latency_p99_ms: float
    throughput_docs_per_sec: float
    total_duration_sec: float
    invariants_passed: bool
    error_count: int


@dataclass
class StressSuiteResult:
    """Complete stress test results."""
    job_id: str
    graph_id: str
    test_config: Dict[str, Any]
    duration_sec: float
    results: List[StressResult]
    saturation_point: Optional[int]


class StressRunner:
    """Execute REAL progressive load testing on FAIM."""

    def __init__(self, ctx: Any):
        self.ctx = ctx

    def run_stress_test(
        self,
        graph_id: str,
        max_concurrency: int = 10,
        document_count: int = 100,
        test_doc_size: str = "small",
    ) -> StressSuiteResult:
        """Run REAL progressive load test with actual ingest operations."""
        job_id = str(uuid.uuid4())
        start_time = time.monotonic()
        results: List[StressResult] = []

        # Generate test documents (real content)
        test_docs = {
            "small": self._generate_test_doc(size=1024),      # 1KB
            "medium": self._generate_test_doc(size=10240),    # 10KB
            "large": self._generate_test_doc(size=102400),    # 100KB
        }
        test_doc = test_docs.get(test_doc_size, test_docs["small"])

        # Progressive concurrency levels
        concurrency_levels = [1, 2, 5, min(10, max_concurrency)]

        for concurrency in concurrency_levels:
            result = self._run_concurrency_level(
                graph_id,
                concurrency,
                document_count,
                test_doc,
            )
            results.append(result)

        total_duration = time.monotonic() - start_time
        saturation_point = self._detect_saturation(results)

        return StressSuiteResult(
            job_id=job_id,
            graph_id=graph_id,
            test_config={
                "max_concurrency": max_concurrency,
                "document_count": document_count,
                "test_doc_size": test_doc_size,
            },
            duration_sec=total_duration,
            results=results,
            saturation_point=saturation_point,
        )

    def _run_concurrency_level(
        self,
        graph_id: str,
        concurrency: int,
        document_count: int,
        test_doc: str,
    ) -> StressResult:
        """Run REAL load test at a single concurrency level.

        Actually ingests documents using the real orchestration pipeline.
        """
        from orchestration.ingest_flow import ingest_packet_flow, FAIMProfile
        from core.invariants import check_all_invariants
        from perception.packetize import create_packet

        latencies: List[float] = []
        error_count = 0
        invariants_passed = True
        docs_ingested = 0

        start_time = time.monotonic()

        # Simulate concurrent ingestion by distributing docs across threads
        def ingest_worker(doc_batch: List[tuple]):
            nonlocal error_count, invariants_passed, docs_ingested

            for doc_id, content in doc_batch:
                try:
                    # Create real packet from content
                    packet = create_packet(
                        tenant_id=self.ctx.tenant_id,
                        graph_id=graph_id,
                        raw_bytes=content.encode("utf-8"),
                        filename=f"stress_test_{doc_id}.txt",
                        doc_type="text",
                    )

                    # REAL ingest using actual pipeline
                    ingest_start = time.monotonic()
                    result = ingest_packet_flow(
                        session=self.ctx.session,
                        tenant_id=self.ctx.tenant_id,
                        graph_id=graph_id,
                        packet=packet,
                        profile=FAIMProfile.STRICT,
                    )
                    ingest_duration = (time.monotonic() - ingest_start) * 1000  # ms

                    latencies.append(ingest_duration)
                    docs_ingested += 1

                    # Commit after each document to avoid long transactions
                    try:
                        self.ctx.session.commit()
                    except Exception:
                        self.ctx.session.rollback()

                    # Check invariants periodically
                    if docs_ingested % 10 == 0:
                        try:
                            check_all_invariants(
                                session=self.ctx.session,
                                graph_id=graph_id,
                            )
                        except Exception as inv_err:
                            invariants_passed = False

                except Exception as e:
                    error_count += 1
                    try:
                        self.ctx.session.rollback()
                    except:
                        pass

        # Distribute documents across worker threads
        docs_per_thread = max(1, document_count // concurrency)
        threads = []

        for thread_idx in range(concurrency):
            start_doc = thread_idx * docs_per_thread
            end_doc = start_doc + docs_per_thread if thread_idx < concurrency - 1 else document_count
            doc_batch = [
                (f"{thread_idx}_{i}", test_doc)
                for i in range(start_doc, end_doc)
            ]

            thread = threading.Thread(
                target=ingest_worker,
                args=(doc_batch,),
                daemon=False,
            )
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        total_duration = time.monotonic() - start_time

        # Calculate latency percentiles from REAL measurements
        if latencies:
            latencies.sort()
            p50 = latencies[int(len(latencies) * 0.50)]
            p95 = latencies[int(len(latencies) * 0.95)]
            p99 = latencies[int(len(latencies) * 0.99)]
        else:
            p50 = p95 = p99 = 0.0

        # REAL throughput from actual documents ingested
        throughput = docs_ingested / total_duration if total_duration > 0 else 0.0

        return StressResult(
            concurrency=concurrency,
            document_count=document_count,
            total_docs_ingested=docs_ingested,
            ingest_latency_p50_ms=p50,
            ingest_latency_p95_ms=p95,
            ingest_latency_p99_ms=p99,
            throughput_docs_per_sec=throughput,
            total_duration_sec=total_duration,
            invariants_passed=invariants_passed,
            error_count=error_count,
        )

    def _generate_test_doc(self, size: int) -> str:
        """Generate realistic test document (deterministic, not random)."""
        # Use Lorem Ipsum like text repeated to reach size
        base_text = (
            "The quick brown fox jumps over the lazy dog. "
            "FAIM is a deterministic memory graph engine that stores content as "
            "typed nodes connected by inheritance, opposition, semantic, and causal edges. "
            "Every operation is auditable, reproducible, and mathematically proven. "
        )

        # Repeat base text to reach target size
        repetitions = (size // len(base_text)) + 1
        text = (base_text * repetitions)[:size]
        return text

    def _detect_saturation(self, results: List[StressResult]) -> Optional[int]:
        """Detect concurrency level where throughput plateaus.

        Real saturation detection: when throughput increase drops below 10%.
        """
        if len(results) < 2:
            return None

        for i in range(1, len(results)):
            prev_throughput = results[i - 1].throughput_docs_per_sec
            curr_throughput = results[i].throughput_docs_per_sec

            if prev_throughput > 0:
                increase = (curr_throughput - prev_throughput) / prev_throughput
                if increase < 0.10:  # Less than 10% increase = saturation
                    return results[i - 1].concurrency

        return None

    def to_dict(self, result: StressSuiteResult) -> Dict[str, Any]:
        """Convert result to JSON-serializable dict."""
        return {
            "job_id": result.job_id,
            "graph_id": result.graph_id,
            "test_config": result.test_config,
            "duration_sec": result.duration_sec,
            "saturation_point": result.saturation_point,
            "results": [
                {
                    "concurrency": r.concurrency,
                    "document_count": r.document_count,
                    "total_docs_ingested": r.total_docs_ingested,
                    "ingest_latency_p50_ms": round(r.ingest_latency_p50_ms, 2),
                    "ingest_latency_p95_ms": round(r.ingest_latency_p95_ms, 2),
                    "ingest_latency_p99_ms": round(r.ingest_latency_p99_ms, 2),
                    "throughput_docs_per_sec": round(r.throughput_docs_per_sec, 2),
                    "total_duration_sec": round(r.total_duration_sec, 2),
                    "invariants_passed": r.invariants_passed,
                    "error_count": r.error_count,
                }
                for r in result.results
            ],
        }
