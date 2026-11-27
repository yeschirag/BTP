#ifndef REPLACEMENT_PACMAN_H
#define REPLACEMENT_PACMAN_H

#include <cstdint>
#include <vector>

#include "cache.h"
#include "modules.h"

/**
 * @brief PACMan-HM Baseline (Wu et al., MICRO 2011)
 *
 * Implements Prefetch-Aware Cache Management (PACMan-HM):
 * 1. Prefetch fills are inserted at MAX_RRPV (3, distant).
 * 2. Demand fills are inserted at MAX_RRPV - 1 (2, long).
 * 3. Unlike PA-SRRIP, prefetch hits do NOT promote the line's RRPV (only demand hits promote to 0).
 */
class pacman : public champsim::modules::replacement
{
  long NUM_WAY;
  static constexpr uint8_t MAX_RRPV = 3;

  std::vector<uint8_t> rrpv;
  std::vector<bool> is_prefetched;

  uint64_t prefetch_fills = 0;
  uint64_t demand_fills = 0;
  uint64_t prefetch_promoted = 0;

public:
  explicit pacman(CACHE* cache);
  pacman(CACHE* cache, long sets, long ways);

  long find_victim(uint32_t triggering_cpu, uint64_t instr_id, long set, const champsim::cache_block* current_set, champsim::address ip,
                   champsim::address full_addr, access_type type);
  void update_replacement_state(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip,
                                champsim::address victim_addr, access_type type, uint8_t hit);
  void replacement_cache_fill(uint32_t triggering_cpu, long set, long way, champsim::address full_addr, champsim::address ip, champsim::address victim_addr,
                              access_type type);
  void replacement_final_stats();
};

#endif
