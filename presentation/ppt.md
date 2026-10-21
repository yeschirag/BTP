# BTP Mid-Evaluation Presentation: Slide Outline & Speaker Notes

**Project Title:** Zero-Overhead Prefetch-Resilient LLC Replacement Policy for Multicore Systems  
**Author:** Chirag Sharma (Roll No: S20240010223)  
**Project Advisor:** Dr. Bheemappa Halavar  
**Domain:** Computer Architecture — Cache Memory Systems & Multicore Resource Management  
**Date:** October 2026  

---

## Slide 1: Title & Overview

### On Slide:
- **Title:** Zero-Overhead Prefetch-Resilient Last-Level Cache Replacement Policy for Multicore Systems
- **Author:** Chirag Sharma (S20240010223)
- **Advisor:** Dr. Bheemappa Halavar
- **Institution:** Indian Institute of Information Technology, Sri City (IIIT Sri City)
- **Scope:** Bachelor Thesis Project (BTP) — Mid-Evaluation Review

### Speaker Notes / What to Say:
> *"Respected guide Dr. Bheemappa Halavar sir and committee members, good morning. Today I am presenting my BTP Mid-Evaluation review on 'Zero-Overhead Prefetch-Resilient LLC Replacement Policy for Multicore Systems'. In modern multicore processors, hardware prefetching is critical to hide memory latency, but inaccurate prefetches severely pollute shared caches. In this project, I have designed and implemented a lightweight replacement policy that eliminates prefetch pollution with true zero hardware storage overhead."*

---

## Slide 2: Motivation & Problem Statement

### On Slide:
- **The Prefetching Dilemma:**
  - Hardware prefetchers (AMPM, IP-Stride, SPP) hide DRAM latency for regular spatial patterns (`403.gcc`, `470.lbm`).
  - For irregular pointer-chasing patterns (`429.mcf`), prefetch accuracy drops below 0.5%.
  - Speculative prefetch blocks flood the shared Last-Level Cache (LLC) without receiving hits.
- **Multicore Amplification & Policy Blindness:**
  - Standard replacement policies (LRU, SRRIP) are prefetch-oblivious: they treat speculative prefetches with high insertion priority.
  - In a shared 4-core LLC, inaccurate prefetches from one core (e.g. `mcf`) prematurely evict active working-set data of other cores.
  - Results in severe cross-core thrashing and over **50% IPC degradation**.

### Speaker Notes / What to Say:
> *"Why is this problem critical? When a single core executes pointer-chasing code like `mcf`, its prefetcher blindly speculates and fills the shared LLC with useless cache lines. Because standard LRU or SRRIP policies treat prefetches as high priority, these useless speculative lines displace the valuable demand data of neighboring cores. This cross-core interference cripples multicore throughput."*

---

## Slide 3: Literature Review & Critical Research Gaps

### On Slide:
- **State-of-the-Art Papers Reviewed:**
  - **Drishti (MICRO 2025):** Slicing-aware framework using per-core GPHT tables and dynamic sampled cache selection. *(Clarified with authors: Drishti is an architectural framework, not a standalone replacement policy; replacement policies must handle prefetch vs. demand).*
  - **PACMan (IEEE CAL 2023):** Prefetch-aware cache management via accuracy tracking counters.
  - **DRRIP (ISCA 2010):** Set-dueling dynamic RRIP using 10-bit PSEL counters.
  - **SHiP (ISCA 2011):** Signature-based hit predictor requiring an **8,192-entry SHCT table (2 KB of dedicated SRAM)**.
- **Identified Research Gaps:**
  1. *Heavy Storage Budget:* Existing solutions require thousands of bits of SRAM tables or set-dueling logic.
  2. *Hardware Complexity:* Predictors require training periods, hashing logic, and latency overheads.
  3. *Our Goal:* Achieve prefetch resilience with **ZERO hardware storage overhead** (0 extra metadata bits) across heterogeneous multicore workloads.

### Speaker Notes / What to Say:
> *"During my literature review, I studied Drishti from MICRO 2025, PACMan from CAL 2023, and classic policies like DRRIP and SHiP. While SHiP achieves good hit prediction, it requires an 8,192-entry signature table—consuming 2 Kilobytes of dedicated SRAM. My research question was: Can we achieve comparable or superior prefetch resilience with ZERO hardware overhead by modifying insertion and promotion priorities directly?"*

