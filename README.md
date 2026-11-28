# Prefetch-Aware LLC Replacement Policies for Multicore Processors

**Bachelor Thesis Project (BTP)**  
**Student:** Chirag Sharma (`S20240010223`)  
**Supervisor:** Dr. Bheemappa Halavar, Dept. of CSE, IIIT Sri City  
**Provenance:** Matched ChampSim Grid (`git a341cc5` on `iiitsgpu`, 1M warmup / 5M sim)  

---

## Executive Summary

In shared non-inclusive Last-Level Caches (8 MB, 16-way), aggressive L2 hardware prefetchers (`va_ampm_lite`, `ip_stride`) cause severe co-runner displacement when irregular workloads (`429.mcf`) execute alongside latency-sensitive applications (`471.omnetpp`, `403.gcc`). Standard replacement policies (`LRU`, `SRRIP`) are prefetch-oblivious and allocate speculative fills at high retention priority.

This repository implements and evaluates three prefetch-aware replacement policies in cycle-accurate **ChampSim**, alongside matched SOTA baselines (`SRRIP`, `DRRIP`, `SHiP`, `PACMan-HM`):
1. **`PA-LRU` ([src/lru_prefetch_aware.cc](src/lru_prefetch_aware.cc)):** Inserts prefetch fills near LRU (`*min_it + 1`) and promotes on demand/prefetch hit (`cycle++`).
2. **`PA-SRRIP` ([src/rrip_prefetch_aware.cc](src/rrip_prefetch_aware.cc)):** Exploits existing 2-bit `RRPV` counters to demote `PREFETCH` fills to `RRPV = 3` (immediate victim) and `DEMAND` fills to `RRPV = 2`, promoting hits (`type != WRITE`) to `RRPV = 0` with **strictly 0 extra SRAM bits**.
3. **`PA-Adaptive` ([src/rrip_prefetch_adaptive.cc](src/rrip_prefetch_adaptive.cc)):** Adds a closed-loop 6-bit saturating confidence counter (`+3` on useful PF hit, `-1` on unused PF eviction) switching prefetch insertion between `RRPV = 2` and `RRPV = 3` (*Note: requires reusing a 1-bit/line PMU `prefetch` flag; otherwise standalone tracking costs 16 KB*).

---

## Verified Matched Grid Results (`iiitsgpu`, `git a341cc5`)

All 8 replacement policies were run under **identical L2C prefetchers** (`va_ampm_lite` and `ip_stride`) with 1-core `IPC_alone` references for true Weighted Speedup and Harmonic Fairness. See **[btp_report.md](btp_report.md)** for full tables and root-cause microarchitectural diagnosis.

### 4-Core Heterogeneous Mix (`gcc + mcf + perlbench + omnetpp`, `va_ampm_lite`)
| Policy | `gcc` | `mcf` | `perlbench` | `omnetpp` | Weighted Speedup | Harmonic Speedup | LLC Demand Misses | Extra Storage |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| Baseline LRU | 2.0600 | 0.0881 | 1.8340 | 0.2895 | 0.9025 | 0.8943 | 1,208,550 | 0 B |
| Baseline SRRIP (Stock) | 2.0340 | 0.0956 | 1.8330 | 0.2770 | 0.9074 | 0.9003 | 1,124,384 | 0 B |
| **Baseline SRRIP-G (Guarded)** | 2.0530 | 0.0936 | 1.8320 | 0.2889 | 0.9134 | 0.9076 | 1,128,330 | 0 B |
| DRRIP | 2.0580 | 0.0901 | 1.8340 | 0.2899 | 0.9071 | 0.9001 | 1,185,074 | ~16 B |
| PACMan-HM | 2.0460 | 0.0951 | 1.8330 | 0.2917 | 0.9182 | 0.9133 | 1,109,056 | 0 B |
| **PA-SRRIP (Ours ≡ PACMan-M)** | 2.0420 | **0.0952** | 1.8320 | **0.2923** | **0.9182** | **0.9135** | **1,109,658** | **0 B (Strictly)** |
| **PA-Adaptive (Ours)** | 2.0470 | **0.0951** | 1.8310 | **0.2921** | **0.9183** | **0.9135** | **1,110,610** | 0.75 B* / 16 KB |
| SHiP (ISCA'11) | 2.0540 | 0.0986 | 1.8360 | 0.3157 | 0.9447 | 0.9429 | 1,066,144 | 2,048 B + sampler |

- **Zero-SRAM Frontier (`PA-SRRIP` $\equiv$ `PACMan-M`):** Over a fair writeback-guarded `SRRIP-G` baseline, `PA-SRRIP` preserves a genuine **`+0.53%`** Weighted Speedup (`-18,672` misses) under `va_ampm_lite`, whereas under `ip_stride` (`0.9172` vs `0.9167`, `+0.06%`) the writeback guard accounted for the apparent stock-SRRIP gap. Prefetcher-OFF `srrip_guarded` matches `PA-SRRIP` bit-for-bit (`1,148,368 == 1,148,368` misses). (`SHiP` leads unconstrained at `2,048 B+` SRAM.)
- **Confirmed `PA-Adaptive` Collapse & `mcf x 4` Failure Mode:** Logged telemetry measures `Final Counter = 0/63` (`6.5%–7.0%` Streaming Mode under `va_ampm_lite`; `1.0%–13.9%` under `ip_stride`), confirming `86%–99%` of fills hit `RRPV = 3` Filtering Mode. On `mcf x 4`, L2 prefetcher accuracy is `28.9%–32.3%`, so unconditional `RRPV = 3` demotion (`0.7143`) trails `SRRIP` (`0.7248`) and `DRRIP` (`0.7367`).

---

## Repository Structure

```text
btp/
├── btp_report.md                     # Deep microarchitectural technical report & audit
├── src/                              # Custom replacement policies & synthetic eval suite
│   ├── lru_prefetch_aware.{h,cc}
│   ├── rrip_prefetch_aware.{h,cc}
│   ├── rrip_prefetch_adaptive.{h,cc}
│   ├── pacman.{h,cc}
│   └── run_multi_eval_suite.cpp      # Standalone 8-policy micro-trace testbench (./run_eval)
├── configs/grid/                     # 20 deterministic matched ChampSim JSON configs
├── scripts/
│   ├── generate_grid_configs.py      # Generates matched grids (va_ampm_lite, ip_stride, nopf, 1core)
│   ├── run_iiitsgpu_grid.sh          # Parallel ThreadPool runner with resume & provenance manifest
│   └── analyze_and_generate.py       # Single-source log parser (WS, HS, LLC misses, L2 Acc)
├── results/iiitsgpu_grid_a341cc5.json# Verified parsed metrics from iiitsgpu matched grid
├── presentation/
│   ├── BTP_Guide_Presentation.tex    # 11-slide ISCA/MICRO-style Beamer presentation
│   ├── BTP_Guide_Presentation.pdf
│   └── generate_btp_charts.py        # Generates charts directly from results JSON
└── ChampSim/                         # Cycle-accurate ChampSim simulator submodule
```
