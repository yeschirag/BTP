#include "lru_prefetch_aware.h"
#include "cache.h"

#include <algorithm>
#include <cassert>
#include <iostream>

// Constructor: passes the cache's total sets (8192) and ways/slots-per-set (16)
lru_prefetch_aware::lru_prefetch_aware(CACHE* cache) : lru_prefetch_aware(cache, cache->NUM_SET, cache->NUM_WAY) {}

// Allocates 1 timestamp (last_used_cycles) and 1 stats-only flag (is_prefetched) per slot
lru_prefetch_aware::lru_prefetch_aware(CACHE* cache, long sets, long ways) 
    : replacement(cache), NUM_WAY(ways), 
      last_used_cycles(static_cast<std::size_t>(sets * ways), 0),
      is_prefetched(static_cast<std::size_t>(sets * ways), false) {}

// STEP 1 (EVICTION): Called ONLY when all 16 slots in `set` are full and a new block arrives.
// Returns which slot index (0..15) to throw out ("the victim").
long lru_prefetch_aware::find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                                     champsim::address full_addr, access_type type)
{
  // Slice out just the 16 timestamps belonging to this set
  auto begin = std::next(std::begin(last_used_cycles), set * NUM_WAY);
  auto end = std::next(begin, NUM_WAY);

  // Pick the slot with the SMALLEST timestamp (touched longest ago = Least Recently Used)
  auto victim = std::min_element(begin, end);
  assert(begin <= victim);
  assert(victim < end);
  return std::distance(begin, victim);
}

// STEP 2 (ARRIVAL / FILL): Called when a new block arrives from lower memory (DRAM) into slot `way`.
// NOTE: The L2 hardware prefetcher already decided to prefetch earlier; here we ONLY decide
// what initial priority timestamp the arriving block gets based on `type`.
void lru_prefetch_aware::replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                                                access_type type)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
  
  if (type == access_type::PREFETCH) {
    // SPECULATIVE PREFETCH ARRIVAL: Insert near the exit door (just above the oldest slot)
    // so useless prefetches evict quickly instead of pushing out real CPU demand blocks.
    prefetch_fills++;
    is_prefetched[index] = true; // Stats tracking only (never affects find_victim)
    
    // Find the smallest (oldest) timestamp currently in this 16-slot set
    auto begin = std::next(std::begin(last_used_cycles), set * NUM_WAY);
    auto end = std::next(begin, NUM_WAY);
    auto min_it = std::min_element(begin, end);
    
    // Place just 1 tick above the minimum: lower priority than all existing demand lines,
    // without creating negative numbers.
    last_used_cycles[index] = *min_it + 1;
  } else {
    // REAL CPU DEMAND ARRIVAL (LOAD / RFO / etc.): Give it the highest timestamp (MRU / safest)
    demand_fills++;
    is_prefetched[index] = false;
    last_used_cycles[index] = cycle++;
  }
}

// STEP 3 (HIT PROMOTION): Called by ChampSim on EVERY cache lookup (both hit=1 and hit=0).
// When a prefetched block actually gets used (`hit == 1`), PROMOTE it from near-LRU to MRU!
void lru_prefetch_aware::update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                                  champsim::address victim_addr, access_type type, uint8_t hit)
{
  std::size_t index = static_cast<std::size_t>(set * NUM_WAY + way);
  
  // Must check `hit` first (on miss, `way == NUM_WAY` = out of bounds) and skip writebacks
  if (hit && access_type{type} != access_type::WRITE) {
    // If this block originally entered as a speculative prefetch, mark it as proven useful
    if (is_prefetched[index]) {
      prefetch_promoted++;
      is_prefetched[index] = false;  // Now graduated to a normal demand line
    }
    // PROMOTION TARGET: `cycle++` is the newest/highest timestamp -> moves to MRU (top safety)!
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