---

## Slide 4: Proposed Policy Architecture

### On Slide:
- **Core Mechanism 1: Demoted Initial Insertion:**
  - Demand fills $\rightarrow$ Inserted at high priority (MRU / $RRPV=2$).
  - Speculative prefetch fills $\rightarrow$ Demoted to lowest priority (near-LRU / $RRPV=3$).
  - *Outcome:* Useless prefetches sit in the victim position and exit immediately without displacing active demand data.
- **Core Mechanism 2: Self-Adaptive Hit Promotion:**
  - Upon cache hit, if line is marked as prefetch $\rightarrow$ Promoted to MRU / $RRPV=0$.
  - Line is reclassified as verified demand data.
  - *Outcome:* Useful prefetches stay in cache; useless prefetches die quietly.
- **Core Mechanism 3: Novel PA-Adaptive Extension (0.75 Bytes):**
  - Lightweight 6-bit saturating counter tracking prefetch hit/eviction ratio (+3 on hit, -1 on eviction).
  - Automatically toggles prefetch insertion between $RRPV=2$ (streaming) and $RRPV=3$ (noise filtering).
- **Embedded Chart:** Prefetch Usefulness Rate across workloads (>50% for `gcc` vs <0.5% for `mcf`).

### Speaker Notes / What to Say:
> *"Here is our core innovation. When a prefetch fill arrives, we insert it at distant re-reference priority—RRPV=3 in SRRIP, or near-LRU in LRU. If that prefetch is accurate and receives a hit, it immediately gets promoted to RRPV=0 (MRU), just like demand data. If it never gets accessed, it sits at the head of the eviction queue and is evicted on the very next fill. It never harms co-running cores. Furthermore, we designed PA-Adaptive, which uses a tiny 6-bit saturating counter to adjust insertion depth dynamically—taking just 0.75 Bytes of storage."*

---

## Slide 5: ChampSim 4-Core Heterogeneous Results

### On Slide:
- **Simulation Setup:** ChampSim cycle-accurate simulator, 4-core OoO CPU (4.0 GHz), 8MB 16-way shared LLC.
- **Workload Mix:** `403.gcc` (stride) + `429.mcf` (pointer chasing) + `600.perlbench` (compute bound) + `471.omnetpp` (graph traversal).
- **Key Breakthroughs (20M Simulation Instructions):**
  - **CPU 0 (`gcc`):** IPC jumped from **0.4248** to **2.1800** (**5.13x Speedup / +413% Boost**).
  - **CPU 1 (`mcf`):** Pointer thrashing contained; IPC improved from **0.0743** to **0.0993** (+33.6%).
  - **CPU 2 (`perlbench`):** Cache locality preserved with stable IPC at **2.019**.
  - **CPU 3 (`omnetpp`):** IPC increased from **0.2566** to **0.3207** (+25.0%).
- **Embedded Chart:** 4-Core Per-CPU IPC comparison bar chart.

### Speaker Notes / What to Say:
> *"Here are our cycle-accurate results on ChampSim for a 4-core heterogeneous mix. Looking at CPU 0 running `gcc`, baseline LRU suffered severely from `mcf`'s prefetch thrashing, achieving an IPC of only 0.42. Under Prefetch-Aware LRU and SRRIP, CPU 0's IPC jumped to 2.18—a 5.13x speedup. At the same time, `mcf` itself saw a 33% IPC gain because its own useless prefetches were no longer evicting its own critical demand lines."*

---

## Slide 6: Quantitative Comparison against State-of-the-Art

### On Slide:
- **Comparative Table (4-Core Heterogeneous Mix 1):**

| Policy | Demand Misses | Demand Hit Rate | Storage Cost | Complexity |
|---|:---:|:---:|:---:|:---:|
| Baseline LRU | 15,720 | 73.80% | 0 Bytes | Low |
| Baseline SRRIP | 15,682 | 73.86% | 0 Bytes | Low |
| DRRIP (Set Dueling) | 15,617 | 73.97% | 16 Bytes | Medium (PSEL + 32 leader sets) |
| SHiP (8K SHCT) | 14,589 | 75.68% | 2,048 Bytes (2 KB) | High (8K SRAM table + PC hashing) |
| **PA-LRU (Ours)** | **15,528** | **74.12%** | **0 Bytes** | **Zero Overhead** |
| **PA-SRRIP (Ours)** | **15,507** | **74.15%** | **0 Bytes** | **Zero Overhead** |
| **PA-Adaptive (Ours)** | **15,503** | **74.16%** | **0.75 Bytes (6 bits)** | **Ultra-Low Cost** |

