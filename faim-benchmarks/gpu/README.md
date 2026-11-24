# GPU Benchmarks (`faim-benchmarks/gpu/`)

CUDA GPU benchmarks (`docker-compose.yml` with `FAIM_CONTAINER_RUNTIME=nvidia` + `NVIDIA_VISIBLE_DEVICES=all` + `FAIM_EMBEDDING_DEVICE=auto` + `FAIM_MIN_CUDA_FREE_MIB=1024`):

1. **Pure FAIM-Native GPU (`native`, `FAIM_FAST_ML_EMBEDDING=false`):**
   - `FAIM_API_WORKERS=6`, `FAIM_INGEST_WORKERS=8`
   - CUDA `VectorBank` + 256-dim matrix kernels + Concept-Expanded MaxSim
2. **FAIM + Granite GPU Hybrid (`hybrid`, `FAIM_FAST_ML_EMBEDDING=true`):**
   - `FAIM_API_WORKERS=3`, `FAIM_INGEST_WORKERS=3` (fits comfortably inside 8 GB RTX 4060 VRAM, with `FAIM_MIN_CUDA_FREE_MIB=1024` automatic CPU fallback)
   - Adds `ibm-granite/granite-embedding-97m-multilingual-r2` dense semantic vectors on top of FAIM-Native

- **Outputs:** `faim-benchmarks/results/gpu/native/<suite>/` and `faim-benchmarks/results/gpu/granite-hybrid/<suite>/`

```bash
chmod +x gpu/run_all_gpu.sh
./gpu/run_all_gpu.sh native   # Pure FAIM-Native GPU only
./gpu/run_all_gpu.sh hybrid   # Granite GPU Hybrid only
./gpu/run_all_gpu.sh all      # Both + restores default stack
```
