#include "rrip_prefetch_aware.h"
#include "cache.h"

#include <algorithm>
#include <cassert>
#include <iostream>

rrip_prefetch_aware::rrip_prefetch_aware(CACHE* cache) : rrip_prefetch_aware(cache, cache->NUM_SET, cache->NUM_WAY) {}

rrip_prefetch_aware::rrip_prefetch_aware(CACHE* cache, long sets, long ways)
    : replacement(cache), NUM_WAY(ways),
      rrpv(static_cast<std::size_t>(sets * ways), MAX_RRPV),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {}

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

    // Increment RRPV of all lines in the set until at least one line reaches MAX_RRPV
    for (auto it = begin; it != end; ++it) {
      if (*it < MAX_RRPV) {
        (*it)++;
      }
    }
  }
}

void rrip_prefetch_aware::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                                 access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (type == access_type::PREFETCH) {
    // PREFETCH: Insert at DISTANT priority (RRPV = 3)
    prefetch_fills++;
    is_prefetched.at(index) = true;
    rrpv.at(index) = MAX_RRPV; // 3
  } else {
    // DEMAND: Insert at LONG-RE-REFERENCE priority (RRPV = 2, standard SRRIP)
    demand_fills++;
    is_prefetched.at(index) = false;
    rrpv.at(index) = MAX_RRPV - 1; // 2
  }
}

void rrip_prefetch_aware::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                                   champsim::address victim_addr, access_type type, uint8_t hit)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (hit && access_type{type} != access_type::WRITE) {
    // On hit: promote to NEAR-IMMEDIATE re-reference (RRPV = 0)
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
