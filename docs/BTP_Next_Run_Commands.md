# Next Run Commands

## Current Status
- `make -j24` completed successfully.
- The next step is to run the built ChampSim binary and save the output.

## 4-Core `va_ampm_lite` Run

```bash
cd ~/BTP/ChampSim
mkdir -p results

./bin/champsim_4core_pa_ampm -w 500000 -i 5000000 \
traces/403.gcc-16B.champsimtrace.xz \
traces/429.mcf-184B.champsimtrace.xz \
traces/600.perlbench_s-210B.champsimtrace.xz \
traces/471.omnetpp-188B.champsimtrace.xz \
> results/mc_pa_ampm_mix1.txt 2>&1
```

## Check Output

```bash
tail -n 30 results/mc_pa_ampm_mix1.txt
```

## Build Reminder
- If you edit the JSON again, regenerate and rebuild:

```bash
rm -rf .csconfig
./config.sh champsim_4core_pa_ampm.json
make -j24
```

## What This File Is For
- Keep the exact command for the current evaluation run.
- Store the run output under `results/` for later comparison with baseline and other prefetchers.
