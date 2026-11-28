#include "srrip_guarded.h"
#include "cache.h"

#include <algorithm>

srrip_guarded::srrip_guarded(CACHE* cache) : srrip_guarded(cache, cache->NUM_SET, cache->NUM_WAY) {}

srrip_guarded::srrip_guarded(CACHE* cache, long sets, long ways)
    : replacement(cache), NUM_WAY(ways), rrpv(static_cast<std::size_t>(sets * ways), MAX_RRPV) {}

long srrip_guarded::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
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

void srrip_guarded::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                           access_type type)
{
  // Prefetch-oblivious SRRIP: all fills (demand, prefetch, writeback) enter at RRPV = 2
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
  rrpv.at(index) = MAX_RRPV - 1;
}

void srrip_guarded::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                             champsim::address victim_addr, access_type type, uint8_t hit)
{
  if (hit && access_type{type} != access_type::WRITE) {
    std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
    rrpv[index] = 0;
  }
}