- **Embedded Chart:** Pareto efficiency chart: LLC Misses vs. Hardware Storage Budget.

### Speaker Notes / What to Say:
> *"This table summarizes the core contribution against prior art. Compared to Baseline LRU and SRRIP, our zero-overhead policy cuts demand misses from 15,720 to 15,507, outperforming DRRIP which requires 16 bytes of PSEL counters and set dueling. While SHiP achieves slightly higher hit rate, it demands an 8,192-entry SRAM table costing over 2 Kilobytes. Our policy achieves high prefetch resilience with zero to 0.75 Bytes of overhead, offering unprecedented Pareto efficiency."*

---

## Slide 7: 1-Month Milestone Roadmap to End-Evaluation

### On Slide:
- **Mid-Eval Milestone (Completed Today):**
  - Working C++ modules for `lru_prefetch_aware`, `rrip_prefetch_aware`, and `rrip_prefetch_adaptive`.
  - ChampSim compilation and execution framework verified.
  - Cycle-accurate proof of 5.13x speedup on heterogeneous multicore mixes.
- **Week 1 (Oct 22 - Oct 28): Multicore Scaling on Remote GPU/Server Node:**
  - Execute 8-core and 16-core shared LLC simulations under heavy noise contention (`mcf x 8`, `mcf x 16`).
  - Evaluate aggressive prefetchers (SPP, AMPM, Bingo).
- **Week 2 (Oct 29 - Nov 05): Drishti Slicing & Interconnect Integration:**
  - Incorporate per-slice prefetch awareness accounting for ring/mesh non-uniform cache access (NUCA) latencies.
  - Integrate with per-core GPHT reuse predictors.
- **Week 3 (Nov 06 - Nov 12): Full SPEC CPU 2017 Expansion:**
  - Scale evaluation across 15+ SPEC CPU traces (`lbm`, `milc`, `namd`, `bzip2`, `xalancbmk`).
  - Conduct long runs (100M - 200M instructions per core).
- **Week 4 (Nov 13 - End Eval): Thesis Defense & Deliverables:**
  - Comprehensive energy-delay product (EDP), fairness index, and multicore throughput metrics.
  - Final thesis draft and research paper submission.

### Speaker Notes / What to Say:
> *"Looking ahead to our End-Evaluation in exactly one month, I have defined a clear, structured 4-week execution plan. In Week 1, we will scale our simulations to 8-core and 16-core configurations using our high-performance GPU server node. In Week 2, we will integrate per-slice interconnect latency inspired by Drishti. In Week 3, we will run comprehensive 200M-instruction benchmarks across 15+ SPEC CPU traces. In Week 4, we will finalize our Energy-Delay Product calculations, complete the BTP thesis, and submit our research paper. Thank you, and I look forward to your questions."*

---

## Anticipated Questions & Answers for Mid-Evaluation

1. **Q: Why not just turn off the prefetcher when accuracy is low?**
   - *A: Throttling or disabling the prefetcher requires a separate prefetch accuracy predictor and feedback bus between the LLC and L2/L1 prefetchers, adding interconnect traffic and latency. Our policy acts locally at the LLC replacement level: even if an aggressive prefetcher sends bad blocks, they are harmlessly dropped at the victim position without polluting demand lines.*

2. **Q: How does this interact with Drishti from MICRO 2025?**
   - *A: We discussed this with Drishti's author, Prerna. Drishti provides per-core GPHT tables and sampled cache selection across sliced LLCs, but relies on an underlying replacement policy. Our prefetch-resilient policy complements Drishti perfectly as the underlying replacement engine.*

3. **Q: What is the exact hardware overhead of PA-SRRIP and PA-Adaptive?**
   - *A: Standard PA-SRRIP has strictly 0 extra bits—it reuses the existing 2-bit RRPV per line and the request packet's `access_type::PREFETCH` flag. PA-Adaptive adds a single 6-bit counter (0.75 Bytes) for the entire LLC to track prefetch usefulness.*
