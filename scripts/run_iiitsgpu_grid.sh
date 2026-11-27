#!/bin/bash
# ==============================================================================
# Bulletproof Parallel ChampSim Grid Runner for iiitsgpu (48 Cores)
# - Matched prefetcher grids (va_ampm_lite & ip_stride)
# - All baselines: LRU, SRRIP, DRRIP, SHiP, PACMan, PA-LRU, PA-SRRIP, PA-Adaptive
# - 4 Workload Mixes + 1-Core Alone baselines + Prefetcher-OFF equivalence test
# - Parallel job throttling (JOBS=12), auto-resume, crash isolation (no set -e!),
#   completion verification, and manifest.json provenance tracking.
# ==============================================================================

set -u

JOBS="${JOBS:-14}"
MODE="${1:-core}" # 'core' (Mix1+Mix2+Alone+Control = 42 jobs) or '--full' (all 4 mixes = 74 jobs)
WARMUP="${WARMUP:-2000000}"
SIM_INST="${SIM_INST:-20000000}"
WARMUP_CTRL="${WARMUP_CTRL:-1000000}"
SIM_CTRL="${SIM_CTRL:-10000000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHAMPSIM_DIR="${ROOT_DIR}/ChampSim"
RESULTS_DIR="${ROOT_DIR}/results_grid"
LOG_DIR="${RESULTS_DIR}/logs"
CFG_DIR="${ROOT_DIR}/configs/grid"

mkdir -p "${RESULTS_DIR}" "${LOG_DIR}"

# Local user-space libs if present
LOCAL_LIB_PATHS=$(find "${HOME}/localdeps" "${HOME}/.local" -type d \( -name "lib" -o -name "lib64" -o -name "stublib" \) 2>/dev/null | tr '\n' ':' || true)
LOCAL_INC_PATHS=$(find "${HOME}/localdeps" "${HOME}/.local" -type d -name "include" 2>/dev/null | tr '\n' ':' || true)
export LIBRARY_PATH="${LOCAL_LIB_PATHS}${HOME}/localdeps/stublib:${HOME}/localdeps/lib:${HOME}/localdeps/lib64:${HOME}/.local/lib:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="${LOCAL_LIB_PATHS}${HOME}/localdeps/stublib:${HOME}/localdeps/lib:${HOME}/localdeps/lib64:${HOME}/.local/lib:${LD_LIBRARY_PATH:-}"
export CPLUS_INCLUDE_PATH="${LOCAL_INC_PATHS}${HOME}/localdeps/include:${HOME}/.local/include:${CPLUS_INCLUDE_PATH:-}"
export C_INCLUDE_PATH="${LOCAL_INC_PATHS}${HOME}/localdeps/include:${HOME}/.local/include:${C_INCLUDE_PATH:-}"
export PATH="${HOME}/localdeps/bin:${HOME}/.local/bin:${PATH}"

GIT_COMMIT=$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "=============================================================================="
echo " BTP Matched Grid Suite on $(hostname) at $(date)"
echo " Git Commit: ${GIT_COMMIT} | CPU Cores: $(nproc 2>/dev/null || sysctl -n hw.ncpu) | Max Parallel Jobs: ${JOBS}"
echo " Warmup=${WARMUP}, SimInstructions=${SIM_INST}"
echo "=============================================================================="

# 1. Generate configs & sync custom modules
python3 "${SCRIPT_DIR}/generate_grid_configs.py"

cd "${CHAMPSIM_DIR}" || exit 1
mkdir -p replacement/lru_prefetch_aware replacement/rrip_prefetch_aware replacement/rrip_prefetch_adaptive replacement/pacman
cp -f "${ROOT_DIR}/src/lru_prefetch_aware."* replacement/lru_prefetch_aware/
cp -f "${ROOT_DIR}/src/rrip_prefetch_aware."* replacement/rrip_prefetch_aware/
cp -f "${ROOT_DIR}/src/rrip_prefetch_adaptive."* replacement/rrip_prefetch_adaptive/
cp -f "${ROOT_DIR}/src/pacman."* replacement/pacman/

