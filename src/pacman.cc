#include "pacman.h"
#include "cache.h"

#include <algorithm>
#include <iostream>

pacman::pacman(CACHE* cache) : pacman(cache, cache->NUM_SET, cache->NUM_WAY) {}

pacman::pacman(CACHE* cache, long sets, long ways)
    : replacement(cache), NUM_WAY(ways),
      rrpv(static_cast<std::size_t>(sets * ways), MAX_RRPV),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {}

long pacman::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                         champsim::address full_addr, access_type type)
{
  auto begin = std::next(std::begin(rrpv), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  while (true) {
    auto victim = std::find(begin, end, MAX_RRPV);
    if (victim != end) {
      return std::distance(begin, victim);
    }

    for (auto it = begin; it != end; ++it) {
      if (*it < MAX_RRPV) {
        (*it)++;
      }
    }
  }
}

void pacman::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                    access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  if (type == access_type::PREFETCH) {
    prefetch_fills++;
    is_prefetched.at(index) = true;
    rrpv.at(index) = MAX_RRPV; // PACMan-M: Distant insertion (3)
  } else {
    demand_fills++;
    is_prefetched.at(index) = false;
    rrpv.at(index) = MAX_RRPV - 1; // Demand: Standard SRRIP insertion (2)
  }
}

void pacman::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                      champsim::address victim_addr, access_type type, uint8_t hit)
{
  if (!hit) {
    return;
  }

  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);

  // PACMan-H rule: do NOT promote on prefetch hits or writebacks
  if (access_type{type} != access_type::PREFETCH && access_type{type} != access_type::WRITE) {
    if (is_prefetched[index]) {
      prefetch_promoted++;
      is_prefetched[index] = false;
    }
    rrpv[index] = 0;
  }
}

void pacman::replacement_final_stats()
{
  std::cout << "=== PACMan-HM (Wu et al., MICRO 2011) Statistics ===" << std::endl;
  std::cout << "Prefetch fills: " << prefetch_fills << std::endl;
  std::cout << "Demand fills: " << demand_fills << std::endl;
  std::cout << "Prefetch blocks promoted (useful): " << prefetch_promoted << std::endl;
  if (prefetch_fills > 0) {
    std::cout << "Prefetch usefulness: " << (100.0 * prefetch_promoted / prefetch_fills) << "%" << std::endl;
  }
  std::cout << "=====================================================" << std::endl;
}
