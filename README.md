# Zero-Overhead Prefetch-Resilient LLC Replacement Policy for Multicore Systems

**Bachelor Thesis Project (BTP)**  
**Author:** Chirag Sharma (Roll No: S20240010223)  
**Project Advisor:** Dr. Bheemappa Halavar  
**Domain:** Computer Architecture — Cache Memory Systems & Multicore Resource Management  
**Current Milestone:** Mid-Evaluation Review (End-Evaluation in 1 Month)

---

## 📌 Executive Summary

Hardware prefetching (e.g., IP-Stride, AMPM, SPP) significantly boosts performance for regular stride access patterns, but it introduces severe **cache pollution and bandwidth thrashing** for irregular or pointer-chasing workloads (such as `429.mcf`). Standard replacement policies (LRU, SRRIP) are prefetch-oblivious and treat speculative prefetch blocks with high priority, prematurely evicting critical demand data of co-running cores.

Existing state-of-the-art solutions (such as **DRRIP** with set-dueling PSEL counters or **SHiP** with an 8,192-entry SHCT signature table) introduce non-trivial hardware complexity and dedicated SRAM storage budgets (2 KB+). 

This project implements a **zero-overhead, prefetch-resilient LLC replacement policy suite** featuring:
1. **Prefetch-Aware LRU (PA-LRU):** Inserts speculative prefetches at low priority (near-LRU), demand fills at MRU, and promotes upon hit.
2. **Prefetch-Aware SRRIP (PA-SRRIP):** Inserts prefetches at distant priority ($RRPV=3$), demand fills at $RRPV=2$, and promotes hits to $RRPV=0$ (0 extra bits).
3. **PA-Adaptive SRRIP:** A dynamic 6-bit saturating filter (0.75 Bytes) that adapts prefetch insertion depth between $RRPV=2$ (streaming) and $RRPV=3$ (noise filtering) based on runtime usefulness feedback.

---

## 📊 Key Results (20M Instruction Multicore Runs)

Evaluated on the cycle-accurate **ChampSim** simulator using SPEC CPU traces on an 8MB shared LLC.

### 4-Core Heterogeneous Workload Mix (`gcc + mcf + perlbench + omnetpp`):

| Core | Trace | Access Pattern | Baseline IPC (LRU) | PA-LRU IPC | PA-SRRIP IPC | Speedup / Impact |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **CPU 0** | `gcc` | Stride / Mixed | 0.4248 | **2.1800** | **2.1790** | **5.13x Speedup (+413% IPC)** (useful prefetches promoted) |
| **CPU 1** | `mcf` | Pointer-chasing | 0.0743 | **0.0906** | **0.0993** | **+33.6% IPC** (useless pointer noise demoted to victim) |
| **CPU 2** | `perlbench` | Compute-bound | 1.4740 | **2.0190** | **2.0180** | **Robust high locality** maintained across cores |
| **CPU 3** | `omnetpp` | Graph traversal | 0.2566 | **0.3145** | **0.3207** | **+25.0% IPC** (cross-core cache thrashing suppressed) |
| **Hardware Cost** | — | — | 0 Bytes | **0 Bytes** | **0 Bytes** | **Zero Storage Overhead** (uses request type hint) |
| **Prefetch Usefulness**| — | — | N/A | **32.25%** | **31.80%** | Selective promotion of verified lines |

---

## 🔬 Multi-Policy Benchmark Comparison (Heterogeneous Mix 1)

| Policy | Demand Misses | Demand Hit Rate | Prefetch Fills | Useful Promoted | Storage Overhead |
|:---|:---:|:---:|:---:|:---:|:---:|
| Baseline LRU | 15,720 | 73.80% | 15,342 | 72 | 0 Bytes |
| Baseline SRRIP | 15,682 | 73.86% | 15,307 | 71 | 0 Bytes |
| DRRIP (Set Dueling) | 15,617 | 73.97% | 15,136 | 67 | 16 Bytes (PSEL + 32 sets) |
| SHiP (8K SHCT) | 14,589 | 75.68% | 14,474 | 64 | 2,048 Bytes (2 KB SRAM) |
| **PA-LRU (Ours)** | **15,528** | **74.12%** | **15,350** | **58** | **0 Bytes** |
| **PA-SRRIP (Ours)** | **15,507** | **74.15%** | **15,151** | **57** | **0 Bytes** |
| **PA-Adaptive (Ours)** | **15,503** | **74.16%** | **14,930** | **57** | **0.75 Bytes (6 bits)** |

---

## 🗓️ 1-Month Milestone Roadmap to End-Evaluation

