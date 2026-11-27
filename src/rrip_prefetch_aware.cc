#include "rrip_prefetch_aware.h"
#include "cache.h"

#include <algorithm>
#include <cassert>
#include <iostream>

// Constructor: initializes every slot's 2-bit RRPV to MAX_RRPV (3 = immediate victim)
rrip_prefetch_aware::rrip_prefetch_aware(CACHE* cache) : rrip_prefetch_aware(cache, cache->NUM_SET, cache->NUM_WAY) {}

rrip_prefetch_aware::rrip_prefetch_aware(CACHE* cache, long sets, long ways)
    : replacement(cache), NUM_WAY(ways),
      rrpv(static_cast<std::size_t>(sets * ways), MAX_RRPV),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {} // Stats-only flag (0 bits needed in hardware)

// STEP 1 (EVICTION): Scan the 16 slots in `set` for RRPV == 3 (distant/victim).
// If nobody is 3 yet, age every slot in the set by +1 and scan again until one hits 3.
long rrip_prefetch_aware::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                                      champsim::address full_addr, access_type type)
{
  auto begin = std::next(std::begin(rrpv), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  // Look for a line with RRPV == MAX_RRPV (3)
  while (true) {
    auto victim = std::find(begin, end, MAX_RRPV);
    if (victim != end) {
      return std::distance(begin, victim);
    }

    // No line at 3 yet -> increment RRPV of every slot (< 3) by +1
    for (auto it = begin; it != end; ++it) {
      if (*it < MAX_RRPV) {
        (*it)++;
      }
    }
  }
}

// STEP 2 (ARRIVAL / FILL): Runs when a newly fetched block lands in `way`.
// Uses only the bus transaction `type` wire (zero extra per-line hardware state).
void rrip_prefetch_aware::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                                 access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (type == access_type::PREFETCH) {
    // SPECULATIVE PREFETCH: Insert at RRPV = 3 (immediate eviction candidate / quarantine)
    prefetch_fills++;
    is_prefetched.at(index) = true; // Stats-only
    rrpv.at(index) = MAX_RRPV;      // 3
  } else {
    // DEMAND FILL: Insert at RRPV = 2 (standard SRRIP "long re-reference" protection)
    demand_fills++;
    is_prefetched.at(index) = false;
    rrpv.at(index) = MAX_RRPV - 1;  // 2
  }
}

// STEP 3 (HIT PROMOTION): Runs on cache lookup; if found (`hit`), promote slot to RRPV = 0 (MRU).
void rrip_prefetch_aware::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                                   champsim::address victim_addr, access_type type, uint8_t hit)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (hit && access_type{type} != access_type::WRITE) {
    // On hit: promote from RRPV 3/2/1 straight to RRPV = 0 (maximum protection)
    if (is_prefetched[index]) {
      prefetch_promoted++;
      is_prefetched[index] = false; // Useful prefetch line is now treated as demand
    }
    rrpv[index] = 0;
  }
}

void rrip_prefetch_aware::replacement_final_stats()
{
  std::cout << "=== Zero-Overhead Prefetch-Aware SRRIP Statistics ===" << std::endl;
  std::cout << "Prefetch fills: " << prefetch_fills << std::endl;
  std::cout << "Demand fills: " << demand_fills << std::endl;
  std::cout << "Prefetch blocks promoted (useful): " << prefetch_promoted << std::endl;
  if (prefetch_fills > 0) {
    std::cout << "Prefetch usefulness: " << (100.0 * prefetch_promoted / prefetch_fills) << "%" << std::endl;
  }
  std::cout << "=====================================================" << std::endl;
}
