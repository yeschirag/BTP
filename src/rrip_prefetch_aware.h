#ifndef REPLACEMENT_RRIP_PREFETCH_AWARE_H
#define REPLACEMENT_RRIP_PREFETCH_AWARE_H

#include <cstdint>
#include <vector>
#include "modules.h"

/**
 * Zero-Overhead Prefetch-Aware Static RRIP (PA-SRRIP) Policy
 * Uses 2-bit RRPV (Re-Reference Interval Prediction) values per line (0..3).
 * - Demand fills are inserted at RRPV = 2 (standard SRRIP insertion).
 * - Prefetch fills are inserted at RRPV = 3 (distant / LRU insertion priority).
 * - Cache hits promote the line to RRPV = 0.
 * - Victims are selected by finding a line with RRPV = 3 (incrementing set RRPVs if needed).
 */
class rrip_prefetch_aware : public replacement
{
  long NUM_WAY;
  static constexpr uint8_t MAX_RRPV = 3;
  
  std::vector<uint8_t> rrpv;
  std::vector<bool> is_prefetched;

  // Statistics
  uint64_t prefetch_fills = 0;
  uint64_t demand_fills = 0;
  uint64_t prefetch_promoted = 0;

public:
  explicit rrip_prefetch_aware(CACHE* cache);
  rrip_prefetch_aware(CACHE* cache, long sets, long ways);

  long find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                   champsim::address full_addr, access_type type);
  void update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                champsim::address victim_addr, access_type type, uint8_t hit);
  void replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                              access_type type);
  void replacement_final_stats();
};

#endif
