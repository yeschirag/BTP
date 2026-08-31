# BTP Mid-Evaluation Results Summary
Date: February 13, 2026

## Experiment Setup
- **Simulator**: ChampSim (latest version)
- **Trace**: 600.perlbench_s-210B (SPEC CPU 2017)
- **Warmup Instructions**: 1 Million
- **Simulation Instructions**: 10 Million

## Configurations Tested

### 1. Baseline LRU (No Prefetcher)
- Standard LRU replacement at LLC
- No prefetching enabled

### 2. Prefetch-Aware LRU (With L2C IP-Stride Prefetcher)
- Modified LRU: Prefetch blocks inserted at LOW priority (near LRU)
- Demand blocks inserted at MRU (normal)
- On hit: Prefetched blocks promoted to MRU
- L2C IP-Stride prefetcher enabled

## Results

| Metric | Baseline LRU | Prefetch-Aware LRU |
|--------|-------------|-------------------|
| IPC | 2.158 | 2.159 |
| LLC Total Access | 1457 | 1508 |
| LLC MPKI | 0.146 | 0.151 |
| LLC Miss Latency | 176.4 cycles | 177.9 cycles |
| Prefetch fills (LLC) | 0 | 194 |
| Demand fills (LLC) | - | 2801 |
| Prefetch blocks reused | - | 0 |

## Key Observations

1. **Low LLC Pressure**: perlbench is compute-bound with excellent cache locality
   - Only ~1500 LLC accesses in 10M instructions
   - Most working set fits in L1/L2 cache

2. **Prefetcher Activity**: L2C IP-Stride generated 294 prefetches
   - 30 were useful at L2C level
   - 81 reached LLC level

3. **Policy Behavior**: Prefetch-aware insertion working correctly
   - 194 prefetch fills at LLC with low priority
   - 0 promotions (prefetches not reused before eviction)

## Code Implementation

### Prefetch-Aware LRU Logic:
```cpp
void replacement_cache_fill(..., access_type type) {
    if (type == access_type::PREFETCH) {
        // Insert at LOW priority (near LRU)
        last_used_cycles[index] = min_in_set + 1;
        is_prefetched[index] = true;
    } else {
        // DEMAND: Insert at MRU (normal)
        last_used_cycles[index] = cycle++;
        is_prefetched[index] = false;
    }
}

void update_replacement_state(..., uint8_t hit) {
    if (hit) {
        if (is_prefetched[index]) {
            prefetch_promoted++;  // Useful prefetch!
            is_prefetched[index] = false;
        }
        last_used_cycles[index] = cycle++;  // Promote to MRU
    }
}
```

## Next Steps (For Full BTP)

1. **More Memory-Intensive Traces**: Test with mcf, lbm, omnetpp
2. **Aggressive Prefetching**: Enable LLC prefetcher (SPP, AMPM)
3. **Compare Policies**: Test against DRRIP, SRRIP, SHIP
4. **Drishti Integration**: Explore per-core reuse prediction

## Files Created
- `replacement/lru_prefetch_aware/lru_prefetch_aware.h`
- `replacement/lru_prefetch_aware/lru_prefetch_aware.cc`
- `champsim_prefetch_aware.json`
