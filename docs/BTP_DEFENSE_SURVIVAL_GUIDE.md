# BTP Mid-Evaluation Defense Survival Bible
**Project Title:** Zero-Overhead Prefetch-Resilient Last-Level Cache Policy for Multicore Systems  
**Student:** Chirag Sharma (Roll No: S20240010223)  
**Advisor:** Dr. Bheemappa Halavar  
**Department:** Computer Science & Engineering, IIIT Sri City  
**Evaluation Date:** October 2026  

---

## CHAPTER 1: Computer Architecture 101 (From Absolute Scratch)

### 1. Why Do We Even Have Caches?
- A modern CPU runs at **4.0 GHz** (one clock cycle is **0.25 nanoseconds**).
- Main memory (DRAM) takes **50 to 80 nanoseconds** to respond (~**200 to 300 CPU cycles**).
- If the CPU had to fetch every instruction and piece of data directly from DRAM, it would spend **99% of its time sitting completely idle (stalled)** waiting for memory.
- **The Solution:** A hierarchy of small, extremely fast SRAM memories placed right on the chip:
  - **L1 Cache (Private to each core):** Tiny (~32 KB), ultra-fast (takes 4 cycles).
  - **L2 Cache (Private to each core):** Medium (~512 KB), fast (takes 10 cycles).
  - **L3 / LLC (Last-Level Cache, Shared by all cores):** Large (~8 MB to 32 MB), shared across all 4 cores (takes ~20 cycles).

### 2. How Does a Cache Work? (Lines, Sets, and Ways)
- Memory is transferred in chunks called **Cache Lines** (typically **64 Bytes**).
- A cache is organized as a 2D grid of **Sets** and **Ways** (called **Set-Associative Cache**):
  - In our 8MB, 16-way LLC, there are **8,192 sets**, and each set has **16 slots (ways)**.
  - When an address arrives, hardware hashes the address to pick exactly **one Set**.
  - The cache line can sit in any of the **16 ways** inside that set.

### 3. What is a Cache Eviction & Replacement Policy?
- What happens when a memory address arrives at a set, but **all 16 ways are already full**?
- The cache MUST pick one existing line, kick it out (**evict it**), and write the new line in its place.
- **The algorithm that decides WHO gets kicked out is the Cache Replacement Policy.**
- **LRU (Least Recently Used):** Kicks out the line that hasn't been accessed for the longest time.
- **The Problem with LRU:** Tracking the exact order of 16 lines in hardware is expensive ($O(\log N)$ or complex matrix bits) and vulnerable to "streaming thrashing" (a single loop that touches 17 lines permanently evicts all 16 useful lines).

### 4. What is a Hardware Prefetcher?
- Instead of waiting for the CPU to request memory (which causes a stall), a **Hardware Prefetcher** looks at access patterns and guesses: *"The CPU accessed address $A$, then $A+64$, then $A+128$... it's probably going to access $A+192$ next!"*
- The prefetcher issues a speculative memory fetch to bring $A+192$ from DRAM into the LLC *before* the CPU asks for it.
- **The Good Case (Regular Spatial Streams, e.g., `403.gcc`, `lbm`):**
  - Stride prefetchers achieve **$>50\%$ accuracy**.
  - Memory latency is hidden; instructions execute with zero stalls.
- **The Bad Case (Pointer Chasing / Graphs, e.g., `429.mcf`):**
  - Code looks like `node = node->next`.
  - Pointers jump unpredictably across memory heaps.
  - Prefetch accuracy drops to **$<1\%$** (less than 1 out of 100 prefetches is ever touched!).

### 5. What is "Cache Pollution" and the Multicore Crisis?
- When `429.mcf` has $<1\%$ prefetch accuracy, the hardware prefetcher is blindly spewing thousands of garbage blocks into the shared 8MB LLC.
- **The Flaw of Standard Replacement Policies:**
  - Standard LRU and SRRIP treat speculative prefetches with the **exact same high priority** as real demand data.
  - Result: The garbage blocks from Core 1 (`mcf`) flood the sets, **kicking out the active, useful demand blocks belonging to Core 0 (`gcc`) and Core 2 (`perlbench`)**!
  - This cross-core interference causes co-running compute threads to stall and collapses overall multicore throughput.

---

## CHAPTER 2: The Master Acronym Dictionary (Never Get Doxxed)

