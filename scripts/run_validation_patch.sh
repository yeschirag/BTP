#!/bin/bash
# ==============================================================================
# Fast Validation Patch (~15-35 min on iiitsgpu with JOBS=7):
# 1. Writeback-guarded SRRIP (matches PA-SRRIP/DRRIP/SHiP WRITE handling):
#    - ctrl_nopf_srrip_guarded (proves bit-exact equivalence with PA-SRRIP when PF=OFF)
#    - mix1_het under va_ampm_lite & ip_stride (isolates pure PF-awareness vs WRITE guard)
# 2. Instrumented PA-Adaptive: logs Final Counter (C) and % PF fills in Streaming Mode (>=32)
# ==============================================================================
set -u

JOBS="${JOBS:-7}"
WARMUP="${WARMUP:-1000000}"
SIM_INST="${SIM_INST:-5000000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CHAMPSIM_DIR="${ROOT_DIR}/ChampSim"
RESULTS_DIR="${ROOT_DIR}/results_grid"
CFG_DIR="${ROOT_DIR}/configs/grid"

mkdir -p "${RESULTS_DIR}" "${CFG_DIR}"

LOCAL_LIB_PATHS=$(find "${HOME}/localdeps" "${HOME}/.local" -type d \( -name "lib" -o -name "lib64" -o -name "stublib" \) 2>/dev/null | tr '\n' ':' || true)
LOCAL_INC_PATHS=$(find "${HOME}/localdeps" "${HOME}/.local" -type d -name "include" 2>/dev/null | tr '\n' ':' || true)
export LIBRARY_PATH="${LOCAL_LIB_PATHS}${HOME}/localdeps/stublib:${HOME}/localdeps/lib:${HOME}/localdeps/lib64:${HOME}/.local/lib:${LIBRARY_PATH:-}"
export LD_LIBRARY_PATH="${LOCAL_LIB_PATHS}${HOME}/localdeps/stublib:${HOME}/localdeps/lib:${HOME}/localdeps/lib64:${HOME}/.local/lib:${LD_LIBRARY_PATH:-}"
export CPLUS_INCLUDE_PATH="${LOCAL_INC_PATHS}${HOME}/localdeps/include:${HOME}/.local/include:${CPLUS_INCLUDE_PATH:-}"
export C_INCLUDE_PATH="${LOCAL_INC_PATHS}${HOME}/localdeps/include:${HOME}/.local/include:${C_INCLUDE_PATH:-}"
export PATH="${HOME}/localdeps/bin:${HOME}/.local/bin:${PATH}"

# 1. Generate 3 srrip_guarded configs from base
python3 - <<PYEOF
import json, copy
from pathlib import Path

base = json.loads(Path("${ROOT_DIR}/configs/champsim_4core_pa_rrip.json").read_text())
out_dir = Path("${CFG_DIR}")
for pf, tag in [("va_ampm_lite", "va_ampm_lite"), ("ip_stride", "ip_stride"), ("no", "nopf")]:
    c = copy.deepcopy(base)
    c["executable_name"] = f"champsim_4core_{tag}_srrip_guarded"
    c["L2C"]["prefetcher"] = pf
    c["LLC"]["replacement"] = "srrip_guarded"
    (out_dir / f"4core_{tag}_srrip_guarded.json").write_text(json.dumps(c, indent=2))
print("[*] Generated 3 srrip_guarded configs.")
PYEOF

cd "${CHAMPSIM_DIR}" || exit 1
NCPU=$(nproc 2>/dev/null || sysctl -n hw.ncpu)

mkdir -p replacement/srrip_guarded replacement/rrip_prefetch_adaptive
cp -f "${ROOT_DIR}/src/srrip_guarded."* replacement/srrip_guarded/
cp -f "${ROOT_DIR}/src/rrip_prefetch_adaptive."* replacement/rrip_prefetch_adaptive/

# Clean before building to guarantee fresh adaptive telemetry & srrip_guarded
make clean >/dev/null 2>&1 || true

for cfg in \
    "${CFG_DIR}/4core_va_ampm_lite_srrip_guarded.json" \
    "${CFG_DIR}/4core_ip_stride_srrip_guarded.json" \
    "${CFG_DIR}/4core_nopf_srrip_guarded.json" \
    "${CFG_DIR}/4core_va_ampm_lite_rrip_prefetch_adaptive.json" \
    "${CFG_DIR}/4core_ip_stride_rrip_prefetch_adaptive.json"; do
    exec_name=$(python3 -c "import json; print(json.load(open('${cfg}'))['executable_name'])")
    echo "[+] Building bin/${exec_name}..."
    rm -f .csconfig/generated_environment.o
    ./config.sh "${cfg}" || exit 1
    make -j"${NCPU}" "bin/${exec_name}" || exit 1
