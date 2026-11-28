# Technical Evaluation Report: Prefetch-Aware Last-Level Cache Replacement under Speculative Multicore Interference

**Author:** Chirag Sharma (`S20240010223`)  
**Supervisor:** Dr. Bheemappa Halavar, Department of CSE, IIIT Sri City  
**Repository Provenance:** Git commit `a341cc5` (evaluation host `iiitsgpu`, 48-core x86_64)  
**Target Domain:** High-Performance Computer Architecture — Shared Last-Level Cache (LLC) Management, Speculative Pollution Mitigation, and Replacement Policy Co-Design

---

## 1. Executive Technical Summary

Modern multicore processors pair private per-core L2 hardware prefetchers (e.g., `ip_stride`, `va_ampm_lite`) with a large shared non-inclusive Last-Level Cache (LLC). When compute-bound or regular-stride applications co-execute with irregular, pointer-chasing workloads (e.g., `429.mcf`), prefetch-oblivious LLC replacement policies (`LRU`, `SRRIP`) allocate speculative prefetch fills at high retention priority, displacing active demand working sets and degrading co-runner throughput and system fairness.

This work implements, verifies, and evaluates three prefetch-aware LLC replacement policies inside cycle-accurate **ChampSim**:
1. **`PA-LRU` ([src/lru_prefetch_aware.cc](file:///Users/yeschirag/Desktop/college/btp/src/lru_prefetch_aware.cc)):** Inserts `access_type::PREFETCH` fills at near-victim priority (`min_cycle_in_set + 1`) while retaining MRU (`cycle++`) for demand fills and hit promotions.
2. **`PA-SRRIP` ([src/rrip_prefetch_aware.cc](file:///Users/yeschirag/Desktop/college/btp/src/rrip_prefetch_aware.cc)):** Exploits the existing 2-bit Re-Reference Prediction Value (`RRPV`, $M=2$) in SRRIP caches to insert `PREFETCH` fills at `RRPV = 3` (immediate eviction candidate) and `DEMAND` fills at `RRPV = 2`, promoting lines to `RRPV = 0` on demand hits—requiring **strictly 0 bits of additional hardware storage** for eviction/insertion logic.
3. **`PA-Adaptive` ([src/rrip_prefetch_adaptive.cc](file:///Users/yeschirag/Desktop/college/btp/src/rrip_prefetch_adaptive.cc)):** Augments `PA-SRRIP` with a closed-loop 6-bit saturating confidence counter ($C \in [0, 63]$, initialized at `32`) updated asymmetrically (`+3` on useful prefetch hit, `-1` on un-promoted prefetch eviction) to toggle prefetch insertion between `RRPV = 2` ($C \ge 32$) and `RRPV = 3` ($C < 32$).

Critically, unlike prior ad-hoc reports, this evaluation enforces **strictly matched prefetcher grids** (`va_ampm_lite` and `ip_stride` isolated separately across **8 policies**: `LRU`, `SRRIP`, `DRRIP`, `SHiP`, `PACMan-HM`, `PA-LRU`, `PA-SRRIP`, `PA-Adaptive`), includes standalone 1-core `IPC_alone` baselines for true **Weighted Speedup** and **Harmonic Fairness**, includes a **prefetcher-OFF equivalence control**, and decouples intrinsic L2 prefetcher accuracy from circular policy-dependent promotion rates.

---

## 2. Simulated Microarchitecture & Experimental Methodology

### 2.1 System Configuration (ChampSim Out-of-Order Model)
All matched configurations are generated deterministically via [scripts/generate_grid_configs.py](file:///Users/yeschirag/Desktop/college/btp/scripts/generate_grid_configs.py) from the shared baseline machine description (`configs/champsim_4core_pa_rrip.json`):

| Subsystem | Architectural Parameters |
|:---|:---|
| **Processor Cores** | 4 OoO cores @ 4.0 GHz; 6-wide fetch/decode/dispatch, 4-wide execute, 5-wide retire; 352-entry ROB, 128-entry LQ, 72-entry SQ, 128-entry scheduler |
| **Front-End & TLB** | `bimodal` branch predictor, `basic_btb`, DIB (32×8); ITLB/DTLB (16×4, 1 cyc), STLB (128×12, 8 cyc) |
| **Private Caches** | L1I: 32 KB (64×8, 4 cyc, `no` PF); L1D: 48 KB (64×12, 5 cyc, `no` PF); L2C: 512 KB (1024×8, 10 cyc, matched **`va_ampm_lite`** or **`ip_stride`**) |
| **Shared LLC (Evaluated)** | **8 MB** (8,192 sets × 16 ways × 64B blocks), non-inclusive/non-exclusive, 20-cycle hit latency, 64 MSHRs, `max_tag_check=1`, `max_fill=1` |
| **Main Memory (DRAM)** | 1 channel, 1 rank, 8 bankgroups, 4 banks/bg, DDR4-3200 (`tCAS=24, tRCD=24, tRP=24, tRAS=52`) |
| **Simulation Window** | `1,000,000` warmup instructions + `5,000,000` simulation instructions per core (`git a341cc5` via [scripts/run_iiitsgpu_grid.sh](file:///Users/yeschirag/Desktop/college/btp/scripts/run_iiitsgpu_grid.sh)) |

### 2.2 Benchmark Traces & Workload Mixes
Traces are SPEC CPU2006/2017 SimPoint slices:
- `403.gcc-16B` (Compute/mixed regular strides; high cache sensitivity to eviction bursts)
- `429.mcf-184B` (Combinatorial network simplex; pointer chasing with high DRAM miss-latency pressure)
- `600.perlbench_s-210B` (Interpreter control/hash workload; predominantly L1/L2 resident)
- `471.omnetpp-188B` (Discrete-event simulator; irregular heap walks sensitive to shared LLC capacity)

Evaluated mixes:
- **`mix1_het`:** `gcc + mcf + perlbench + omnetpp` (4-core heterogeneous contention)
- **`mix2_mcf4`:** `mcf × 4` (symmetric bandwidth & pointer-chasing stress)
- **`alone` (1-core):** Each benchmark executed solo on an identical 8 MB LLC configuration (`num_cores=1`) to obtain `IPC_alone` without inter-core interference.

### 2.3 Quantitative Evaluation Metrics
To prevent skewed arithmetic reporting across heterogeneous IPC magnitudes:
1. **True Weighted Speedup (`WS`):**
   $$\text{WS} = \frac{1}{N} \sum_{i=0}^{N-1} \frac{\text{IPC}_{\text{shared}, i}}{\text{IPC}_{\text{alone}, i}}$$
2. **Harmonic Mean Speedup (`HS` — Fairness-Sensitive Throughput):**
   $$\text{HS} = \frac{N}{\sum_{i=0}^{N-1} \frac{\text{IPC}_{\text{alone}, i}}{\text{IPC}_{\text{shared}, i}}}$$
3. **Mean Normalized IPC vs. Shared LRU:** $\frac{1}{N}\sum_{i=0}^{N-1}\left(\frac{\text{IPC}_{\text{pol},i}}{\text{IPC}_{\text{LRU},i}}\right) - 1$.
4. **Independent LLC Demand Misses:** Sum of `LOAD` and `RFO` misses across all 4 cores (`cpu*->LLC LOAD/RFO MISS`), excluding speculative prefetch and writeback traffic.
5. **Decoupled L2 Prefetcher Accuracy:** $\frac{\sum \text{L2C\_PF\_USEFUL}}{\sum (\text{L2C\_PF\_USEFUL} + \text{L2C\_PF\_USELESS})}$, avoiding the circularity of policy-dependent `Prefetch Promoted / Prefetch Fills` telemetry.

---

## 3. Algorithmic Formulations, Prior Art & Hardware Cost Audit

### 3.1 ChampSim Hook Semantics & Writeback Guard Finding
ChampSim invokes three callbacks via `CACHE::replacement_module_model` ([ChampSim/inc/cache.h:439-520](file:///Users/yeschirag/Desktop/college/btp/ChampSim/inc/cache.h#L439-L520)):
1. `find_victim(...)` during `CACHE::fill_cache_line` when all 16 ways are valid.
2. `replacement_cache_fill(...)` immediately prior to overwriting the victim block, passing `fill.type`.
3. `update_replacement_state(...)` in `CACHE::try_hit` for **both** hits and misses (`way_idx == NUM_WAY` on miss).

**Prefetcher-OFF Equivalence Check Diagnosis (`ctrl_nopf_srrip` vs. `ctrl_nopf_pa_rrip`):**  
With L2 prefetchers disabled (`prefetcher = "no"`), `ctrl_nopf_pa_rrip` yields **1,148,368** LLC demand misses vs. **1,149,732** for stock ChampSim `srrip` (`0.12%` delta). Inspection of [ChampSim/replacement/srrip/srrip.cc:24-46](file:///Users/yeschirag/Desktop/college/btp/ChampSim/replacement/srrip/srrip.cc#L24-L46) and [ChampSim/inc/cache.h:515](file:///Users/yeschirag/Desktop/college/btp/ChampSim/inc/cache.h#L515) shows the exact cause: ChampSim's stock `srrip` does not implement `replacement_cache_fill` and lacks an `access_type != access_type::WRITE` guard in `update_replacement_state`, thereby promoting dirty L2 writeback hits to `RRPV = 0`. Both `drrip.cc` (`line 39`), `ship.cc` (`line 86`), `pacman.cc`, and our `rrip_prefetch_aware.cc` explicitly exclude `WRITE` writeback hits, accounting cleanly for the `0.12%` difference.

### 3.2 Structural Comparison with State-of-the-Art (SOTA)

| Policy | Prefetch Fill Priority | Hit Promotion Rule | Adaptive Mechanism | Extra Storage (8 MB LLC = 131,072 lines) |
|:---|:---|:---|:---|:---|
| **Baseline LRU** | MRU (`cycle++`) | Any hit $\rightarrow$ MRU | None | `0 B` (vs LRU baseline) |
| **Baseline SRRIP** (ISCA'10) | `RRPV = 2` | Any hit $\rightarrow$ `RRPV = 0` | None | `0 B` (reuses 2-bit RRPV) |
| **DRRIP** (ISCA'10) | `2` (SRRIP) or `{3,2}` 31:1 (BRRIP) | `type != WRITE` $\rightarrow$ `0` | 32+32 Set-Dueling + 10b `PSEL` | **`~16 B`** (PSEL + leader IDs) |
| **SHiP** (ISCA'11) | `RRPV = 3` if `SHCT[sig]==max` else `2` | `type != WRITE` $\rightarrow$ `0`; train sampler | PC-signature `SHCT` (2-bit × 8,192) + sampler sets | **`2,048 B` (2 KB)** + sampler tags |
| **PACMan-HM** (MICRO'11) | `PREFETCH` $\rightarrow$ `3`; Demand $\rightarrow$ `2` | **`type != PREFETCH && != WRITE`** $\rightarrow$ `0` | None (`PACMan-Dyn` adds Set Dueling `PSEL`) | **`0 B`** (`~16 B` for Dyn) |
| **PA-LRU (Ours)** | `PREFETCH` $\rightarrow$ `*min_it + 1`; Demand $\rightarrow$ `cycle++` | `type != WRITE` $\rightarrow$ `cycle++` | None | **`0 B`** (telemetry flag unused by policy) |
| **PA-SRRIP (Ours)** | `PREFETCH` $\rightarrow$ `3`; Demand $\rightarrow$ `2` | `type != WRITE` $\rightarrow$ `0` | None | **`0 B`** *(telemetry-only `is_prefetched`)* |
| **PA-Adaptive (Ours)** | `C >= 32 ? 2 : 3` for `PREFETCH` | `type != WRITE` $\rightarrow$ `0`; `+3` if PF | 6b global saturating counter (`+3 / -1`) | **`0.75 B`** *(if reusing 1b/line PMU flag)* / **`16 KB + 0.75 B`** *(standalone)* |

**Crucial Storage Audit (Full Silicon Honesty):**
- In **`PA-SRRIP`**, `std::vector<bool> is_prefetched` exists solely to print `prefetch_promoted` in `replacement_final_stats()`. Neither `find_victim()` nor `rrpv` reads it—thus `PA-SRRIP` genuinely incurs **0 extra SRAM bits**.
- In **`PA-Adaptive`**, `find_victim()` (`line 26`) and `update_replacement_state()` (`line 66`) **actively read `is_prefetched[index]`** to distinguish un-promoted prefetch evictions from demand evictions. Across 131,072 lines, a standalone 1-bit/line array requires **`16,384 Bytes (16 KB)`**, which is **8× larger than SHiP's 2 KB `SHCT`**. Therefore, `PA-Adaptive` is storage-competitive **only** when hardware already maintains a per-line `prefetched` metadata bit for PMU telemetry (`CACHE::BLOCK::prefetch` in ChampSim).
- **Relation to PACMan (Wu et al., MICRO 2011):** `PACMan-M` inserts hardware prefetch fills at distant `RRPV = 3` while leaving demand-hit promotion unchanged; `PACMan-HM` additionally suppresses promotion on prefetch hits (`type == PREFETCH`); and `PACMan-Dyn` adds 32-set Set Dueling (`PSEL`). **`PA-SRRIP` is functionally identical to `PACMan-M`**—we evaluate it under controlled multicore contention alongside `PACMan-HM`, audit exact silicon storage, and test a global asymmetric `+3/-1` adaptive controller (`PA-Adaptive`) instead of set dueling.

---

## 4. Matched Empirical Results (`iiitsgpu`, `git a341cc5`)

### 4.1 Grid A: `L2C Prefetcher = va_ampm_lite`
*Standalone `IPC_alone` (`1-core LRU, 8 MB LLC`): `gcc = 2.0740`, `mcf = 0.1094`, `perlbench = 1.8680`, `omnetpp = 0.3490`.*

#### Mix 1: Heterogeneous Workload (`gcc + mcf + perlbench + omnetpp`)
| Policy | `gcc` (CPU0) | `mcf` (CPU1) | `perlbench` (CPU2) | `omnetpp` (CPU3) | Mean Norm vs LRU | Weighted Speedup | Harmonic Speedup | LLC Demand Misses | L2 PF Acc (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline LRU | 2.0600 | 0.0881 | 1.8340 | 0.2895 | +0.00% | 0.9025 | 0.8943 | 1,208,550 | 26.89% |
| Baseline SRRIP | 2.0340 | 0.0956 | 1.8330 | 0.2770 | +0.73% | 0.9074 | 0.9003 | 1,124,384 | 27.13% |
| DRRIP (ISCA'10) | 2.0580 | 0.0901 | 1.8340 | 0.2899 | +0.58% | 0.9071 | 0.9001 | 1,185,074 | 26.99% |
| SHiP (ISCA'11) | 2.0540 | 0.0986 | 1.8360 | 0.3157 | **+5.19%** | **0.9447** | **0.9429** | **1,066,144** | 27.19% |
| PACMan-HM (MICRO'11) | 2.0460 | 0.0951 | 1.8330 | 0.2917 | +1.99% | 0.9182 | 0.9133 | 1,109,056 | 27.00% |
| PA-LRU (Ours) | 2.0500 | 0.0896 | 1.8340 | 0.2928 | +0.59% | 0.9071 | 0.9003 | 1,190,366 | 27.04% |
| **PA-SRRIP (Ours)** | 2.0420 | 0.0952 | 1.8320 | 0.2923 | **+2.00%** | **0.9182** | **0.9135** | **1,109,658** | 26.91% |
| **PA-Adaptive (Ours)** | 2.0470 | 0.0951 | 1.8310 | 0.2921 | **+2.01%** | **0.9183** | **0.9135** | **1,110,610** | 26.95% |

#### Mix 2: Pointer-Chasing Contention Stress (`mcf × 4`)
| Policy | Avg IPC (CPU0–3) | Mean Norm vs LRU | Weighted Speedup | Harmonic Speedup | LLC Demand Misses | L2 PF Acc (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline LRU | 0.0743 | +0.00% | 0.6796 | 0.6796 | 3,045,362 | 28.91% |
| Baseline SRRIP | 0.0793 | +6.66% | 0.7248 | 0.7248 | 2,834,660 | 28.82% |
| DRRIP (ISCA'10) | 0.0806 | +8.41% | 0.7367 | 0.7367 | 2,854,058 | 28.98% |
| SHiP (ISCA'11) | **0.0855** | **+14.98%** | **0.7814** | **0.7814** | **2,623,182** | 28.88% |
| PACMan-HM (MICRO'11) | 0.0782 | +5.11% | 0.7143 | 0.7143 | 2,863,414 | 28.87% |
| PA-LRU (Ours) | 0.0744 | +0.03% | 0.6798 | 0.6798 | 3,047,436 | 28.92% |
| PA-SRRIP (Ours) | 0.0782 | +5.11% | 0.7143 | 0.7143 | 2,862,338 | 28.90% |
| PA-Adaptive (Ours) | 0.0782 | +5.13% | 0.7144 | 0.7144 | 2,861,418 | 28.90% |

### 4.2 Grid B: `L2C Prefetcher = ip_stride`
*Standalone `IPC_alone` (`1-core LRU, 8 MB LLC`): `gcc = 2.0320`, `mcf = 0.1092`, `perlbench = 1.8590`, `omnetpp = 0.3393`.*

#### Mix 1: Heterogeneous Workload (`gcc + mcf + perlbench + omnetpp`)
| Policy | `gcc` (CPU0) | `mcf` (CPU1) | `perlbench` (CPU2) | `omnetpp` (CPU3) | Mean Norm vs LRU | Weighted Speedup | Harmonic Speedup | LLC Demand Misses | L2 PF Acc (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline LRU | 2.0100 | 0.0895 | 1.8200 | 0.2811 | +0.00% | 0.9041 | 0.8970 | 1,224,826 | 30.62% |
| Baseline SRRIP | 1.9990 | 0.0963 | 1.8240 | 0.2710 | +0.91% | 0.9113 | 0.9046 | 1,147,114 | 31.40% |
| DRRIP (ISCA'10) | 2.0060 | 0.0914 | 1.8200 | 0.2823 | +0.58% | 0.9087 | 0.9026 | 1,204,426 | 30.32% |
| SHiP (ISCA'11) | 2.0150 | 0.0994 | 1.8260 | 0.3057 | **+5.10%** | **0.9463** | **0.9446** | **1,088,776** | 30.80% |
| PACMan-HM (MICRO'11) | 2.0090 | 0.0953 | 1.8210 | 0.2814 | +1.66% | 0.9177 | 0.9125 | 1,141,878 | 30.59% |
| PA-LRU (Ours) | 2.0070 | 0.0896 | 1.8210 | 0.2811 | -0.01% | 0.9040 | 0.8969 | 1,223,036 | 30.94% |
| **PA-SRRIP (Ours)** | 2.0090 | 0.0951 | 1.8210 | 0.2816 | +1.60% | 0.9172 | 0.9121 | 1,143,828 | 30.61% |
| **PA-Adaptive (Ours)** | 2.0080 | 0.0953 | 1.8210 | 0.2816 | **+1.65%** | **0.9176** | **0.9125** | **1,142,268** | 30.67% |

#### Mix 2: Pointer-Chasing Contention Stress (`mcf × 4`)
| Policy | Avg IPC (CPU0–3) | Mean Norm vs LRU | Weighted Speedup | Harmonic Speedup | LLC Demand Misses | L2 PF Acc (%) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| Baseline LRU | 0.0744 | +0.00% | 0.6806 | 0.6806 | 3,083,478 | 32.31% |
| Baseline SRRIP | 0.0794 | +6.89% | 0.7275 | 0.7275 | 2,860,892 | 31.79% |
| DRRIP (ISCA'10) | 0.0808 | +8.67% | 0.7396 | 0.7396 | 2,884,322 | 32.02% |
| SHiP (ISCA'11) | **0.0857** | **+15.35%** | **0.7851** | **0.7851** | **2,647,162** | 31.87% |
| PACMan-HM (MICRO'11) | 0.0781 | +5.07% | 0.7151 | 0.7151 | 2,896,238 | 32.22% |
| PA-LRU (Ours) | 0.0743 | -0.08% | 0.6800 | 0.6800 | 3,084,510 | 31.88% |
| PA-SRRIP (Ours) | 0.0781 | +5.07% | 0.7151 | 0.7151 | 2,896,968 | 31.77% |
| PA-Adaptive (Ours) | 0.0781 | +5.08% | 0.7152 | 0.7152 | 2,896,792 | 32.27% |

---

## 5. Longitudinal & Historical Experimental Results (Complete Project Progression)

In addition to the canonical matched `a341cc5` grid (Section 4), this repository preserves earlier single-core, 20M/200M ChampSim, and synthetic micro-trace evaluations conducted during policy development. These are documented below with explicit provenance and methodological notes so an external evaluator can inspect the complete progression without hidden or dropped runs.

### 5.1 Long-Window Single-Core ChampSim Baselines (`ChampSim/results_overnight/`, `10M warmup / 200M sim`)
Executed to verify zero single-core IPC regression and quantify intrinsic LLC prefetch reuse across extreme access patterns:

| Log File | Policy | Sim IPC | LLC Prefetch Fills | Useful Promoted | Residual LLC Promotion (%) |
|:---|:---|---:|---:|---:|---:|
| `1core_gcc_baseline.txt` | Baseline LRU | 2.1830 | — | — | — |
| `1core_gcc_pa_lru.txt` | PA-LRU | **2.1830** (0.0%) | 5,293 | 2,652 | **50.10%** |
| `1core_mcf_baseline.txt` | Baseline LRU | 0.1001 | — | — | — |
| `1core_mcf_pa_lru.txt` | PA-LRU | **0.1001** (0.0%) | 19,124 | 6 | **0.03%** |

*Observation:* Over a 200M-instruction window on an isolated core, `PA-LRU` introduces zero IPC regression on either regular (`gcc`) or irregular (`mcf`) traces while confirming a >1,600× disparity in residual LLC prefetch reuse (`50.10%` vs `0.03%`).

### 5.2 Earlier 20M/200M Heterogeneous & Initial `iiitsgpu` Runs (Pre-Matched Configs)
Earlier 4-core sweeps paired `champsim_4core_baseline.json` (**L2 `ip_stride`**) against `PA-LRU` / `PA-SRRIP` / `PA-Adaptive` configured with **L2 `va_ampm_lite`**. Those numbers are preserved below alongside their exact confound tags (superseded by Section 4's strictly matched grids):

| Dataset / Log | Warmup / Sim | Policy (L2 PF) | `gcc` (CPU0) | `mcf` (CPU1) | `perl` (CPU2) | `omnet` (CPU3) | LLC PF Fills / Promoted (%) |
|:---|:---:|:---|---:|---:|---:|---:|:---|
| `results_overnight/4core_mix_baseline.txt` | 10M / 200M | LRU (`ip_stride`) | 2.1750 | 0.0798 | 2.0400 | 0.2654 | — |
| `results_fast/4core_mix_pa_lru_fast.txt` | 1M / 20M | PA-LRU (`va_ampm_lite`) | 2.1800 | 0.0906 | 2.0190 | 0.3145 | 503,157 / 10,607 (2.11%) |
| `results_fast/4core_mix_pa_rrip_fast.txt` | 1M / 20M | PA-SRRIP (`va_ampm_lite`) | 2.1790 | 0.0993 | 2.0180 | 0.3207 | 426,336 / 10,116 (2.37%) |
| `results_fast/4core_mcf4_pa_rrip_fast.txt` | 1M / 20M | PA-SRRIP (`va_ampm_lite`) | 0.0848 | 0.0848 | 0.0850 | 0.0847 | 115,044 / 810 (0.70%) |
| `results_remote/4core_mix_baseline.txt` | 1M / 20M | LRU (`ip_stride`) | 2.1450 | 0.0809 | 2.2650 | 0.2274 | — |
| `results_remote/4core_mix_pa_rrip.txt` | 1M / 20M | PA-SRRIP (`va_ampm_lite`) | 2.1760 | 0.0994 | 1.9760 | 0.3170 | 418,134 / 12,123 (2.90%) |
| `results_remote/4core_mix_pa_adaptive.txt` | 1M / 20M | PA-Adaptive (`va_ampm_lite`) | 2.1760 | 0.0994 | 1.9760 | 0.3171 | 418,462 / 12,656 (3.02%) |
| `results_remote/4core_mcf4_pa_rrip.txt` | 1M / 20M | PA-SRRIP (`va_ampm_lite`) | 0.0849 | 0.0850 | 0.0847 | 0.0849 | 115,098 / 742 (0.64%) |
| `results_remote/4core_mcf4_pa_adaptive.txt` | 1M / 20M | PA-Adaptive (`va_ampm_lite`) | 0.0849 | 0.0850 | 0.0847 | 0.0849 | 114,318 / 1,023 (0.89%) |

*Why Section 4 Supersedes Section 5.2:* Comparing `ip_stride` baseline (`2.2650 / 0.2274`) against `va_ampm_lite` `PA-SRRIP` (`1.9760 / 0.3170`) conflated replacement effects with prefetcher aggressiveness (producing an apparent `+39.4%` `omnetpp` jump alongside a `-12.8%` `perlbench` drop). Section 4 isolates both prefetchers cleanly and proves `perlbench` stays flat (`1.832` vs `1.834`). Notice also that on `20M` `mcf x 4`, `PA-Adaptive` retained `+37.9%` more promoted blocks (`1,023` vs `742`) at identical IPC (`0.0849`).

### 5.3 Early Prototype Verification Logs (`results/`, Feb 2026)
- **1-Core `mcf` (`2M warmup / 10M sim`):** `1core_baseline_mcf.txt` = `0.0813` IPC vs `1core_prefetch_aware_mcf.txt` = `0.0813` IPC (`538` PF fills, `1` useful = `0.19%`).
- **4-Core `gcc+mcf+perl+gcc` (`1M warmup / 5M sim`):** `4core_baseline_mix1.txt` (`1.9700 / 0.0847 / 2.0270 / 1.9850`) vs `4core_prefetch_aware_mix1.txt` (`1.9710 / 0.0847 / 2.0270 / 1.9850`; `6,475` PF fills, `2,088` useful = `32.25%`).

### 5.4 Standalone Synthetic Multi-Policy Micro-Trace Suite (`src/run_multi_eval_suite.cpp` / `./run_eval`)
A standalone single-level C++ cache model (16-way sets, synthetic stride/pointer-chasing streams) evaluating all 8 replacement policies under controlled synthetic interference:

| Policy | Mix 1 (`gcc+mcf+perl+omnet`, 128×16) Demand Misses | Mix 1 Hit Rate | Mix 2 (`mcf × 4`, 1×16) Demand Misses | Mix 2 Hit Rate |
|:---|---:|---:|---:|---:|
| Baseline LRU | 15,720 | 73.80% | 59,572 | 0.713% |
| Baseline SRRIP | 15,682 | 73.86% | 59,592 | 0.680% |
| DRRIP (Set Dueling) | 15,617 | 73.97% | **59,092** | **1.513%** |
| SHiP | **14,589** | **75.68%** | 59,542 | 0.763% |
| PACMan-HM (MICRO'11) | 15,501 | 74.16% | 59,303 | 1.161% |
| Prefetch-Aware LRU | 15,528 | 74.12% | 59,327 | 1.121% |
| Prefetch-Aware SRRIP | 15,507 | 74.15% | 59,302 | 1.163% |
| PA-Adaptive SRRIP | 15,503 | 74.16% | 59,302 | 1.163% |

*(Across synthetic `1-Core gcc` [192 misses], `1-Core perlbench` [14 misses], `1-Core lbm` [3 misses], `1-Core omnetpp` [196 misses], and `4-Core gcc x 4` [256 misses], all 8 policies tie identically, confirming zero degradation on regular/compute workloads.)*

---

## 6. Deep Microarchitectural Diagnosis & Synthesis

1. **Zero-SRAM Heterogeneous Contention Recovery (`mix1_het`):**  
   In both matched prefetcher configurations, unguarded stock `Baseline SRRIP` boosts `mcf` (`0.0881 -> 0.0956`) relative to `LRU`, while reducing `omnetpp` IPC (`0.2895 -> 0.2770` under `va_ampm_lite`; `0.2811 -> 0.2710` under `ip_stride`). Under `PA-SRRIP` ($\equiv$ `PACMan-M`), **`omnetpp` recovers to LRU-equivalent throughput (`0.2923` vs `0.2895`)** while retaining `mcf`'s gain (`0.0952`), raising Weighted Speedup to **`0.9182`** (**`+1.74%`** vs `LRU`, **`+1.19%`** vs unguarded `SRRIP`) and Harmonic Fairness to **`0.9135`** (**`+2.15%`** vs `LRU`, **`+1.47%`** vs `SRRIP`) at **0 extra SRAM bits**. Notice **`PA-SRRIP` (`1,109,658` misses) ties `PACMan-HM` (`1,109,056` misses, within `0.05%`)**, and `perlbench` remains flat (`1.832` vs `1.834`), confirming the earlier `-12.8%` drop was an artifact of prefetcher mismatch.

2. **Homogeneous Pointer-Chasing Inversion (`mix2_mcf4`):**  
   Under `mcf × 4`, both `PA-SRRIP` and `PACMan-HM` (`WS 0.7143`, `2,862,338` misses) **trail** `Baseline SRRIP` (`0.7248`, `2,834,660` misses) and `DRRIP` (`0.7367`). Independent L2C hardware telemetry shows `mcf`'s L2 prefetcher achieves **`28.9%–32.3%` accuracy**. Under 4-way symmetric contention, this is **consistent with** unconditional `RRPV = 3` quarantine evicting timely `mcf` prefetches before LLC reuse (+28K misses vs `SRRIP`). Also note that **miss counts do not map one-to-one to IPC**: `DRRIP` incurs *more* demand misses than `SRRIP` on `mcf × 4` (`2,854,058` vs `2,834,660`) yet achieves higher IPC (`0.0806` vs `0.0793`) due to memory-level parallelism and demand criticality differences.

3. **Collapse of `PA-Adaptive` Toward Static Filtering (`PA-SRRIP`):**  
   Across all 4 grid scenarios, `PA-Adaptive` yields virtually identical IPC to `PA-SRRIP` (`0.9183` vs `0.9182`, `0.7144` vs `0.7143`). *Plausible Explanation (Subject to Counter Instrumentation):* Although L2 prefetcher accuracy is `27–32%`, private L2 absorbs most timely hits before LLC lookup, and residual LLC promotion rate measured *under `RRPV=3` quarantine* is ~$2\text{--}3\%$ (note: this $p_{\text{hit,LLC}}$ metric is partly circular since `RRPV=3` shortens lifetime). Under a `+3/-1` LLC-only update rule, expected drift $\mathbb{E}[\Delta C] = 3(0.03) - 0.97 < 0$ is **predicted** to stay below threshold `32` (`Filtering Mode`). Instrumented telemetry (`scripts/run_validation_patch.sh`) directly logs `Final Counter` and `% Streaming Mode` to replace this prediction with measurement.

4. **Scoped Frontier Positioning (Zero-SRAM vs. `SHiP` `2 KB`):**  
   At `2,048 B+` SRAM overhead, `SHiP` dominates (`WS 0.9447 / 0.9463` on `mix1_het`, `0.7814 / 0.7851` on `mix2_mcf4`). **`PA-SRRIP` reproduces the zero-SRAM prefetch-demotion point (`PACMan-M`)**, tying `PACMan-HM` (within `0.05%` on misses) with gains limited to heterogeneous mixes, while conceding both symmetric contention (`DRRIP` / `SRRIP`) and unconstrained SRAM regimes (`SHiP`).

5. **`PA-LRU` Shortcomings:**  
   `PA-LRU` trails `PA-SRRIP` (`0.9071` vs `0.9182` on `va_ampm_lite`; `0.9040` vs `0.9172` on `ip_stride`), **likely because** `LRU` lacks an intermediate insertion point (`RRPV = 2`) and suffers rapid eviction churn near `*min_it + 1`.

---

## 7. Explicit Limitations, Methodology Validity & Future Directions

### 7.1 Threats to Validity & Limitations
- **Short Simulation Horizon:** `1M` warmup + `5M` simulation instructions per core is short relative to an 8 MB (`131,072`-line) LLC; small deltas (`0.7%–2.0%`) require `50M–100M` runs to confirm steady-state stability.
- **Limited Breadth:** Only 2 mixes (`mix1_het`, `mix2_mcf4`), 1 SimPoint slice per SPEC benchmark, and 1 machine configuration.
- **Writeback-Guard Confound in Stock `SRRIP`:** Stock ChampSim `srrip.cc` omits the `type != WRITE` guard present in `DRRIP`, `SHiP`, `PACMan-HM`, and `PA-SRRIP` (`0.12%` miss delta in `nopf`). `src/srrip_guarded.{h,cc}` + `scripts/run_validation_patch.sh` directly eliminate this confound.
- **Zero Measured Benefit from `PA-Adaptive`:** `PA-Adaptive` adds essentially zero IPC delta over static `PA-SRRIP` while requiring `1-bit/line` tracking (`16 KB` standalone unless reusing a PMU bit).

### 7.2 Future Directions
1. **Cross-Level L2→LLC Utility Hinting:** Forward L2 `pf_useful` feedback into `PA-Adaptive` so symmetric `mcf × 4` remains in `RRPV = 2` rather than filtering out useful ~30%-accurate prefetches.
2. **Evaluate `PACMan-Dyn` (Set-Dueling + Wire Filtering):** Benchmark set-dueling (`PSEL`) prefetch adaptation directly alongside `DRRIP` across heterogeneous and symmetric mixes.
3. **Longer SimPoints & Dead-Block Demand Filters:** Validate across `50M–100M` windows on broader SPEC mixes (`lbm`, `milc`, `cactusBSSN`).
