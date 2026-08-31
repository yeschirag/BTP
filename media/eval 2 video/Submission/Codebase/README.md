# BTP — Code used in ChampSim implementation

Purpose
- Minimal set of source and config files required to reproduce the replacement-policy experiments used in the project.

Included files
- `lru_prefetch_aware.cc`: ChampSim replacement policy implementation (source).
- `lru_prefetch_aware.h`: Header for the replacement module.
- `champsim_prefetch_aware.json`: Single-core ChampSim config used for experiments.
- `champsim_4core_prefetch_aware.json`: 4-core shared-LLC config used in multicore experiments.

Quick usage
1. Copy `lru_prefetch_aware.cc` and `lru_prefetch_aware.h` into your local ChampSim replacement modules directory (e.g., `modules/replacement/` or appropriate location in your ChampSim fork).
2. In WSL (Ubuntu) from your ChampSim root:

```bash
./config.sh champsim_prefetch_aware.json
make
```

3. Run the binary with a trace (example):

```bash
./bin/champsim_prefetch_aware --warmup 500000 --simulation 5000000 traces/403.gcc-16B.champsimtrace.xz
```

Notes
- The JSON configs included point to the simulator settings used in our evaluation (prefetcher enabled and LLC parameters). Adjust trace path and warmup/simulation counts as needed.