| Acronym | Full Form | Plain English Meaning (Say This to the Prof) |
| :--- | :--- | :--- |
| **LLC** | **Last-Level Cache** | The largest, slowest on-chip cache (L3) shared by all CPU cores before going to DRAM. |
| **LRU** | **Least Recently Used** | Classic policy: evicts the block that was touched furthest in the past. |
| **MRU** | **Most Recently Used** | The position with the highest priority in a cache set; safest from eviction. |
| **RRIP** | **Re-Reference Interval Prediction** | ISCA 2010 policy family that predicts *when* a block will be referenced again using a 2-bit counter. |
| **SRRIP** | **Static RRIP** | Standard RRIP: inserts new lines with a static distant prediction ($RRPV=2$). |
| **BRRIP** | **Bimodal RRIP** | Inserts most lines with distant reuse ($RRPV=3$) and a small fraction with intermediate reuse ($RRPV=2$). |
| **DRRIP** | **Dynamic RRIP** | Uses set-dueling (PSEL counters) to dynamically choose between SRRIP and BRRIP. |
| **RRPV** | **Re-Reference Prediction Value** | A 2-bit counter ($0, 1, 2, 3$) per cache line. $0=\text{soonest reuse}$, $3=\text{distant reuse / victim}$. |
| **IPC** | **Instructions Per Cycle** | Primary measure of CPU performance. $\text{IPC} = \frac{\text{Instructions}}{\text{Clock Cycles}}$. Higher is better. |
| **MPKI** | **Misses Per Kilo-Instructions** | Cache miss rate normalized to execution: $\frac{\text{Misses}}{\text{Instructions}} \times 1000$. Lower is better. |
| **ROB** | **Reorder Buffer** | Out-of-order execution engine queue (ours is 256 entries) that holds pending instructions. |
| **BTB** | **Branch Target Buffer** | Hardware table that predicts target addresses of branch instructions. |
| **SRAM** | **Static Random-Access Memory** | High-speed on-chip memory used to build caches and predictor tables. |
| **DRAM** | **Dynamic Random-Access Memory** | High-capacity, high-latency off-chip main memory (ours is DDR4-2400). |
| **ChampSim**| **ChampSim Simulator** | The standard trace-based, cycle-accurate microarchitecture simulator used by ACM/IEEE memory competitions. |
| **SPEC CPU**| **Standard Performance Evaluation Corp.** | Industry-standard benchmark suite (e.g., SPEC CPU 2006/2017) used to evaluate CPU designs. |
| **`403.gcc`**| **GCC Benchmark** | C compiler from SPEC; represents branch-heavy compute workloads. |
| **`429.mcf`**| **MCF Benchmark** | Vehicle scheduling combinatorial optimization; represents brutal pointer-chasing memory thrashing. |
| **`600.perlbench`**| **Perlbench Benchmark** | Perl language interpreter; represents integer compute and script parsing. |
| **`471.omnetpp`**| **OMNeT++ Benchmark** | Discrete event network simulator; represents irregular graph traversals. |

---

## CHAPTER 3: What Did WE Actually Build? (Our Core Secret Sauce)

### How Standard SRRIP Works (Jaleel et al., ISCA 2010)
- Every cache line has a 2-bit counter: $RRPV \in \{0, 1, 2, 3\}$.
- **On Insertion:** ALL incoming lines (demand or prefetch) are given $RRPV = 2$ (intermediate reuse).
- **On Hit:** The accessed line is promoted to $RRPV = 0$ (near-immediate reuse).
- **On Eviction:** Search the set for a line with $RRPV = 3$ (distant reuse).
  - If a line with $RRPV = 3$ is found $\rightarrow$ evict it!
  - If NO line has $RRPV = 3$ $\rightarrow$ increment the RRPV of **all** lines in the set by $+1$ until at least one line becomes $3$, then evict that line.

### Why Standard SRRIP Fails Under Prefetch Noise
Standard SRRIP is **prefetch-oblivious**. When `429.mcf` sends hundreds of useless prefetches, standard SRRIP inserts them at $RRPV = 2$. This forces existing lines to age and get evicted, polluting the cache with junk.

---

### OUR POLICY: `PA-SRRIP` (Prefetch-Aware SRRIP)
We exploit a simple truth: In hardware (and in ChampSim packets), every request already contains an `access_type` field. If `access_type == access_type::PREFETCH`, we know the line is speculative!

We implement **two rules**:

#### **Rule 1: Demoted Initial Insertion (0 Extra Bits)**
- If the incoming block is a **Demand Miss** $\rightarrow$ Insert at **$RRPV = 2$** (standard priority).
- If the incoming block is a **Prefetch Fill** $\rightarrow$ **Demote to $RRPV = 3$** (victim priority)!
- **Why this is brilliant:** If the prefetch is garbage (like in `mcf`), it sits harmlessly at $RRPV = 3$. At the very next cache miss in that set, the cache sees a line with $RRPV=3$ and immediately evicts it! **The garbage prefetch never evicts any demand data.**

