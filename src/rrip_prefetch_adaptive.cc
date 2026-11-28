#include "rrip_prefetch_adaptive.h"
#include "cache.h"

#include <algorithm>
#include <cassert>
#include <iostream>

// Constructor: initializes RRPV=3 and confidence_counter=32 (starts in neutral/streaming threshold)
rrip_prefetch_adaptive::rrip_prefetch_adaptive(CACHE* cache) : rrip_prefetch_adaptive(cache, cache->NUM_SET, cache->NUM_WAY) {}

rrip_prefetch_adaptive::rrip_prefetch_adaptive(CACHE* cache, long sets, long ways)
    : replacement(cache), NUM_WAY(ways),
      rrpv(static_cast<std::size_t>(sets * ways), MAX_RRPV),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {}

// STEP 1 (EVICTION + FEEDBACK PENALTY): Finds first RRPV == 3 slot to evict (aging +1 if none).
// If that victim entered as a prefetch and was NEVER hit, penalize the 6-bit confidence counter (-1).
long rrip_prefetch_adaptive::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                                        champsim::address full_addr, access_type type)
{
  auto begin = std::next(std::begin(rrpv), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  while (true) {
    auto victim = std::find(begin, end, MAX_RRPV);
    if (victim != end) {
      long way = std::distance(begin, victim);
      std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
      // Note: reads `is_prefetched[index]` (reuses 1-bit/line prefetch metadata or costs 16 KB on 8MB LLC)
      if (is_prefetched[index]) {
        // Victim was an un-promoted prefetch line -> penalize confidence counter (-1)
        prefetch_demoted_evictions++;
        confidence_counter = std::max(0, confidence_counter - 1);
      }
      return way;
    }

    // Age all lines in the set (< 3) by +1
    for (auto it = begin; it != end; ++it) {
      if (*it < MAX_RRPV) {
        (*it)++;
      }
    }
  }
}

// STEP 2 (ADAPTIVE FILL): Chooses prefetch insertion depth dynamically using confidence_counter.
// >= 32 (Streaming Mode): insert prefetch at RRPV=2; < 32 (Filtering Mode): demote to RRPV=3.
void rrip_prefetch_adaptive::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                                   access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (type == access_type::PREFETCH) {
    prefetch_fills++;
    is_prefetched.at(index) = true;
    // Dynamic demotion: high confidence keeps useful stream (RRPV=2); low confidence quarantines (RRPV=3)
    if (confidence_counter >= 32) {
      pf_streaming_fills++;
      rrpv.at(index) = MAX_RRPV - 1;
    } else {
      pf_filtering_fills++;
      rrpv.at(index) = MAX_RRPV;
    }
  } else {
    demand_fills++;
    is_prefetched.at(index) = false;
    rrpv.at(index) = MAX_RRPV - 1; // Demand always enters at RRPV=2
  }
}

// STEP 3 (HIT PROMOTION + FEEDBACK REWARD): On hit, promote slot to RRPV=0 (MRU).
// If the hit block was an un-promoted prefetch, reward confidence_counter (+3) and clear flag.
void rrip_prefetch_adaptive::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                                     champsim::address victim_addr, access_type type, uint8_t hit)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (hit && access_type{type} != access_type::WRITE) {
    if (is_prefetched[index]) {
      prefetch_promoted++;
      // Asymmetric +3 reward: useful prefetch hits are rarer than useless fills
      confidence_counter = std::min(63, confidence_counter + 3);
      is_prefetched[index] = false;
    }
    rrpv[index] = 0; // Promote to MRU (maximum retention)
  }
}

void rrip_prefetch_adaptive::replacement_final_stats()
{
  std::cout << "=== PA-Adaptive SRRIP (Dynamic Demotion) Statistics ===" << std::endl;
  std::cout << "Prefetch fills: " << prefetch_fills << std::endl;
  std::cout << "Demand fills: " << demand_fills << std::endl;
  std::cout << "Prefetch blocks promoted (useful): " << prefetch_promoted << std::endl;
  std::cout << "Unused prefetch evictions: " << prefetch_demoted_evictions << std::endl;
  std::cout << "Final Confidence Counter: " << confidence_counter << " / 63" << std::endl;
  std::cout << "Prefetch fills in Streaming Mode (C >= 32): " << pf_streaming_fills << std::endl;
  std::cout << "Prefetch fills in Filtering Mode (C < 32): " << pf_filtering_fills << std::endl;
  if (prefetch_fills > 0) {
    std::cout << "Fraction of PF fills in Streaming Mode: " << (100.0 * pf_streaming_fills / prefetch_fills) << "%" << std::endl;
    std::cout << "Prefetch usefulness: " << (100.0 * prefetch_promoted / prefetch_fills) << "%" << std::endl;
  }
  std::cout << "=======================================================" << std::endl;
}
