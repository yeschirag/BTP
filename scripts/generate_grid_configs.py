#!/usr/bin/env python3
"""
Generate matched ChampSim configuration files for systematic evaluation:
- Grid A: L2C prefetcher = va_ampm_lite
- Grid B: L2C prefetcher = ip_stride
- Control: L2C prefetcher = no (SRRIP vs PA-SRRIP equivalence check)
- 1-Core Standalone configs (IPC_alone) for Weighted & Harmonic Speedup
"""
import json
import copy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_CFG_PATH = ROOT / "configs" / "champsim_4core_pa_rrip.json"
OUT_DIR = ROOT / "configs" / "grid"

POLICIES = [
    "lru",
    "srrip",
    "drrip",
    "ship",
    "pacman",
    "lru_prefetch_aware",
    "rrip_prefetch_aware",
    "rrip_prefetch_adaptive",
]

PREFETCHERS = ["va_ampm_lite", "ip_stride"]


def make_1core_from_4core(cfg_4core: dict, prefetcher: str, policy: str) -> dict:
    cfg = copy.deepcopy(cfg_4core)
    cfg["num_cores"] = 1
    # Use a 2MB 16-way single-core slice OR keep 8MB? Standard ChampSim 1-core uses 2MB/16-way,
    # OR keep 8MB if measuring contention-free baseline of same cache. Keeping 8192 sets (8MB)
    # isolates cross-core contention + capacity sharing cleanly against the 8MB shared LLC.
    cfg["executable_name"] = f"champsim_1core_{prefetcher}_{policy}"
    cfg["L2C"]["prefetcher"] = prefetcher
    cfg["LLC"]["replacement"] = policy
    return cfg


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(BASE_CFG_PATH, "r") as f:
        base = json.load(f)

    generated = []

    # 4-Core Matched Grids (va_ampm_lite and ip_stride)
    for pf in PREFETCHERS:
        for pol in POLICIES:
            cfg = copy.deepcopy(base)
            cfg["executable_name"] = f"champsim_4core_{pf}_{pol}"
            cfg["L2C"]["prefetcher"] = pf
            cfg["LLC"]["replacement"] = pol
            out_path = OUT_DIR / f"4core_{pf}_{pol}.json"
            with open(out_path, "w") as f:
                json.dump(cfg, f, indent=2)
            generated.append(out_path.name)

    # Prefetcher-OFF sanity check configs (SRRIP vs PA-SRRIP)
    for pol in ["srrip", "rrip_prefetch_aware"]:
        cfg = copy.deepcopy(base)
        cfg["executable_name"] = f"champsim_4core_nopf_{pol}"
        cfg["L2C"]["prefetcher"] = "no"
        cfg["LLC"]["replacement"] = pol
        out_path = OUT_DIR / f"4core_nopf_{pol}.json"
        with open(out_path, "w") as f:
            json.dump(cfg, f, indent=2)
        generated.append(out_path.name)

    # 1-Core Standalone baselines (for true IPC_alone Weighted/Harmonic Speedup)
    for pf in PREFETCHERS:
        cfg_1c = make_1core_from_4core(base, pf, "lru")
        out_path = OUT_DIR / f"1core_{pf}_lru.json"
        with open(out_path, "w") as f:
            json.dump(cfg_1c, f, indent=2)
        generated.append(out_path.name)

    print(f"Generated {len(generated)} matched configs in {OUT_DIR}")


if __name__ == "__main__":
    main()
