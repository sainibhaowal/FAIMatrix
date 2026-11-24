"""Unit tests for hardware-aware worker and VRAM autoscaling."""

from __future__ import annotations

from faim_native.runtime.hardware_autoscaler import (
    HardwareSnapshot,
    compute_worker_plan,
)


def test_vps_4_vcpu_12gb_ram_scales_by_demand() -> None:
    """4 vCPU / 12 GB VPS scales cleanly from low to max without OOM."""
    vps = HardwareSnapshot(
        cpu_count=4,
        ram_total_mib=12288,
        ram_available_mib=9216,
    )
    low = compute_worker_plan(vps, fast_ml_embedding=False, demand="low")
    high = compute_worker_plan(vps, fast_ml_embedding=False, demand="max")

    assert low.api_workers + low.ingest_workers < high.api_workers + high.ingest_workers
    assert high.api_workers + high.ingest_workers == 6
    assert high.estimated_ram_mib < 4096


def test_laptop_14gb_ram_rtx4060_hybrid_caps_under_5500mib_vram() -> None:
    """14 GB RAM + RTX 4060 (5.5 GB free VRAM) caps hybrid at 6 workers, batch 256."""
    laptop = HardwareSnapshot(
        cpu_count=32,
        ram_total_mib=14336,
        ram_available_mib=4096,
        gpu_name="NVIDIA GeForce RTX 4060 Laptop GPU",
        gpu_vram_total_mib=8188,
        gpu_vram_free_mib=5578,
    )
    plan = compute_worker_plan(
        laptop,
        fast_ml_embedding=True,
        demand="max",
        vram_budget_mib=5632,
        max_total_workers=18,
    )
    assert plan.api_workers == 2
    assert 3 <= plan.ingest_workers <= 4
    assert plan.estimated_vram_mib <= 5632
    assert plan.embedding_batch_size == 256
    assert plan.min_cuda_free_mib == 512


def test_laptop_32_threads_native_scales_up_to_18_workers() -> None:
    """32-thread / 14 GB host in lightweight native mode scales up to 16-18 workers."""
    laptop = HardwareSnapshot(
        cpu_count=32,
        ram_total_mib=14336,
        ram_available_mib=9216,
    )
    plan = compute_worker_plan(
        laptop,
        fast_ml_embedding=False,
        demand="max",
        max_total_workers=18,
    )
    assert 16 <= (plan.api_workers + plan.ingest_workers) <= 18
    assert plan.estimated_ram_mib <= 7000


def test_workstation_24gb_vram_64gb_ram_scales_to_18_gpu_workers() -> None:
    """Large GPU workstation scales hybrid workers up to the 18-worker cap."""
    ws = HardwareSnapshot(
        cpu_count=32,
        ram_total_mib=65536,
        ram_available_mib=55000,
        gpu_name="NVIDIA RTX 4090",
        gpu_vram_total_mib=24576,
        gpu_vram_free_mib=23000,
    )
    plan = compute_worker_plan(
        ws,
        fast_ml_embedding=True,
        demand="max",
        vram_budget_mib=20480,
        max_total_workers=18,
    )
    assert plan.api_workers + plan.ingest_workers == 18
    assert plan.embedding_batch_size == 256
