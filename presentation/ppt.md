# BTP Mid-Review: Lightweight Prefetch-Resilient LLC Replacement Policy

**Student:** Chirag
**Advisor:** Dr. Bheemappa Halavar
**Date:** February 2026

---

## Slide 1: Title & Overview

### Lightweight Prefetch-Resilient LLC Replacement Policy for Multicore Systems

- **Domain:** Computer Architecture — Cache Memory Management
- **Focus:** Last-Level Cache (LLC) replacement under aggressive hardware prefetching
- **Core Idea:** Reduce prefetch pollution using low-priority insertion — zero hardware overhead
- **Simulator:** ChampSim (cycle-accurate multicore simulator)
- **Benchmarks:** SPEC CPU 2006/2017 traces (gcc, mcf, perlbench)

---

## Slide 2: Literature Review

### Paper 1: Drishti — MICRO 2025
**"Drishti: Do Not Forget Slicing While Designing Last-Level Cache Replacement Policies for Many-Core Systems"**

- Proposes **per-core Global Prediction History Table (GPHT)** for reuse prediction
- Introduces **Dynamic Sampled Cache Selection** — tests multiple policies on sample sets and picks the best
- **Key insight:** Modern LLCs are sliced; replacement policies must account for per-core behavior
- **Not a replacement policy itself** — works as a framework with underlying policies (Mockingjay, Hawkeye)
- **Gap identified:** Drishti does not explicitly distinguish prefetch vs. demand blocks; prefetch-awareness must come from the underlying replacement policy


### Paper 2: PACMan — IEEE Computer Architecture Letters, 2023
**"Prefetch-Aware Cache Management"**

- Explicitly addresses prefetch-demand interaction at LLC level
- Proposes tracking prefetch accuracy to modulate insertion/promotion policies
- Demonstrates that prefetch-oblivious policies leave significant performance on the table
- **Gap identified:** PACMan's accuracy tracking requires additional counters and sampling logic. There is no study of whether a simpler mechanism (e.g., insertion priority alone) can capture most of the benefit at zero overhead

### Summary of Gaps

| # | Gap | Source |
|---|-----|--------|
| 1 | No lightweight, zero-overhead prefetch-resilient LLC replacement design exists | PACMan |
| 2 | Drishti's framework does not handle prefetch type — needs underlying policy support | Drishti |
| 3 | PACMan's accuracy tracking adds hardware overhead; unclear if simpler insertion-only approach can achieve similar benefit | PACMan |
| 4 | Prefetch–replacement interaction is understudied in shared multicore LLCs with heterogeneous workloads | Drishti, PACMan |

---

## Slide 3: Problem Statement

### Problem

Aggressive hardware prefetching can **pollute the Last-Level Cache** by filling it with speculatively fetched blocks that are never accessed. In shared multicore LLCs, this pollution is amplified as multiple cores prefetch simultaneously, causing **eviction of useful demand data** and increasing miss rates.

Existing solutions either:
- **Ignore the problem** (standard LRU treats prefetch and demand equally)
- **Add significant hardware** (PACMan: accuracy counters and sampling logic; Drishti: GPHT tables + sampled cache selection)

There is a need for a **lightweight, zero-overhead mechanism** that can reduce prefetch pollution in shared LLCs without requiring additional hardware structures, training periods, or workload-specific tuning.

---

## Slide 4: Three Objectives

### Objective 1: Design a Zero-Overhead Prefetch-Aware LLC Replacement Policy

- Modify LRU insertion to differentiate **prefetch blocks** (low priority) from **demand blocks** (normal MRU priority)
- Promote prefetched blocks to MRU **only on hit** (proving they are useful)
- Achieve this using **only the existing `access_type` flag** — no new hardware tables or counters

### Objective 2: Evaluate Across Diverse Workload Types and Multicore Configurations

- Test on **compute-bound** (perlbench), **mixed** (gcc), and **memory-bound** (mcf) SPEC CPU traces
- Evaluate in both **single-core** and **4-core shared LLC** configurations
- Measure **IPC improvement**, **LLC MPKI**, and a new metric: **prefetch usefulness** (promoted prefetches / total prefetch fills)

### Objective 3: Characterize When Prefetch-Aware Insertion Is Effective vs. When It Is Not