# 2. Build all required binaries cleanly sequentially
NCPU=$(nproc 2>/dev/null || sysctl -n hw.ncpu)
echo "[*] Building all matched ChampSim binaries..."
for cfg_file in "${CFG_DIR}"/*.json; do
    exec_name=$(python3 -c "import json; print(json.load(open('${cfg_file}'))['executable_name'])")
    if [ ! -x "bin/${exec_name}" ]; then
        echo "    [+] Building bin/${exec_name}..."
        find .csconfig -maxdepth 1 \( -name "*main.o" -o -name "generated_environment.o" \) -delete 2>/dev/null || true
        ./config.sh "${cfg_file}" || { echo "[-] config.sh failed for ${exec_name}"; exit 1; }
        find .csconfig -maxdepth 1 \( -name "*main.o" -o -name "generated_environment.o" \) -delete 2>/dev/null || true
        make -j"${NCPU}" "bin/${exec_name}" || { echo "[-] make failed for ${exec_name}"; exit 1; }
    else
        echo "    [OK] bin/${exec_name} ready."
    fi
done

# 3. Record run metadata manifest
python3 -c "
import json, time
manifest = {
    'git_commit': '${GIT_COMMIT}',
    'hostname': '$(hostname)',
    'started_at': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
    'warmup': ${WARMUP},
    'sim_instructions': ${SIM_INST},
    'max_jobs': ${JOBS}
}
with open('${RESULTS_DIR}/manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2)
"

# 4. Build job queue
QUEUE_FILE="${RESULTS_DIR}/job_queue.txt"
: > "${QUEUE_FILE}"

GCC="traces/403.gcc-16B.champsimtrace.xz"
MCF="traces/429.mcf-184B.champsimtrace.xz"
PERL="traces/600.perlbench_s-210B.champsimtrace.xz"
OMNET="traces/471.omnetpp-188B.champsimtrace.xz"

POLICIES=(lru srrip drrip ship pacman lru_prefetch_aware rrip_prefetch_aware rrip_prefetch_adaptive)
PREFETCHERS=(va_ampm_lite ip_stride)

# A. Primary 4-Core Matched Grids
for pf in "${PREFETCHERS[@]}"; do
    for pol in "${POLICIES[@]}"; do
        bin="bin/champsim_4core_${pf}_${pol}"
        echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix1_het_${pf}_${pol}.txt|${GCC} ${MCF} ${PERL} ${OMNET}" >> "${QUEUE_FILE}"
        echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix2_mcf4_${pf}_${pol}.txt|${MCF} ${MCF} ${MCF} ${MCF}" >> "${QUEUE_FILE}"
        if [ "${MODE}" = "--full" ] || [ "${MODE}" = "full" ]; then
            echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix3_reg4_${pf}_${pol}.txt|${GCC} ${GCC} ${PERL} ${PERL}" >> "${QUEUE_FILE}"
            echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix4_asym_${pf}_${pol}.txt|${MCF} ${MCF} ${OMNET} ${GCC}" >> "${QUEUE_FILE}"
        fi
    done
done

# B. 1-Core Standalone Alone Baselines (for True Weighted & Harmonic Speedup)
for pf in "${PREFETCHERS[@]}"; do
    bin="bin/champsim_1core_${pf}_lru"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_gcc.txt|${GCC}" >> "${QUEUE_FILE}"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_mcf.txt|${MCF}" >> "${QUEUE_FILE}"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_perlbench.txt|${PERL}" >> "${QUEUE_FILE}"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_omnetpp.txt|${OMNET}" >> "${QUEUE_FILE}"
done

# C. Prefetcher-OFF Equivalence Verification (SRRIP vs PA-SRRIP)
echo "bin/champsim_4core_nopf_srrip|${WARMUP_CTRL}|${SIM_CTRL}|${RESULTS_DIR}/ctrl_nopf_srrip.txt|${GCC} ${MCF} ${PERL} ${OMNET}" >> "${QUEUE_FILE}"
echo "bin/champsim_4core_nopf_rrip_prefetch_aware|${WARMUP_CTRL}|${SIM_CTRL}|${RESULTS_DIR}/ctrl_nopf_pa_rrip.txt|${GCC} ${MCF} ${PERL} ${OMNET}" >> "${QUEUE_FILE}"

TOTAL_JOBS=$(wc -l < "${QUEUE_FILE}" | tr -d ' ')
echo "[*] Total queued simulation jobs: ${TOTAL_JOBS}"

run_one_job() {
    local line="$1"
    IFS='|' read -r bin w i out traces <<< "${line}"
    local bname
    bname=$(basename "${out}")

    # Skip if already completed cleanly
    if [ -f "${out}" ] && grep -q "ChampSim completed all CPUs" "${out}" 2>/dev/null; then
        echo "[SKIP-OK] ${bname} already complete."
        return 0
    fi

    echo "[START $(date '+%H:%M:%S')] ${bname}"
    # shellcheck disable=SC2086
    "${bin}" -w "${w}" -i "${i}" ${traces} > "${out}" 2>&1
    local rc=$?
    if [ $rc -eq 0 ] && grep -q "ChampSim completed all CPUs" "${out}" 2>/dev/null; then
        echo "[DONE  $(date '+%H:%M:%S')] ${bname} (OK)"
    else
        echo "[FAIL  $(date '+%H:%M:%S')] ${bname} (rc=${rc})" >&2
    fi
}

export -f run_one_job

# Launch parallel pool using xargs -P (portable across Linux & macOS)
xargs -P "${JOBS}" -I {} bash -c 'run_one_job "$@"' _ {} < "${QUEUE_FILE}"

echo ""
echo "=============================================================================="
echo " Suite Finished at $(date)"
DONE_CNT=$(grep -l "ChampSim completed all CPUs" "${RESULTS_DIR}"/*.txt 2>/dev/null | wc -l | tr -d ' ')
echo " Completed Cleanly: ${DONE_CNT} / ${TOTAL_JOBS}"
echo "=============================================================================="