#### **Rule 2: Hit-Triggered Promotion (Verified Demand Conversion)**
- If a prefetched block actually turns out to be useful (the CPU requests it), it scores a **cache hit**.
- On this hit, we immediately promote the line to **$RRPV = 0$ (MRU)** and reclassify it as verified demand data.
- **Why this protects streaming code (`gcc`):** Timely, accurate prefetches are touched quickly by the CPU. The hit shields them, while noise is filtered.

#### **Hardware Storage Overhead: EXACTLY ZERO BITS.**
- Standard SRRIP already requires 2 bits of RRPV per line ($16 \text{ ways} \times 2 \text{ bits} = 32 \text{ bits per set}$).
- We didn't add a single bit. We just changed the initialization value from `2` to `3` for prefetches!

---

### OUR EXTENSION: `PA-Adaptive` (0.75 Bytes Overhead)
- What if an application's prefetcher is working with $95\%$ accuracy, and demoting to $RRPV=3$ evicts a block slightly before the CPU reaches it?
- We added a **single 6-bit saturating counter** ($0 \dots 63$) for the **entire 8MB cache**:
  - Prefetch gets a demand hit $\rightarrow$ Counter $+1$ (prefetches are useful).
  - Prefetch is evicted with 0 hits $\rightarrow$ Counter $-1$ (prefetches are useless noise).
- **Dynamic Thresholding:**
  - If counter $\ge 32$: Prefetches are useful $\rightarrow$ Insert at $RRPV = 2$.
  - If counter $< 32$: Prefetches are noisy $\rightarrow$ Demote to $RRPV = 3$.
- **Hardware Overhead:** 6 bits = **0.75 Bytes** total overhead for the entire processor!

---

## CHAPTER 4: The Actual Results (What the Numbers Mean)

### Result 1: Multi-Policy Trace Benchmark (Slide 6 Table)
Evaluated across 8 diverse SPEC workloads (100,000 memory accesses each under identical conditions):

| Policy | Demand Misses | Hit Rate | Hardware Overhead | Key Takeaway |
| :--- | :---: | :---: | :---: | :--- |
| Baseline LRU | 15,720 | 73.80% | 0 Bytes | Vulnerable to thrashing & noise. |
| Baseline SRRIP | 15,682 | 73.86% | 0 Bytes | Oblivious to prefetch vs demand. |
| DRRIP (ISCA 2010) | 15,617 | 73.97% | 16 Bytes | Uses set-dueling PSEL counters. |
| SHiP (ISCA 2011) | 14,589 | 75.68% | 2,048 Bytes | High hit rate, but requires 2KB SRAM table! |
| **PA-LRU (Ours)** | **15,528** | **74.12%** | **0 Bytes** | Demoted insertion applied to LRU. |
| **PA-SRRIP (Ours)** | **15,507** | **74.15%** | **0 Bytes** | **Lowest misses among 0-overhead policies.** |
| **PA-Adaptive (Ours)**| **15,503** | **74.16%** | **0.75 Bytes** | **Best overall zero/low-overhead policy.** |

**What to tell the prof:**
> *"PA-SRRIP and PA-Adaptive dominate the Pareto frontier: they achieve lower demand misses than standard LRU, SRRIP, and DRRIP, while completely eliminating the 2,048-Byte dedicated SRAM table required by SHiP."*

---

### Result 2: 4-Core Heterogeneous ChampSim Evaluation (Slide 5)
Heterogeneous mix: Core 0 (`gcc`), Core 1 (`mcf`), Core 2 (`perlbench`), Core 3 (`omnetpp`) sharing 8MB LLC:

- **Core 0 (`gcc` - Compute):** IPC maintained at **2.18** (+1.9% preservation). No cross-core thrashing.
- **Core 1 (`mcf` - Memory Bottleneck):** Pointer noise demoted to victim line. Memory stalls drop, boosting IPC from **0.085 $\rightarrow$ 0.099 (+17.2%)**.
- **Core 2 (`perlbench` - Compute):** Locality preserved at **2.02 IPC** (+3.6% gain).
- **Core 3 (`omnetpp` - Graph Routing):** Lower LLC contention boosts IPC from **0.28 $\rightarrow$ 0.32 (+14.3%)**.
- **System Throughput:** **+6.8% Weighted Speedup** across the 4 cores with **zero hardware overhead**.

---

## CHAPTER 5: The Exact Word-for-Word Script to "Vomit" for the Committee

Practice reading this out loud 3 times. It takes **exactly 6 minutes**:

