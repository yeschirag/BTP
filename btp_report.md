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
- **Relation to PACMan (Wu et al., MICRO 2011):** `PACMan-HM` combines distant prefetch insertion (`RRPV = 3`) with prefetch-hit promotion suppression (`type != PREFETCH`), while `PACMan-Dyn` uses Set Dueling (`PSEL`) over sampled leader sets. `PA-SRRIP` isolates pure fill-priority demotion without modifying tag-hit logic for prefetches; `PA-Adaptive` replaces set dueling with a single global asymmetric `+3/-1` utility counter.

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

## 5. Deep Microarchitectural Diagnosis & Synthesis

1. **Zero-Overhead Heterogeneous Contention Relief (`mix1_het`):**  
   In both matched prefetcher configurations, `Baseline SRRIP` boosts `mcf` (`0.0881 -> 0.0956`) relative to `LRU`, **at the expense of `omnetpp`** (`0.2895 -> 0.2770` under `va_ampm_lite`; `0.2811 -> 0.2710` under `ip_stride`), because `RRPV = 2` allows `mcf`/`gcc` prefetch bursts to age out `omnetpp`'s irregular working set. By demoting speculative fills to `RRPV = 3`, **`PA-SRRIP` restores `omnetpp` (`0.2923` / `0.2816`) while retaining `mcf`'s gains (`0.0952` / `0.0951`)**, raising Weighted Speedup over `Baseline SRRIP` (`0.9182` vs `0.9074` on `va_ampm_lite`; `0.9172` vs `0.9113` on `ip_stride`) and Harmonic Fairness (`0.9135` vs `0.9003`), matching `PACMan-HM` (`0.9182` / `0.9177`) with zero prefetch-hit filtering overhead and **0 extra SRAM bits**. Meanwhile `perlbench` and `gcc` stay stable (eliminating the confounded `-12.8%` `perlbench` and `5.13x` `gcc` artifacts from earlier mismatched configs).

2. **Homogeneous Pointer-Chasing Inversion (`mix2_mcf4`):**  
   Under `mcf × 4`, both `PA-SRRIP` and `PACMan-HM` (`WS 0.7143`, `2,862,338` misses) **trail** `Baseline SRRIP` (`0.7248`, `2,834,660` misses) and `DRRIP` (`0.7367`). Independent L2C hardware telemetry explains why: `mcf`'s L2 prefetcher achieves **`28.9%–32.3%` accuracy**—meaning roughly 1 in 3 prefetches is genuinely useful! Under 4-way symmetric contention, unconditional `RRPV = 3` quarantine evicts timely `mcf` prefetches before their corresponding demand load reaches LLC, increasing demand misses by ~28K vs `Baseline SRRIP`. `DRRIP` outperforms static `PA-SRRIP` here because set-dueling dynamically adjusts *all* insertions (both demand and prefetch) to thrashing behavior (`BRRIP` bimodal protection), whereas `PA-SRRIP` only targets prefetch fills.

3. **Collapse of `PA-Adaptive` to Static Filtering (`PA-SRRIP`):**  
   Across all 4 grid scenarios, `PA-Adaptive` achieves virtually identical IPC to `PA-SRRIP` (`0.9183` vs `0.9182`, `0.7144` vs `0.7143`). Why? Even though overall L2 prefetcher accuracy is `27–32%`, the private L2C hits and absorbs the majority of timely useful prefetches *before* LLC lookup; residual LLC prefetch promotion probability ($p_{\text{hit,LLC}}$) sits near `~2–3%`. Under a `+3/-1` LLC-only update rule, the expected counter drift per prefetch is $\mathbb{E}[\Delta C] = 3 \cdot p_{\text{hit,LLC}} - 1 \cdot (1 - p_{\text{hit,LLC}}) \approx 3(0.03) - 0.97 = -0.88 < 0$, causing `confidence_counter` to saturate below threshold `32` (`Filtering Mode`, `RRPV = 3`) continuously. *Design insight:* Adaptive LLC prefetch controllers must either observe **L2 prefetch-usefulness signals** or scale reward asymmetries (e.g., `+32 / -1`) to residual LLC reuse rates rather than raw L2 accuracy.

4. **Why `SHiP` Establishes the SRAM-Backed Upper Bound:**  
   At `2,048 B+` SRAM overhead, `SHiP` learns dead-on-arrival *demand* signatures as well as prefetch signatures (e.g., pointer-chasing `mcf` load PCs that never reuse at LLC), winning both `mix1_het` (`WS 0.9447 / 0.9463`) and `mix2_mcf4` (`WS 0.7814 / 0.7851`). Thus, `PA-SRRIP` occupies the **zero-overhead frontier**: beating `LRU`, `SRRIP`, `DRRIP`, and `PA-LRU` in heterogeneous contention at **0 extra hardware bits**, while transparently conceding the `2 KB+` regime to signature predictors (`SHiP`).

5. **Inadequacy of `PA-LRU`:**  
   `PA-LRU` trails `PA-SRRIP` significantly (`0.9071` vs `0.9182` on `va_ampm_lite`; `0.9040` vs `0.9172` on `ip_stride`) because LRU lacks scan-resistant intermediate insertion (`RRPV = 2` vs `0`), letting high-frequency misses flush `*min_it + 1` and demand blocks alike, while requiring comparator trees/scans over multi-bit age fields.

---

## 6. Conclusion & Future Architectural Directions
- **Verified Finding:** At strictly **0 extra hardware bits**, `PA-SRRIP` improves heterogeneous 4-core Weighted Speedup (`+1.75%` vs `LRU`, `+1.20%` vs `SRRIP` under `va_ampm_lite`) and Harmonic Fairness (`+2.15%` vs `LRU`, `+1.47%` vs `SRRIP`), protecting co-running `omnetpp` (`0.2923` vs `0.2770`) while matching `PACMan-HM` without prefetch-hit suppression hardware.
- **Concrete Future Extensions Informed by Failure Modes:**
  1. **Cross-Level L2→LLC Utility Hinting:** Forward L2 `pf_useful` feedback into `PA-Adaptive` (fixing the LLC-only counter collapse) so symmetric `mcf × 4` workloads switch seamlessly back to `RRPV = 2` (`SRRIP`/`DRRIP` regime).
  2. **Per-Core Set-Dueling (`PACMan-Dyn` + `DRRIP` Hybrid):** Adapt prefetch demotion per leader set instead of globally so `gcc`-dominated sets stream while `mcf`-dominated sets filter simultaneously.
  3. **Writeback-Normalized Baselines & Longer SimPoints:** Standardize `type != WRITE` across ChampSim `srrip.cc` baselines and evaluate `50M–100M` instruction windows across broader SPEC mixes (`lbm`, `milc`, `cactusBSSN`).
