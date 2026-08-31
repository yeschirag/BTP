# BTP: Prefetch-Resilient LLC Replacement Policy

## Project Overview
Bachelor's Thesis Project implementing lightweight, prefetch-aware cache replacement policies for ChampSim simulator. Goal: reduce LLC pollution from useless prefetches without complex hardware predictors.

## Architecture

### Core Policy: `lru_prefetch_aware`
- **Insert prefetches at low priority** (near LRU position) → evicted first if unused
- **Promote on hit** → useful prefetches move to MRU like demand blocks
- **Zero hardware overhead** compared to predictor-based approaches

Key files:
- [lru_prefetch_aware.h](../lru_prefetch_aware.h) - ChampSim replacement module header
- [lru_prefetch_aware.cc](../lru_prefetch_aware.cc) - Implementation with `replacement_cache_fill()`, `update_replacement_state()`

### ChampSim Configs (JSON)
- `champsim_prefetch_aware.json` - Single-core with L2C IP-Stride prefetcher
- `champsim_4core_prefetch_aware.json` - 4-core shared LLC configuration
- `champsim_4core_baseline.json` - Baseline comparison (standard LRU)

## Development Environment
- **Windows + WSL2 (Ubuntu 22.04)** - ChampSim builds/runs in WSL
- **ChampSim location**: `~/BTP/ChampSim/` in WSL
- **Traces**: SPEC CPU 2006/2017 format (`.xz` compressed)

## ChampSim Workflow

### Building
```bash
# In WSL, from ~/BTP/ChampSim/
./config.sh champsim_prefetch_aware.json
make
```

### Running Simulations
```bash
./bin/champsim_prefetch_aware --warmup 500000 --simulation 5000000 traces/403.gcc-16B.champsimtrace.xz
```

### Key Metrics to Track
- **IPC** - Instructions Per Cycle
- **LLC MPKI** - Misses Per Kilo Instructions
- **Prefetch usefulness** - `prefetch_promoted / prefetch_fills` (printed at end)

## Code Conventions

### ChampSim Replacement Module Structure
```cpp
class lru_prefetch_aware : public champsim::modules::replacement {
    // Required overrides:
    long find_victim(...);           // Select eviction candidate
    void replacement_cache_fill(...); // Handle new block insertion
    void update_replacement_state(...); // Handle hits
    void replacement_final_stats();   // Print custom statistics
};
```

### Access Type Detection
```cpp
if (type == access_type::PREFETCH) {
    // Prefetch block - insert low priority
} else {
    // Demand block - insert at MRU
}
```

## Experiment Structure

| Trace Type | Expected Behavior |
|------------|-------------------|
| Compute-bound (perlbench) | Low LLC pressure, minimal prefetch impact |
| Mixed (gcc) | ~35% prefetch usefulness, IPC improvement |
| Memory-bound (mcf) | <1% usefulness, pointer-chasing defeats prefetcher |

## Future Work (documented in BTP_Implementation_Log.md)
- Compare with DRRIP, SHiP, SRRIP policies
- Heterogeneous multicore experiments (gcc + mcf mix)
- Drishti-style sampling exploration