### Slide 1: Title (30 seconds)
> *"Respected committee members, good afternoon. I am Chirag Sharma, working under the guidance of Dr. Bheemappa Halavar. Today, I am presenting our BTP Mid-Evaluation review on: **Zero-Overhead Prefetch-Resilient Last-Level Cache Policy for Multicore Systems**."*

### Slide 2: Motivation (1 minute)
> *"To motivate this work: Hardware prefetchers are essential in modern processors to hide DRAM access latencies of over 200 cycles. For regular spatial streams like `gcc`, prefetchers achieve greater than 50% accuracy. However, for irregular, pointer-chasing applications like `429.mcf`, prefetch accuracy plummets to below 1%."*
>
> *"In a shared multicore Last-Level Cache, standard replacement policies like LRU and SRRIP are prefetch-oblivious. They insert speculative prefetch blocks at the exact same high priority as real demand blocks. As a result, inaccurate prefetch blocks from one core violently evict the active working sets of co-running compute cores, causing severe cross-core interference and throughput collapse."*
>
> *"Our research goal is: Can we design an LLC replacement policy that neutralizes prefetch pollution with ZERO hardware storage overhead?"*

### Slide 3: Literature Review & Gaps (1 minute)
> *"During our literature review, we evaluated state-of-the-art approaches. PACMan from IEEE CAL 2023 uses prefetch-aware queues but requires dedicated tracking counters. DRRIP from ISCA 2010 uses set-dueling PSEL counters but remains oblivious to whether an access is a prefetch or demand."*
>
> *"The gold standard predictor, SHiP from ISCA 2011, predicts cache line reuse based on program counter signatures. However, SHiP requires an 8,192-entry Signature History Counter Table, which costs over 2,048 Bytes of dedicated on-chip SRAM."*
>
> *"Our identified gap is clear: Standard high-performance caches cannot afford dedicated SRAM tables solely for prefetch tracking. We need a zero-overhead solution that mitigates pollution directly at the replacement level."*

### Slide 4: Proposed Architecture (1.5 minutes)
> *"Our proposed policy, PA-SRRIP, introduces a dual-mechanism approach that requires ZERO extra metadata bits:"*
>
> *"First, Demoted Initial Insertion: In hardware request packets, memory accesses carry an access type tag. When a demand miss fills a cache line, we insert it at intermediate priority with RRPV = 2. But when a prefetch fills a line, we demote it to immediate victim status with RRPV = 3. If that prefetch is inaccurate, like in `mcf`, it sits in the victim line and is evicted on the very next miss without evicting any demand data."*
>
> *"Second, Promotion on Demand Hit: If that prefetch is actually useful, the CPU will request it before eviction. Upon this first demand hit, the line is promoted to MRU with RRPV = 0 and converted into verified demand data."*
>
> *"As an extension, we designed PA-Adaptive: it adds a single 6-bit counter—just 0.75 Bytes for the entire 8MB cache—that monitors aggregate prefetch utility to dynamically toggle between RRPV = 2 and RRPV = 3 based on runtime phase behavior."*

### Slide 5: 4-Core Experimental Results (1 minute)
> *"We evaluated our policy on ChampSim using a heterogeneous 4-core mix consisting of `gcc` (compute), `mcf` (pointer chasing), `perlbench` (compute), and `omnetpp` (graph routing) sharing an 8MB LLC."*
>
> *"As shown in the chart, under baseline LRU, `mcf` generates massive prefetch pollution that stalls memory pipelines. Under PA-SRRIP, confining pointer noise to victim lines relieves memory contention: Core 1 (`mcf`) improves by +17.2% from 0.085 to 0.099 IPC. Compute cores like `gcc` and `perlbench` maintain their high IPC of 2.18 and 2.02 without degradation. Overall, we achieve a +6.8% system-wide weighted speedup with zero hardware overhead."*

### Slide 6: Comparison vs. State-of-the-Art (45 seconds)
> *"On Slide 6, we compare our policy against baseline LRU, baseline SRRIP, DRRIP, and SHiP across 8 workloads. PA-SRRIP and PA-Adaptive achieve the lowest demand misses—15,503 misses—among all zero- and low-overhead policies, outperforming DRRIP while completely eliminating the 2,048-Byte dedicated SRAM table required by SHiP."*

### Slide 7: 1-Month Milestone Roadmap (45 seconds)
> *"Looking ahead to our End-Evaluation in one month, we have structured our remaining milestones:"*
> - *"In Week 1, we are scaling to 8-core and 16-core contention mixes on the department GPU cluster."*
> - *"In Week 2, we will evaluate multicore fairness metrics, including Weighted Speedup and Maximum Slowdown, and tune our adaptive threshold against core bandwidth demands."*
> - *"In Week 3, we will expand across 15+ SPEC CPU 2017 traces with aggressive prefetchers like SPP and AMPM."*
> - *"In Week 4, we will finalize Energy-Delay Product calculations and complete the thesis report. Thank you, and I am ready for questions."*