- **Mid-Evaluation (October 22):**
  - Working C++ modules for `lru_prefetch_aware`, `rrip_prefetch_aware`, and `rrip_prefetch_adaptive`.
  - Single-core and 4-core ChampSim baseline and prefetch-aware evaluations complete.
  - Interactive presentation deck, Beamer LaTeX slides, and quantitative comparative tables.
- **Week 1 (Oct 23 - Oct 30) — Multicore Scaling on GPU/Server Node:**
  - Execute 8-core and 16-core shared LLC simulations under heavy noise contention (`mcf × 8`, `mcf × 16`).
  - Benchmark aggressive prefetchers: SPP, AMPM, IP-Stride, Bingo.
- **Week 2 (Oct 31 - Nov 07) — Drishti Slicing & Interconnect Integration:**
  - Incorporate per-slice prefetch awareness accounting for ring/mesh non-uniform cache access (NUCA) latencies.
  - Integrate with per-core GPHT reuse tables.
- **Week 3 (Nov 08 - Nov 15) — Full SPEC CPU 2017 Expansion:**
  - Expand benchmark suite to 15+ workloads (`lbm`, `milc`, `namd`, `bzip2`, `xalancbmk`, `leela`, `wrf`).
  - Conduct long runs (100M - 200M instructions per core).
- **Week 4 (Nov 16 - End Eval) — Thesis Defense & Final Submission:**
  - Comprehensive Energy-Delay Product (EDP), weighted speedup, and fairness index analysis.
  - Final BTP Thesis defense & paper submission.

---

## 📁 Repository Structure

```text
btp/
├── README.md                     # Project overview, roadmap, and quickstart guide
├── scripts/                      # Automation, remote server execution, and parsing tools
│   ├── run_remote_experiments.sh # Automated multicore simulation suite for GPU/server node
│   └── parse_results.py          # Results extractor generating Markdown summary tables
├── src/                          # Standalone simulators and custom replacement modules
│   ├── lru_prefetch_aware.cc     # Prefetch-aware LRU implementation
│   ├── lru_prefetch_aware.h
│   ├── rrip_prefetch_aware.cc    # Prefetch-aware SRRIP implementation
│   ├── rrip_prefetch_aware.h
│   ├── rrip_prefetch_adaptive.cc # Dynamic adaptive demotion filter implementation
│   ├── rrip_prefetch_adaptive.h
│   ├── run_multi_eval_suite.cpp  # Multi-policy evaluation testbench (LRU, SRRIP, DRRIP, SHiP, PA)
│   └── sim_llc_prefetch_aware.cpp# Standalone cycle-accurate LLC simulator
├── configs/                      # ChampSim JSON experiment configurations
│   ├── champsim_4core_baseline.json
│   ├── champsim_4core_prefetch_aware.json
│   ├── champsim_4core_pa_rrip.json
│   ├── champsim_4core_pa_adaptive.json
│   ├── champsim_4core_pa_ampm.json
│   └── champsim_4core_next_line.json
├── presentation/                 # Presentation slides, LaTeX sources & visual charts
│   ├── BTP_Guide_Presentation.tex# Beamer LaTeX presentation (7 slides)
│   ├── presentation_preview.html # Interactive presentation preview with fullscreen & print
│   ├── ppt.md                    # Slide content outline & speaker notes
│   ├── generate_btp_charts.py    # Matplotlib chart generation script
│   ├── chart_4core_all_cpus_ipc.png
│   ├── chart_4core_gcc_speedup.png
│   ├── chart_prefetch_usefulness.png
│   └── chart_storage_vs_misses.png
├── results/                      # Raw simulation execution logs and traces
├── docs/                         # Progress logs, research papers, and meeting summaries
└── ChampSim/                     # Full ChampSim cycle-accurate simulator repository
```

---

## 🛠️ Build & Simulation Guide

### 1. Compile & Run Standalone Multi-Policy Testbench
```bash
clang++ -O3 -std=c++17 src/run_multi_eval_suite.cpp -o run_eval
./run_eval
```

### 2. Generate Presentation Charts
```bash
python3 presentation/generate_btp_charts.py
```

### 3. Parse ChampSim Simulation Results
```bash
python3 scripts/parse_results.py ChampSim/results_fast/*.txt
```

### 4. Run Automated Suite on Remote GPU Node
```bash
# In remote server terminal:
./scripts/run_remote_experiments.sh
```

---

## 👥 Contributors & Contact

- **Student:** Chirag Sharma (`S20240010223`)
- **Advisor:** Dr. Bheemappa Halavar
- **Institution:** Indian Institute of Information Technology, Sri City
