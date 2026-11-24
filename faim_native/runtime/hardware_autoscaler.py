"""Hardware-aware worker and GPU batch autoscaler for FAIM.

Detects host CPU threads, total/available host RAM, and NVIDIA GPU VRAM, then
computes an OOM-safe worker plan (`FAIM_API_WORKERS`, `FAIM_INGEST_WORKERS`,
`FAIM_EMBEDDING_BATCH_SIZE`, `FAIM_MIN_CUDA_FREE_MIB`, `INGEST_WORKERS`) for
both CPU-only deployments (e.g. 4 vCPU / 12 GB VPS) and GPU workstations.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Optional

DemandLevel = Literal["low", "balanced", "max"]


@dataclass(frozen=True)
class HardwareSnapshot:
    """Detected host CPU, RAM, and GPU capacity."""

    cpu_count: int
    ram_total_mib: int
    ram_available_mib: int
    gpu_name: Optional[str] = None
    gpu_vram_total_mib: int = 0
    gpu_vram_free_mib: int = 0


@dataclass(frozen=True)
class WorkerPlan:
    """Computed OOM-safe worker and batching configuration."""

    mode: Literal["native", "hybrid"]
    demand: DemandLevel
    api_workers: int
    ingest_workers: int
    bench_ingest_workers: int
    embedding_batch_size: int
    min_cuda_free_mib: int
    estimated_ram_mib: int
    estimated_vram_mib: int
    limited_by: str


def _read_proc_meminfo() -> tuple[int, int]:
    """Return (MemTotal MiB, MemAvailable MiB) from /proc/meminfo."""
    total_kib = 0
    avail_kib = 0
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                total_kib = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                avail_kib = int(line.split()[1])
    total_mib = max(1024, total_kib // 1024) if total_kib else 8192
    avail_mib = max(512, avail_kib // 1024) if avail_kib else total_mib // 2
    return total_mib, avail_mib


def _probe_nvidia_gpu() -> tuple[Optional[str], int, int]:
    """Return (gpu_name, total_vram_mib, free_vram_mib) via nvidia-smi."""
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return None, 0, 0
    if not out:
        return None, 0, 0
    first = out.splitlines()[0].split(",")
    if len(first) < 3:
        return None, 0, 0
    name = first[0].strip()
    total_mib = int(float(first[1].strip()))
    free_mib = int(float(first[2].strip()))
    return name, total_mib, free_mib


def detect_hardware() -> HardwareSnapshot:
    """Inspect current host CPU, RAM, and GPU."""
    cpu_count = os.cpu_count() or 2
    ram_total_mib, ram_available_mib = _read_proc_meminfo()
    gpu_name, gpu_vram_total_mib, gpu_vram_free_mib = _probe_nvidia_gpu()
    return HardwareSnapshot(
        cpu_count=cpu_count,
        ram_total_mib=ram_total_mib,
        ram_available_mib=ram_available_mib,
        gpu_name=gpu_name,
        gpu_vram_total_mib=gpu_vram_total_mib,
        gpu_vram_free_mib=gpu_vram_free_mib,
    )


def compute_worker_plan(
    hw: HardwareSnapshot,
    *,
    fast_ml_embedding: bool = False,
    demand: DemandLevel = "max",
    vram_budget_mib: Optional[int] = None,
    max_total_workers: int = 18,
    min_total_workers: int = 2,
) -> WorkerPlan:
    """Compute OOM-safe API + ingest worker counts and CUDA batch size."""
    infra_ram_mib = 3072  # Postgres + Redis + Qdrant + OS headroom
    # Blend MemTotal headroom with MemAvailable so idle desktop cache does not
    # overly starve workers while still backing off under active memory pressure.
    safe_ram_ceiling = max(
        1024,
        min(
            hw.ram_total_mib - infra_ram_mib,
            max(hw.ram_available_mib + 2048, int(hw.ram_total_mib * 0.55)),
        ),
    )

    if fast_ml_embedding:
        mode: Literal["native", "hybrid"] = "hybrid"
        ram_per_worker_mib = 1350
        vram_per_worker_mib = 850
        has_gpu = hw.gpu_vram_free_mib > 0
        raw_vram_cap = vram_budget_mib or 5632  # default <= 5.50 GiB cap
        effective_vram_mib = (
            min(raw_vram_cap, max(0, hw.gpu_vram_free_mib - 256))
            if has_gpu
            else 0
        )
        max_by_ram = max(min_total_workers, safe_ram_ceiling // ram_per_worker_mib)
        max_by_cpu = max(min_total_workers, min(max_total_workers, hw.cpu_count))
        max_by_vram = (
            max(1, effective_vram_mib // vram_per_worker_mib)
            if has_gpu
            else max_by_cpu
        )
        hard_cap = min(max_total_workers, max_by_ram, max_by_cpu, max_by_vram)
        embedding_batch_size = 256 if effective_vram_mib >= 4096 else 128
        min_cuda_free_mib = 512 if has_gpu else 1024
    else:
        mode = "native"
        ram_per_worker_mib = 350
        vram_per_worker_mib = 0
        max_by_ram = max(min_total_workers, safe_ram_ceiling // ram_per_worker_mib)
        # On 4 vCPU, allow up to 6 lightweight workers; on 16+ threads allow up to 18.
        max_by_cpu = max(
            min_total_workers,
            min(max_total_workers, hw.cpu_count + (2 if hw.cpu_count <= 8 else 0)),
        )
        hard_cap = min(max_total_workers, max_by_ram, max_by_cpu)
        embedding_batch_size = 128
        min_cuda_free_mib = 1024

    hard_cap = max(min_total_workers, hard_cap)
    demand_scale = {"low": 0.4, "balanced": 0.7, "max": 1.0}[demand]
    target_total = max(min_total_workers, int(round(hard_cap * demand_scale)))

    # Split ~1/3 API workers (min 2 when >= 3 total), ~2/3 ingest workers.
    if target_total <= 2:
        api_workers, ingest_workers = 1, 1
    else:
        api_workers = max(2, min(6, target_total // 3))
        ingest_workers = max(1, target_total - api_workers)

    total_workers = api_workers + ingest_workers
    bench_ingest_workers = max(2, min(12, ingest_workers * 2 if mode == "native" else ingest_workers + 2))

    limiting = []
    if hard_cap == max_by_ram:
        limiting.append("host_ram")
    if fast_ml_embedding and hw.gpu_vram_free_mib > 0 and hard_cap == max_by_vram:
        limiting.append("gpu_vram")
    if hard_cap == max_by_cpu:
        limiting.append("cpu_threads")
    if hard_cap == max_total_workers:
        limiting.append("max_cap")

    return WorkerPlan(
        mode=mode,
        demand=demand,
        api_workers=api_workers,
        ingest_workers=ingest_workers,
        bench_ingest_workers=bench_ingest_workers,
        embedding_batch_size=embedding_batch_size,
        min_cuda_free_mib=min_cuda_free_mib,
        estimated_ram_mib=total_workers * ram_per_worker_mib,
        estimated_vram_mib=total_workers * vram_per_worker_mib if hw.gpu_vram_free_mib > 0 else 0,
        limited_by=",".join(limiting) or "demand",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="FAIM hardware autoscaler")
    parser.add_argument("--mode", choices=["native", "hybrid"], default="native")
    parser.add_argument("--demand", choices=["low", "balanced", "max"], default="max")
    parser.add_argument("--vram-budget-mib", type=int, default=5632)
    parser.add_argument("--max-workers", type=int, default=18)
    parser.add_argument("--format", choices=["json", "env"], default="json")
    args = parser.parse_args()

    hw = detect_hardware()
    plan = compute_worker_plan(
        hw,
        fast_ml_embedding=(args.mode == "hybrid"),
        demand=args.demand,
        vram_budget_mib=args.vram_budget_mib,
        max_total_workers=args.max_workers,
    )
    if args.format == "env":
        print(f"FAIM_API_WORKERS={plan.api_workers}")
        print(f"FAIM_INGEST_WORKERS={plan.ingest_workers}")
        print(f"INGEST_WORKERS={plan.bench_ingest_workers}")
        print(f"FAIM_EMBEDDING_BATCH_SIZE={plan.embedding_batch_size}")
        print(f"FAIM_MIN_CUDA_FREE_MIB={plan.min_cuda_free_mib}")
        print(f"FAIM_AUTOSCALE_LIMIT={plan.limited_by}")
    else:
        print(json.dumps({"hardware": asdict(hw), "plan": asdict(plan)}, indent=2))


if __name__ == "__main__":
    main()
