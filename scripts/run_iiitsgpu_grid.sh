#!/bin/bash
# ==============================================================================
# Bulletproof Parallel ChampSim Grid Runner for iiitsgpu (48 Cores)
# - Matched prefetcher grids (va_ampm_lite & ip_stride)
# - All baselines: LRU, SRRIP, DRRIP, SHiP, PACMan, PA-LRU, PA-SRRIP, PA-Adaptive
# - 1-Core Alone baselines + Prefetcher-OFF equivalence test
# - Clean builds per binary (prevents stale .csconfig / NUM_CPUS mismatches)
# - Python ThreadPool parallel runner (zero xargs/export-f quirks), auto-resume,
#   crash isolation, completion verification, and manifest.json provenance.
# ==============================================================================

set -u

JOBS="${JOBS:-32}"
MODE="${1:-core}" # 'core' (Mix1+Mix2+Alone+Control = 42 jobs, <4h strict) or '--full' (74 jobs)
WARMUP="${WARMUP:-1000000}"
SIM_INST="${SIM_INST:-5000000}"
WARMUP_CTRL="${WARMUP_CTRL:-1000000}"
SIM_CTRL="${SIM_CTRL:-5000000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHAMPSIM_DIR="${ROOT_DIR}/ChampSim"
RESULTS_DIR="${ROOT_DIR}/results_grid"
CFG_DIR="${ROOT_DIR}/configs/grid"

mkdir -p "${RESULTS_DIR}"

# Local user-space libs if present (e.g. iiitsgpu ~/localdeps)
LOCAL_LIB_PATHS=$(find "${HOME}/localdeps" "${HOME}/.local" -type d \( -name "lib" -o -name "lib64" -o -name "stublib" \) 2>/dev/null | tr '\n' ':' || true)
LOCAL_INC_PATHS=$(find "${HOME}/localdeps" "${HOME}/.local" -type d -name "include" 2>/dev/null | tr '\n' ':' || true)
export LIBRARY_PATH="${LOCAL_LIB_PATHS}${HOME}/localdeps/stublib:${HOME}/localdeps/lib:${HOME}/localdeps/lib64:${HOME}/.local/lib:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="${LOCAL_LIB_PATHS}${HOME}/localdeps/stublib:${HOME}/localdeps/lib:${HOME}/localdeps/lib64:${HOME}/.local/lib:${LD_LIBRARY_PATH:-}"
export CPLUS_INCLUDE_PATH="${LOCAL_INC_PATHS}${HOME}/localdeps/include:${HOME}/.local/include:${CPLUS_INCLUDE_PATH:-}"
export C_INCLUDE_PATH="${LOCAL_INC_PATHS}${HOME}/localdeps/include:${HOME}/.local/include:${C_INCLUDE_PATH:-}"
export PATH="${HOME}/localdeps/bin:${HOME}/.local/bin:${PATH}"

# Ensure ChampSim/Makefile includes localdeps/stublib if missing
python3 -c "
import os
mk = '${CHAMPSIM_DIR}/Makefile'
if os.path.exists(mk):
    with open(mk, 'r') as f: s = f.read()
    if 'stublib' not in s:
        s = s.replace('override LDFLAGS  +=', 'override LDFLAGS  += -L' + os.path.expanduser('~/localdeps/stublib') + ' -L' + os.path.expanduser('~/localdeps/lib') + ' -L' + os.path.expanduser('~/localdeps/lib64') + ' -L' + os.path.expanduser('~/.local/lib') + ' ')
        s = s.replace('override CPPFLAGS +=', 'override CPPFLAGS += -I' + os.path.expanduser('~/localdeps/include') + ' -I' + os.path.expanduser('~/.local/include') + ' ')
        with open(mk, 'w') as f: f.write(s)
" 2>/dev/null || true

GIT_COMMIT=$(git -C "${ROOT_DIR}" rev-parse --short HEAD 2>/dev/null || echo "unknown")
NCPU=$(nproc 2>/dev/null || sysctl -n hw.ncpu)

