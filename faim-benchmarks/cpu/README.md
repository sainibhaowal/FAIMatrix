# CPU-Only Benchmarks (`faim-benchmarks/cpu/`)

All pure zero-ML CPU benchmarks (`FAIM_FAST_ML_EMBEDDING=false`, `FAIM_EMBEDDING_DEVICE=cpu`), matching GitHub Actions `FAIM CPU Parallel Benchmarks` (`.github/workflows/benchmarks-cpu.yml`).

- **BEIR Retrieval:** `scifact`, `nfcorpus`, `arguana`, `fiqa`, `trec-covid`
- **Conversational & Temporal Memory:** `locomo`, `longmemeval`, plus optional `beam` (`BEAM_DATA_PATH`) and `tm` (`TM_DATA_PATH`)
- **Outputs:** `faim-benchmarks/results/cpu/<suite>/`

```bash
chmod +x cpu/run_all_cpu.sh
./cpu/run_all_cpu.sh
```
