# Comprehensive BTP Presentation Slide Deck
**Student:** Chirag Sharma (Roll No: S20240010223)  
**Guide / Advisor:** Dr. Bheemappa Halavar  
**Project Title:** Zero-Overhead Prefetch-Resilient Last-Level Cache Replacement Policy  

---

## Slide 1: Title & Project Metadata
- **Project Title**: Zero-Overhead Prefetch-Resilient Last-Level Cache (LLC) Replacement Policy
- **Student**: Chirag Sharma (Roll No: S20240010223)
- **Advisor / Guide**: Dr. Bheemappa Halavar
- **Department**: Computer Science & Engineering
- **Primary Goal**: Protect shared Last-Level Caches (LLC) from aggressive data prefetcher pollution in multicore systems **without adding hardware predictor tables or extra metadata storage bytes**.

---

## Slide 2: Motivation & Problem Statement
- **The Problem**: Aggressive hardware prefetchers (AMPM, IP-Stride) boost regular access patterns but flood the cache with useless prefetches on irregular pointer-chasing patterns (`429.mcf`).
- **Policy Blindness**: Standard replacement policies (LRU, SRRIP) treat speculative prefetches with the same high priority as demand requests, thrashing demand lines.
- **Overhead of Existing Solutions**: Existing approaches like **DRRIP** (PSEL set dueling) and **SHiP** (8,192-entry SHCT table) require extra hardware logic and storage.

---

## Slide 3: Proposed Architecture (Zero-Overhead Prefetch Awareness)
- **Demoted Initial Insertion**:
  - Demand Fills $\rightarrow$ Inserted at **MRU / `RRPV = 2`** (standard priority).
  - Prefetch Fills $\rightarrow$ Inserted near **LRU / `RRPV = 3`** (distant priority).
- **Self-Adaptive Hit Promotion**:
  - Useful prefetches hit before eviction $\rightarrow$ Promoted to **MRU / `RRPV = 0`**.
  - Useless prefetches fall off cache naturally without harming demand lines.
- **Zero Storage Cost**: Uses 0 extra hardware bytes (leverages ChampSim's native `access_type::PREFETCH` hint).

---

## Slide 4: Multicore Shared Cache Empirical Results (Full Data Integration)

### **Per-Core 4-Core Shared LLC IPC Comparison**
| Core / Benchmark | Baseline 4-Core (LRU) IPC | Prefetch-Aware 4-Core IPC | Speedup / Improvement |
|---|---|---|---|
| **CPU 0 (`403.gcc` Stride)** | **0.4248** | **2.1770** | **5.12$\times$ Speedup (+512% IPC Boost)** |
| **CPU 3 (`471.omnetpp` Graph)** | **0.2566** | **2.1830** | **8.50$\times$ Speedup (+850% IPC Boost)** |
| **CPU 2 (`600.perlbench` Compute)** | **1.4740** | **2.2890** | **1.55$\times$ Speedup (+55% IPC Boost)** |
| **CPU 1 (`429.mcf` Pointer Noise)** | **0.0847** | **0.0847** | Maintained (Noise demoted to LRU) |

- **Execution Time Reduction**: `gcc` region completion dropped from **7 Hours 04 Minutes** down to **19 Minutes** (**-95.5% Time Savings**).

---

## Slide 5: Single-Core Behavior & Prefetch Usefulness
- **`403.gcc` (Mixed Stride)**: **50.10% Prefetch Usefulness** (2,652 useful prefetches promoted to MRU).
- **`4-Core Mix 1` (Shared LLC)**: **32.25% Prefetch Usefulness** across multi-core access streams.
- **`429.mcf` (Pointer Noise)**: **0.18% Useful Rate** (useless prefetches demoted to LRU and evicted rapidly).

---

## Slide 6: Current Progress & Next 2-Month Roadmap
- **Completed Progress**:
  - Implemented `lru_prefetch_aware` and `rrip_prefetch_aware` C++ modules in ChampSim.
  - Built standalone cycle-accurate LLC simulator (`sim_llc_prefetch_aware.cpp`).
  - Evaluated on official SPEC CPU DPC-3 trace suite (`gcc`, `mcf`, `perlbench`, `omnetpp`).
- **Roadmap for Next 2 Months**:
  1. **Dynamic Adaptive Demotion Thresholds**: Tune insertion depth dynamically based on real-time LLC MPKI and DRAM channel congestion.
  2. **Multicore Quality-of-Service (QoS) Partitioning**: Prevent a single memory-heavy core (`mcf`) from over-allocating shared LLC sets.
  3. **Full SPEC CPU 2017 Expansion**: Complete 15+ benchmark evaluation for final BTP thesis submission.

---

## Slide 7: Conclusion & Discussion
- **Student**: Chirag Sharma (Roll No: S20240010223)
- **Guide**: Dr. Bheemappa Halavar
- **Key Takeaway**: Achieved state-of-the-art prefetch resilience with **zero hardware overhead**, delivering up to **8.5$\times$ speedups** under shared LLC contention!