echo "=============================================================================="
echo " BTP Matched Grid Suite on $(hostname) at $(date)"
echo " Git Commit: ${GIT_COMMIT} | CPU Cores: ${NCPU} | Parallel Jobs: ${JOBS} | Mode: ${MODE}"
echo " Warmup=${WARMUP}, SimInstructions=${SIM_INST}"
echo "=============================================================================="

# 1. Generate configs & sync custom modules
python3 "${SCRIPT_DIR}/generate_grid_configs.py" || { echo "[-] Failed to generate grid configs"; exit 1; }

cd "${CHAMPSIM_DIR}" || exit 1

# Verify traces exist before building/running
for tr in traces/403.gcc-16B.champsimtrace.xz traces/429.mcf-184B.champsimtrace.xz traces/600.perlbench_s-210B.champsimtrace.xz traces/471.omnetpp-188B.champsimtrace.xz; do
    if [ ! -s "${tr}" ]; then
        echo "[-] Missing or empty trace: ${CHAMPSIM_DIR}/${tr}"
        exit 1
    fi
done

mkdir -p replacement/lru_prefetch_aware replacement/rrip_prefetch_aware replacement/rrip_prefetch_adaptive replacement/pacman
cp -f "${ROOT_DIR}/src/lru_prefetch_aware."* replacement/lru_prefetch_aware/
cp -f "${ROOT_DIR}/src/rrip_prefetch_aware."* replacement/rrip_prefetch_aware/
cp -f "${ROOT_DIR}/src/rrip_prefetch_adaptive."* replacement/rrip_prefetch_adaptive/
cp -f "${ROOT_DIR}/src/pacman."* replacement/pacman/