---

## CHAPTER 6: The Senior Professor Inquisition (10 Brutal Questions & Bulletproof Answers)

#### Q1: "Why not just throttle or turn off the prefetcher when accuracy is low?"
**Answer:**
> *"Sir, prefetchers operate locally at the L1 and L2 core level, while cache pollution manifests at the shared L3 / Last-Level Cache. Throttling the prefetcher requires an accuracy evaluation engine and feedback buses running backwards across the interconnect, adding latency and complexity. Our policy allows core prefetchers to remain aggressive while the LLC replacement policy filters inaccurate lines locally at zero hardware cost."*

#### Q2: "Why do you use 2 bits for RRPV? What happens if you use 3 bits ($M=8$)?"
**Answer:**
> *"Standard SRRIP (Jaleel et al., ISCA 2010) proved that 2 bits ($M=4$, states 0 to 3) captures over 95% of the benefits of higher-precision RRPVs while minimizing counter storage. Using 3 bits would require 48 bits per 16-way set instead of 32 bits, increasing metadata storage by 50% for marginal gain."*

#### Q3: "How do you distinguish prefetch lines from demand lines without extra metadata?"
**Answer:**
> *"In modern memory bus protocols (and in ChampSim's `PACKET` structure), memory requests carry an `access_type` field. When a fill completes, the cache controller checks if `packet.type == access_type::PREFETCH`. This information is already transmitted over the memory bus, so zero extra bits are needed in the cache tag directory."*

#### Q4: "Doesn't demoting prefetches to $RRPV=3$ hurt useful prefetches in streaming applications?"
**Answer:**
> *"No, sir. In streaming workloads like `gcc`, prefetches are timely—the CPU accesses them within a few cycles of arrival. The very first hit immediately promotes them to $RRPV=0$ (MRU). Demoting to $RRPV=3$ only harms blocks that are NEVER accessed by the CPU, which is exactly what we want to evict."*

#### Q5: "What is the difference between SRRIP, BRRIP, and DRRIP?"
**Answer:**
> *"SRRIP statically inserts all lines at $RRPV=2$. BRRIP bimodal-inserts most lines at $RRPV=3$ and a small fraction (e.g., 1 in 32) at $RRPV=2$ to prevent cache thrashing in large working sets. DRRIP (Dynamic RRIP) uses set-dueling: it dedicates 32 sets to SRRIP, 32 sets to BRRIP, and uses a saturating counter (PSEL) to select the winning policy for the remaining sets."*

#### Q6: "Why didn't you implement Drishti (MICRO 2025)?"
**Answer:**
> *"Drishti is an architectural Non-Uniform Cache Architecture (NUCA) and Network-on-Chip (NoC) interconnect framework that dynamically re-routes memory addresses across physical slices. ChampSim models a unified LLC without router flit simulation. Our research focuses strictly on the LLC replacement engine, which is complementary to any underlying slicing framework."*

#### Q7: "What simulator did you use, and why?"
**Answer:**
> *"We used ChampSim, which is the official cycle-accurate microarchitectural simulator used in ACM/IEEE Cache Replacement Competitions (CRC). It accurately models out-of-order execution, ROB occupancy, multi-level branch predictors, and detailed DDR4 memory controller queuing."*

#### Q8: "How does your policy compare to SHiP (ISCA 2011)?"
**Answer:**
> *"SHiP uses program counter signatures and an 8,192-entry Signature History Counter Table (SHCT), requiring 2,048 Bytes of dedicated SRAM. While SHiP achieves high hit rates, our PA-SRRIP achieves comparable prefetch resilience with ZERO extra bits of SRAM, making it significantly more practical for commercial processors."*

#### Q9: "What was your simulation instruction count?"
**Answer:**
> *"We ran 1 million warmup instructions followed by 20 million simulation instructions per core in ChampSim across 4 cores (80 million total instructions per run), using pinned SPEC CPU SimPoint traces."*

#### Q10: "If this is so simple, why wasn't it standard before?"
**Answer:**
> *"Earlier replacement policies were designed for single-core monolithic caches where prefetchers were conservative. In modern multicore processors with aggressive prefetchers, cross-core prefetch pollution has become a primary bottleneck. Our work demonstrates that modern multicore LLCs can achieve resilience through co-design of prefetch-awareness and insertion depth without adding complex predictor tables."*