- Quantify prefetch usefulness across workload types to understand when the policy helps
- Demonstrate **self-adaptive behavior** — the policy automatically adjusts based on whether prefetches receive cache hits
- Provide guidance on when lightweight prefetch-awareness suffices vs. when more complex policies (Drishti, PACMan) are needed

---

## Slide 5: Progress Achieved So Far

### Setup & Implementation — DONE

- ChampSim environment configured (WSL2) with baseline and prefetch-aware binaries (1-core & 4-core)

- Custom ChampSim replacement module: `lru_prefetch_aware` (lru_prefetch_aware.h, lru_prefetch_aware.cc)
- Three key functions implemented: `find_victim()`, `replacement_cache_fill()`, `update_replacement_state()`
- Prefetch usefulness tracking integrated into `replacement_final_stats()`

### Experiments Completed — 6 Experiments

**Single-Core Results:**

| Trace | Type | Baseline IPC | Prefetch-Aware IPC | Prefetch Usefulness |
|-------|------|-------------|-------------------|---------------------|
| perlbench | Compute-bound | 2.158 | 2.159 (+0.05%) | 0% — compute-bound, low LLC traffic |
| **gcc** | **Mixed** | **1.967** | **2.180 (+10.8%)** | **50.1%** — useful prefetches promoted |
| **mcf** | **Memory-bound** | **0.0743** | **0.0906 (+21.9%)** | **0.2%** — pointer-chasing demoted to protect cache |

**4-Core Heterogeneous Mix (gcc + mcf + perlbench + omnetpp, 20M instructions):**

| Core | Trace | Type | PA-LRU IPC | PA-SRRIP IPC |
|------|-------|------|:----------:|:------------:|
| CPU 0 | `gcc` | Stride-friendly | **2.180** | **2.179** |
| CPU 1 | `mcf` | Memory-bound | **0.0906** | **0.0993** |
| CPU 2 | `perlbench` | Compute-bound | **2.019** | **2.018** |
| CPU 3 | `omnetpp` | Graph traversal | **0.3145** | **0.3207** |

**4-Core LLC Behavior & Statistics (20M Run):**
- **Useful Prefetches Promoted:** Up to **32.25%** usefulness in heterogeneous mixes.
- **Extreme Memory Stress (4×mcf):** Maintained stable IPC (~0.085) with prefetch demotions preventing cross-core thrashing.
- **Hardware Storage Overhead:** **0 extra bits** (uses existing metadata / access hints).

### Key Finding: Self-Adaptive Without Any Predictor

```
  gcc (stride-friendly)                mcf (pointer-chasing)
  ┌──────────────────┐                ┌──────────────────┐
  │ Prefetch arrives  │                │ Prefetch arrives  │
  │ → Insert LOW      │                │ → Insert LOW      │
  ├──────────────────┤                ├──────────────────┤
  │ Gets HIT (>35%)  │                │ No hits (<0.5%)  │
  │ → Promote to MRU │                │ → Stays near LRU │
  │ → STAYS in cache │                │ → EVICTED first  │
  └──────────────────┘                └──────────────────┘
  Result: IPC boost                   Result: Demand data protected
```

---

## Slide 6: Summary & Remaining Work

### What Has Been Achieved

| Milestone | Status |
|-----------|--------|
| Literature review (Drishti, PACMan) | Done |
| Problem formulation & objectives defined | Done |
| ChampSim environment setup | Done |
| Prefetch-Aware LRU implementation | Done |
| Single-core experiments (3 traces) | Done |
| 1-core long-run mcf (10M instructions) | Done |
| 4-core heterogeneous experiment | Done |

### Remaining Work for Full BTP

1. **Compare with DRRIP, SHiP, SRRIP** — evaluate if our zero-overhead approach captures most of their benefit
2. **More aggressive prefetchers** — test with SPP/AMPM at LLC level (higher prefetch traffic)
3. **Larger instruction windows** — 50M+ instruction runs for statistical confidence
4. **Adaptive insertion position** — explore lightweight counter to dynamically adjust prefetch insertion priority
5. **Drishti integration** — combine per-core reuse prediction with prefetch-aware insertion
6. **Final report and analysis**