# 2. Build all required binaries cleanly
# Run one initial make clean before the first build so stale .csconfig .o files never leak across runs,
# and clean again whenever num_cores switches (1 <-> 4).
LAST_CORES=""
CLEANED_ONCE=0
echo "[*] Building all matched ChampSim binaries..."
for cfg_file in "${CFG_DIR}"/*.json; do
    read -r exec_name num_cores <<< "$(python3 -c "import json; d=json.load(open('${cfg_file}')); print(d['executable_name'], d['num_cores'])")"
    if [ ! -x "bin/${exec_name}" ]; then
        echo "    [+] Building bin/${exec_name} (num_cores=${num_cores})..."
        if [ "${CLEANED_ONCE}" -eq 0 ] || { [ -n "${LAST_CORES}" ] && [ "${LAST_CORES}" != "${num_cores}" ]; }; then
            make clean >/dev/null 2>&1 || true
            CLEANED_ONCE=1
        fi
        rm -f .csconfig/generated_environment.o
        ./config.sh "${cfg_file}" || { echo "[-] config.sh failed for ${exec_name}"; exit 1; }
        make -j"${NCPU}" "bin/${exec_name}" || { echo "[-] make failed for ${exec_name}"; exit 1; }
        LAST_CORES="${num_cores}"
    else
        echo "    [OK] bin/${exec_name} already built."
    fi
done

# 3. Record run metadata manifest
python3 -c "
import json, time
manifest = {
    'git_commit': '${GIT_COMMIT}',
    'hostname': '$(hostname)',
    'started_at': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
    'mode': '${MODE}',
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

# A. Fast 1-Core Alone Baselines & Control FIRST (frees worker slots quickly for 4-core runs)
for pf in "${PREFETCHERS[@]}"; do
    bin="bin/champsim_1core_${pf}_lru"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_gcc.txt|${GCC}" >> "${QUEUE_FILE}"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_mcf.txt|${MCF}" >> "${QUEUE_FILE}"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_perlbench.txt|${PERL}" >> "${QUEUE_FILE}"
    echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/alone_${pf}_omnetpp.txt|${OMNET}" >> "${QUEUE_FILE}"
done

# B. Prefetcher-OFF Equivalence Verification (SRRIP vs PA-SRRIP)
echo "bin/champsim_4core_nopf_srrip|${WARMUP_CTRL}|${SIM_CTRL}|${RESULTS_DIR}/ctrl_nopf_srrip.txt|${GCC} ${MCF} ${PERL} ${OMNET}" >> "${QUEUE_FILE}"
echo "bin/champsim_4core_nopf_rrip_prefetch_aware|${WARMUP_CTRL}|${SIM_CTRL}|${RESULTS_DIR}/ctrl_nopf_pa_rrip.txt|${GCC} ${MCF} ${PERL} ${OMNET}" >> "${QUEUE_FILE}"

# C. Primary 4-Core Matched Grids (Mix 1 Heterogeneous first, then Mix 2 mcfx4)
for pf in "${PREFETCHERS[@]}"; do
    for pol in "${POLICIES[@]}"; do
        bin="bin/champsim_4core_${pf}_${pol}"
        echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix1_het_${pf}_${pol}.txt|${GCC} ${MCF} ${PERL} ${OMNET}" >> "${QUEUE_FILE}"
    done
done

for pf in "${PREFETCHERS[@]}"; do
    for pol in "${POLICIES[@]}"; do
        bin="bin/champsim_4core_${pf}_${pol}"
        echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix2_mcf4_${pf}_${pol}.txt|${MCF} ${MCF} ${MCF} ${MCF}" >> "${QUEUE_FILE}"
        if [ "${MODE}" = "--full" ] || [ "${MODE}" = "full" ]; then
            echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix3_reg4_${pf}_${pol}.txt|${GCC} ${GCC} ${PERL} ${PERL}" >> "${QUEUE_FILE}"
            echo "${bin}|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/mix4_asym_${pf}_${pol}.txt|${MCF} ${MCF} ${OMNET} ${GCC}" >> "${QUEUE_FILE}"
        fi
    done
done

# 5. Execute queue with Python ThreadPoolExecutor (no xargs/export-f portability pitfalls)
python3 - "${QUEUE_FILE}" "${JOBS}" <<'PYEOF'
import sys
import os
import time
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

queue_file = sys.argv[1]
max_workers = int(sys.argv[2])

with open(queue_file) as f:
    jobs = [line.strip().split("|") for line in f if line.strip()]

total = len(jobs)
print(f"[*] Executing {total} jobs with max_workers={max_workers}", flush=True)

def run_job(idx, entry):
    bin_path, w, i, out_path, traces_str = entry
    bname = os.path.basename(out_path)
    if os.path.exists(out_path):
        try:
            with open(out_path, "r", errors="replace") as rf:
                if "ChampSim completed all CPUs" in rf.read():
                    return (bname, True, "SKIP-OK", 0.0)
        except OSError:
            pass

    cmd = [bin_path, "-w", w, "-i", i] + shlex.split(traces_str)
    t0 = time.time()
    print(f"[START {time.strftime('%H:%M:%S')}] ({idx}/{total}) {bname}", flush=True)
    with open(out_path, "w") as wf:
        proc = subprocess.run(cmd, stdout=wf, stderr=subprocess.STDOUT)
    dt = time.time() - t0

    ok = False
    if proc.returncode == 0 and os.path.exists(out_path):
        with open(out_path, "r", errors="replace") as rf:
            ok = "ChampSim completed all CPUs" in rf.read()
    status = "DONE" if ok else f"FAIL(rc={proc.returncode})"
    return (bname, ok, status, dt)

passed = 0
failed = []
with ThreadPoolExecutor(max_workers=max_workers) as ex:
    futs = {ex.submit(run_job, idx + 1, j): j for idx, j in enumerate(jobs)}
    done_cnt = 0
    for fut in as_completed(futs):
        done_cnt += 1
        bname, ok, status, dt = fut.result()
        if ok:
            passed += 1
        else:
            failed.append((bname, status))
        print(f"[{status:12s} {time.strftime('%H:%M:%S')}] ({done_cnt}/{total}) {bname} ({dt/60:.1f} min)", flush=True)

print("\n==============================================================================", flush=True)
print(f" Suite Finished at {time.strftime('%Y-%m-%d %H:%M:%S %Z')}", flush=True)
print(f" Passed: {passed} / {total}", flush=True)
if failed:
    print(" Failed jobs:", flush=True)
    for bname, st in failed:
        print(f"   - {bname}: {st}", flush=True)
print("==============================================================================", flush=True)
PYEOF