done

GCC="traces/403.gcc-16B.champsimtrace.xz"
MCF="traces/429.mcf-184B.champsimtrace.xz"
PERL="traces/600.perlbench_s-210B.champsimtrace.xz"
OMNET="traces/471.omnetpp-188B.champsimtrace.xz"

QUEUE="${RESULTS_DIR}/validation_queue.txt"
cat > "${QUEUE}" <<EOF
bin/champsim_4core_nopf_srrip_guarded|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_nopf_srrip_guarded.txt|${GCC} ${MCF} ${PERL} ${OMNET}
bin/champsim_4core_va_ampm_lite_srrip_guarded|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_mix1_va_ampm_lite_srrip_guarded.txt|${GCC} ${MCF} ${PERL} ${OMNET}
bin/champsim_4core_ip_stride_srrip_guarded|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_mix1_ip_stride_srrip_guarded.txt|${GCC} ${MCF} ${PERL} ${OMNET}
bin/champsim_4core_va_ampm_lite_rrip_prefetch_adaptive|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_mix1_va_ampm_lite_pa_adaptive_logged.txt|${GCC} ${MCF} ${PERL} ${OMNET}
bin/champsim_4core_ip_stride_rrip_prefetch_adaptive|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_mix1_ip_stride_pa_adaptive_logged.txt|${GCC} ${MCF} ${PERL} ${OMNET}
bin/champsim_4core_va_ampm_lite_rrip_prefetch_adaptive|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_mix2_va_ampm_lite_pa_adaptive_logged.txt|${MCF} ${MCF} ${MCF} ${MCF}
bin/champsim_4core_ip_stride_rrip_prefetch_adaptive|${WARMUP}|${SIM_INST}|${RESULTS_DIR}/val_mix2_ip_stride_pa_adaptive_logged.txt|${MCF} ${MCF} ${MCF} ${MCF}
EOF

python3 - "${QUEUE}" "${JOBS}" <<'PYEOF'
import sys, os, time, shlex, subprocess, re
from concurrent.futures import ThreadPoolExecutor, as_completed

with open(sys.argv[1]) as f:
    jobs = [l.strip().split("|") for l in f if l.strip()]

def run_one(entry):
    b, w, i, out, tr = entry
    t0 = time.time()
    print(f"[START {time.strftime('%H:%M:%S')}] {os.path.basename(out)}", flush=True)
    with open(out, "w") as wf:
        p = subprocess.run([b, "-w", w, "-i", i] + shlex.split(tr), stdout=wf, stderr=subprocess.STDOUT)
    dt = (time.time() - t0) / 60.0
    txt = open(out, errors="replace").read()
    ok = (p.returncode == 0 and "ChampSim completed all CPUs" in txt)
    print(f"[{'DONE' if ok else 'FAIL'}  {time.strftime('%H:%M:%S')}] {os.path.basename(out)} ({dt:.1f} min)", flush=True)
    return out, txt

with ThreadPoolExecutor(max_workers=int(sys.argv[2])) as ex:
    results = [f.result() for f in as_completed([ex.submit(run_one, j) for j in jobs])]

print("\n=== VALIDATION SUMMARY ===")
for out, txt in sorted(results):
    ipcs = re.findall(r"Simulation finished CPU \d+.*?cumulative IPC:\s*([\d\.]+)", txt)
    misses = sum(int(m.group(1)) for m in re.finditer(r"cpu\d+->LLC\s+(?:LOAD|RFO)\s+ACCESS:\s*\d+\s+HIT:\s*\d+\s+MISS:\s*(\d+)", txt))
    cnt = re.search(r"Final Confidence Counter:\s*(\d+ / 63)", txt)
    frac = re.search(r"Fraction of PF fills in Streaming Mode:\s*([\d\.]+%)", txt)
    extra = f" | Counter={cnt.group(1)}, Streaming={frac.group(1)}" if (cnt and frac) else ""
    print(f"{os.path.basename(out)}: IPCs={ipcs} | LLC_Demand_Misses={misses}{extra}")
PYEOF
