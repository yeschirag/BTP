#include "lru_prefetch_aware.h"

#include <algorithm>
#include <cassert>
#include <iostream>

lru_prefetch_aware::lru_prefetch_aware(CACHE* cache) : lru_prefetch_aware(cache, cache->NUM_SET, cache->NUM_WAY) {}

lru_prefetch_aware::lru_prefetch_aware(CACHE* cache, long sets, long ways) 
    : replacement(cache), NUM_WAY(ways), 
      last_used_cycles(static_cast<std::size_t>(sets * ways), 0),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {}

long lru_prefetch_aware::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                                     champsim::address full_addr, access_type type)
{
  auto begin = std::next(std::begin(last_used_cycles), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  // Find the way whose last use cycle is most distant (LRU)
  auto victim = std::min_element(begin, end);
  assert(begin <= victim);
  assert(victim < end);
  return std::distance(begin, victim);
}

void lru_prefetch_aware::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                                access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
  
  if (type == access_type::PREFETCH) {
    // PREFETCH: Insert at LOW priority (near LRU position)
    prefetch_fills++;
    is_prefetched[index] = true;
    
    // Find the minimum cycle in this set and insert just above it
    auto begin = std::next(std::begin(last_used_cycles), set * NUM_WAY);
    auto end = std::next(begin, NUM_WAY);
    auto min_it = std::min_element(begin, end);
    
    // Insert with a value slightly higher than LRU (low priority but not lowest)
    last_used_cycles[index] = *min_it + 1;
  } else {
    // DEMAND: Insert at MRU position (normal behavior)
    demand_fills++;
    is_prefetched[index] = false;
    last_used_cycles[index] = cycle++;
  }
}

void lru_prefetch_aware::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                                  champsim::address victim_addr, access_type type, uint8_t hit)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
  
  // Skip writeback hits
  if (hit && access_type{type} != access_type::WRITE) {
    // On hit: promote to MRU
    // If this was a prefetched block being reused, count it as a useful prefetch
    if (is_prefetched[index]) {
      prefetch_promoted++;
      is_prefetched[index] = false;  // Promoted line is now treated as demand
    }
    last_used_cycles[index] = cycle++;
  }
}

void lru_prefetch_aware::replacement_final_stats()
{
  std::cout << "=== Prefetch-Aware LRU Statistics ===" << std::endl;
  std::cout << "Prefetch fills: " << prefetch_fills << std::endl;
  std::cout << "Demand fills: " << demand_fills << std::endl;
  std::cout << "Prefetch blocks promoted (useful): " << prefetch_promoted << std::endl;
  if (prefetch_fills > 0) {
    std::cout << "Prefetch usefulness: " << (100.0 * prefetch_promoted / prefetch_fills) << "%" << std::endl;
  }
  std::cout << "=====================================" << std::endl;
}
