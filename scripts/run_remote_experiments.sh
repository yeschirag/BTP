#!/bin/bash
# ==============================================================================
# BTP High-Performance Simulation Suite for Remote Server / GPU Node
# Student: Chirag Sharma (S20240010223) | Guide: Dr. Bheemappa Halavar
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHAMPSIM_DIR="${ROOT_DIR}/ChampSim"
RESULTS_DIR="${ROOT_DIR}/results_remote"

mkdir -p "${RESULTS_DIR}"

echo "=============================================================================="
echo " Starting BTP Experiment Suite on $(hostname) at $(date)"
echo " CPU Cores Available: $(nproc 2>/dev/null || sysctl -n hw.ncpu)"
if command -v nvidia-smi &> /dev/null; then
    echo " GPU Detected:"
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader || true
fi
echo "=============================================================================="

cd "${CHAMPSIM_DIR}"

# Ensure traces exist
if [ ! -d "traces" ] || [ -z "$(ls -A traces/*.xz 2>/dev/null)" ]; then
    echo "[-] Error: traces directory not found or empty in ${CHAMPSIM_DIR}/traces"
    exit 1
fi

WARMUP=1000000
SIM_INST=20000000

echo "[*] Simulation Parameters: Warmup=${WARMUP}, SimInstructions=${SIM_INST}"

# 1. Sync replacement modules into ChampSim/replacement/
echo "[*] Syncing replacement modules into ChampSim/replacement/..."
mkdir -p replacement/lru_prefetch_aware replacement/rrip_prefetch_aware replacement/rrip_prefetch_adaptive
cp -f "${ROOT_DIR}/src/lru_prefetch_aware."* replacement/lru_prefetch_aware/ 2>/dev/null || true
cp -f "${ROOT_DIR}/src/rrip_prefetch_aware."* replacement/rrip_prefetch_aware/ 2>/dev/null || true
cp -f "${ROOT_DIR}/src/rrip_prefetch_adaptive."* replacement/rrip_prefetch_adaptive/ 2>/dev/null || true

# 2. Build Binaries if missing
echo "[*] Verifying & Building Binaries..."
for cfg in champsim_4core_baseline champsim_4core_pa_rrip champsim_4core_pa_adaptive champsim_4core_pa_ampm; do
    if [ ! -f "bin/${cfg}" ]; then
        echo "    Building bin/${cfg}..."
        ./config.sh "${ROOT_DIR}/configs/${cfg}.json"
        rm -f .csconfig/generated_environment.o
        make -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu)" "bin/${cfg}"
    else
        echo "    [OK] bin/${cfg} already built."
    fi
done

# ------------------------------------------------------------------------------
# SECTION 1: 4-Core Heterogeneous Mix (gcc + mcf + perlbench + omnetpp)
# ------------------------------------------------------------------------------
echo ""
echo "=============================================================================="
echo " SECTION 1: 4-Core Heterogeneous Mix (gcc + mcf + perlbench + omnetpp)"
echo "=============================================================================="

echo "[1/4] Running Baseline LRU on Heterogeneous Mix..."
./bin/champsim_4core_baseline -w ${WARMUP} -i ${SIM_INST} \
  traces/403.gcc-16B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/600.perlbench_s-210B.champsimtrace.xz \
  traces/471.omnetpp-188B.champsimtrace.xz > "${RESULTS_DIR}/4core_mix_baseline.txt" 2>&1
echo "      -> Finished Baseline LRU."

echo "[2/4] Running Prefetch-Aware LRU (PA-LRU) on Heterogeneous Mix..."
./bin/champsim_4core_pa_ampm -w ${WARMUP} -i ${SIM_INST} \
  traces/403.gcc-16B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/600.perlbench_s-210B.champsimtrace.xz \
  traces/471.omnetpp-188B.champsimtrace.xz > "${RESULTS_DIR}/4core_mix_pa_lru.txt" 2>&1
echo "      -> Finished PA-LRU."

echo "[3/4] Running Prefetch-Aware SRRIP (PA-SRRIP) on Heterogeneous Mix..."
./bin/champsim_4core_pa_rrip -w ${WARMUP} -i ${SIM_INST} \
  traces/403.gcc-16B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/600.perlbench_s-210B.champsimtrace.xz \
  traces/471.omnetpp-188B.champsimtrace.xz > "${RESULTS_DIR}/4core_mix_pa_rrip.txt" 2>&1
echo "      -> Finished PA-SRRIP."

echo "[4/4] Running PA-Adaptive SRRIP (Dynamic Demotion) on Heterogeneous Mix..."
./bin/champsim_4core_pa_adaptive -w ${WARMUP} -i ${SIM_INST} \
  traces/403.gcc-16B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/600.perlbench_s-210B.champsimtrace.xz \
  traces/471.omnetpp-188B.champsimtrace.xz > "${RESULTS_DIR}/4core_mix_pa_adaptive.txt" 2>&1
echo "      -> Finished PA-Adaptive SRRIP."

# ------------------------------------------------------------------------------
# SECTION 2: 4-Core Pointer Noise Contention Mix (mcf x 4)
# ------------------------------------------------------------------------------
echo ""
echo "=============================================================================="
echo " SECTION 2: 4-Core Noise Contention Stress (mcf x 4)"
echo "=============================================================================="

echo "[1/2] Running PA-SRRIP on mcf x 4..."
./bin/champsim_4core_pa_rrip -w ${WARMUP} -i ${SIM_INST} \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz > "${RESULTS_DIR}/4core_mcf4_pa_rrip.txt" 2>&1
echo "      -> Finished PA-SRRIP (mcf x 4)."

echo "[2/2] Running PA-Adaptive SRRIP on mcf x 4..."
./bin/champsim_4core_pa_adaptive -w ${WARMUP} -i ${SIM_INST} \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz \
  traces/429.mcf-184B.champsimtrace.xz > "${RESULTS_DIR}/4core_mcf4_pa_adaptive.txt" 2>&1
echo "      -> Finished PA-Adaptive SRRIP (mcf x 4)."

echo ""
echo "=============================================================================="
echo " Simulations Completed Successfully at $(date)!"
echo " Results stored in: ${RESULTS_DIR}/"
echo "=============================================================================="
