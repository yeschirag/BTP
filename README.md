# Zero-Overhead Prefetch-Resilient LLC Replacement Policy for Multicore Systems

**Bachelor Thesis Project (BTP)**  
**Author:** Chirag Sharma (Roll No: S20240010223)  
**Project Advisor:** Dr. Bheemappa Halavar  
**Domain:** Computer Architecture — Cache Memory Systems & Multicore Resource Management

---

## 📌 Executive Summary

Hardware prefetching (e.g., IP-Stride, AMPM) significantly boosts performance for regular stride access patterns, but it introduces severe **cache pollution and bandwidth thrashing** for irregular or pointer-chasing workloads (such as `429.mcf`). Standard replacement policies (LRU, SRRIP) are prefetch-oblivious and treat speculative prefetch blocks with high priority, prematurely evicting critical demand data.

Existing state-of-the-art solutions (such as **DRRIP** with set-dueling PSEL counters or **SHiP** with an 8,192-entry SHCT signature table) introduce non-trivial hardware complexity and storage budgets. 

This project implements a **zero-overhead, prefetch-resilient LLC replacement policy** that:
1. **Inserts speculative prefetches at low priority** (near-LRU / $RRPV=3$).
2. **Inserts demand fills at high priority** (MRU / $RRPV=2$).
3. **Promotes useful prefetches to MRU** ($RRPV=0$) upon first cache hit.
4. Requires **0 extra storage bits** by leveraging standard cache pipeline request hints.

---

## 📊 Key Results (20M Instruction Runs)

Evaluated on the cycle-accurate **ChampSim** simulator using SPEC CPU traces on an 8MB shared LLC.

### 4-Core Heterogeneous Workload Mix (`gcc + mcf + perlbench + omnetpp`):

| Core | Trace | Access Pattern | Baseline IPC (LRU) | PA-LRU IPC (20M) | PA-SRRIP IPC (20M) | Speedup / Impact |
|:---|:---|:---|:---:|:---:|:---:|:---|
| **CPU 0** | `gcc` | Stride / Mixed | 1.9670 | **2.1800** | **2.1790** | **+10.8% IPC** (useful prefetches promoted) |
| **CPU 1** | `mcf` | Pointer-chasing | 0.0743 | **0.0906** | **0.0993** | **+21.9% IPC** (useless prefetches evicted quickly) |
| **CPU 2** | `perlbench` | Compute-bound | 2.0150 | **2.0190** | **2.0180** | Robust, high locality maintained |
| **CPU 3** | `omnetpp` | Graph traversal | 0.2566 | **0.3145** | **0.3207** | **+22.6% IPC** under PA-SRRIP |
| **Hardware Overhead** | — | — | 0 Bytes | **0 Bytes** | **0 Bytes** | **Zero Storage Overhead** |
| **Prefetch Usefulness** | — | — | N/A | **32.25%** | **31.80%** | Selective promotion of useful lines |

---

## 📁 Repository Structure

```text
btp/
├── README.md                     # Project overview, results, and quickstart guide
├── .gitignore                    # Build artifacts and heavy binary exclusion rules
├── src/                          # Standalone simulators and custom replacement modules
│   ├── lru_prefetch_aware.cc     # Prefetch-aware LRU implementation
│   ├── lru_prefetch_aware.h
│   ├── rrip_prefetch_aware.cc    # Prefetch-aware SRRIP implementation
│   ├── rrip_prefetch_aware.h
│   ├── sim_llc_prefetch_aware.cpp# Standalone cycle-accurate LLC simulator
│   ├── run_multi_eval_suite.cpp  # Multi-policy evaluation testbench
│   ├── run.cpp
│   └── toy_cache_rl.cpp
├── configs/                      # ChampSim JSON experiment configurations
│   ├── champsim_4core_baseline.json
│   ├── champsim_4core_prefetch_aware.json
│   ├── champsim_4core_pa_rrip.json
│   ├── champsim_4core_pa_ampm.json
│   └── champsim_4core_next_line.json
├── presentation/                 # Presentation slides, LaTeX sources & visual charts
│   ├── BTP_Guide_Presentation.tex# Beamer LaTeX presentation
│   ├── presentation_preview.html # Interactive dark-theme presentation preview
│   ├── ppt.md                    # Slide content outline & speaker notes
│   ├── generate_btp_charts.py    # Matplotlib chart generation script
│   ├── chart_4core_all_cpus_ipc.png
│   ├── chart_4core_gcc_speedup.png
│   └── chart_prefetch_usefulness.png
├── results/                      # Raw simulation execution logs and traces
│   ├── 1core_baseline_mcf.txt
│   ├── 1core_prefetch_aware_mcf.txt
│   ├── 4core_baseline_mix1.txt
│   └── 4core_prefetch_aware_mix1.txt
├── docs/                         # Progress logs, research papers, and meeting summaries
│   ├── BTP_Implementation_Log.md
│   ├── BTP_Discussion_Summary.txt
│   ├── BTP_Today_Progress.md
│   ├── MidEval_Results_Summary.md
│   ├── results_multi_run_summary.md
│   └── MICRO25.pdf
├── media/                        # Demonstration videos and media assets
└── ChampSim/                     # Full ChampSim cycle-accurate simulator repository
```

---

## 🛠️ Build & Simulation Guide

### 1. Compile Standalone LLC Simulator
```bash
g++ -O3 -std=c++17 src/sim_llc_prefetch_aware.cpp -o sim_llc
./sim_llc
```

### 2. Run Policy Evaluation Testbench
```bash
g++ -O3 -std=c++17 src/run_multi_eval_suite.cpp -o run_eval
./run_eval
```

### 3. Generate Presentation Charts
```bash
python3 presentation/generate_btp_charts.py
```

### 4. Build and Run in ChampSim
```bash
cd ChampSim
./config.sh ../configs/champsim_4core_prefetch_aware.json
make -j$(nproc)
```

---

## 👥 Contributors & Contact

- **Student:** Chirag Sharma (`S20240010223`)
- **Advisor:** Dr. Bheemappa Halavar
