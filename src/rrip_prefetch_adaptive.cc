#include "rrip_prefetch_adaptive.h"
#include "cache.h"

#include <algorithm>
#include <cassert>
#include <iostream>

rrip_prefetch_adaptive::rrip_prefetch_adaptive(CACHE* cache) : rrip_prefetch_adaptive(cache, cache->NUM_SET, cache->NUM_WAY) {}

rrip_prefetch_adaptive::rrip_prefetch_adaptive(CACHE* cache, long sets, long ways)
    : replacement(cache), NUM_WAY(ways),
      rrpv(static_cast<std::size_t>(sets * ways), MAX_RRPV),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {}

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
      if (is_prefetched[index]) {
        // Victim was an un-promoted prefetch line -> penalize confidence counter
        prefetch_demoted_evictions++;
        confidence_counter = std::max(0, confidence_counter - 1);
      }
      return way;
    }

    // Age lines in the set
    for (auto it = begin; it != end; ++it) {
      if (*it < MAX_RRPV) {
        (*it)++;
      }
    }
  }
}

void rrip_prefetch_adaptive::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                                   access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (type == access_type::PREFETCH) {
    prefetch_fills++;
    is_prefetched.at(index) = true;
    // Dynamic demotion: if confidence >= 32, insert at RRPV=2, else demote to RRPV=3
    rrpv.at(index) = (confidence_counter >= 32) ? (MAX_RRPV - 1) : MAX_RRPV;
  } else {
    demand_fills++;
    is_prefetched.at(index) = false;
    rrpv.at(index) = MAX_RRPV - 1; // 2
  }
}

void rrip_prefetch_adaptive::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                                     champsim::address victim_addr, access_type type, uint8_t hit)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (hit && access_type{type} != access_type::WRITE) {
    if (is_prefetched[index]) {
      prefetch_promoted++;
      // Reward confidence counter (+3)
      confidence_counter = std::min(63, confidence_counter + 3);
      is_prefetched[index] = false;
    }
    rrpv[index] = 0;
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
  if (prefetch_fills > 0) {
    std::cout << "Prefetch usefulness: " << (100.0 * prefetch_promoted / prefetch_fills) << "%" << std::endl;
  }
  std::cout << "=======================================================" << std::endl;
}
