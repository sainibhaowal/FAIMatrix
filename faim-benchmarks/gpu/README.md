# GPU Benchmarks (`faim-benchmarks/gpu/`)

CUDA GPU benchmarks (`docker-compose.gpu.yml` + `FAIM_EMBEDDING_DEVICE=auto`):
- **Pure FAIM-Native GPU (`FAIM_FAST_ML_EMBEDDING=false`):** `VectorBank` + 256-dim CUDA matrix kernels + Concept-Expanded MaxSim
- **FAIM + Granite GPU Hybrid (`FAIM_FAST_ML_EMBEDDING=true`):** Adds `granite-embedding-97m-multilingual-r2` with proactive VRAM OOM guard (`FAIM_MIN_CUDA_FREE_MIB=1024`)
- **Outputs:** `faim-benchmarks/results/gpu/<suite>/`

```bash
chmod +x gpu/run_all_gpu.sh
./gpu/run_all_gpu.sh
```
