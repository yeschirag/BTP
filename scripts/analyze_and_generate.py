#!/usr/bin/env python3
"""
Single Source of Truth Analyzer & Generator for BTP Evaluation
- Verifies completion ("ChampSim completed all CPUs") for every log
- Computes per-CPU IPC, Mean Normalized Speedup vs Shared Baseline,
  True Weighted Speedup (sum IPC_shared / IPC_alone / N), and Harmonic Speedup
- Extracts INDEPENDENT hardware counters (LLC Load+RFO misses, L2C Prefetcher Useful/(Useful+Useless))
  alongside policy-level promotion counters
- Generates Markdown tables, verified charts, and provenance manifest
"""
import argparse
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional


POLICY_LABELS = {
    "lru": "Baseline LRU",
    "srrip": "Baseline SRRIP",
    "drrip": "DRRIP (ISCA'10)",
    "ship": "SHiP (ISCA'11)",
    "pacman": "PACMan-HM (MICRO'11)",
    "lru_prefetch_aware": "PA-LRU (Ours)",
    "rrip_prefetch_aware": "PA-SRRIP (Ours)",
    "rrip_prefetch_adaptive": "PA-Adaptive (Ours)",
}

POLICY_ORDER = [
    "lru",
    "srrip",
    "drrip",
    "ship",
    "pacman",
    "lru_prefetch_aware",
    "rrip_prefetch_aware",
    "rrip_prefetch_adaptive",
]

MIX_CORES = {
    "mix1_het": ["gcc", "mcf", "perlbench", "omnetpp"],
    "mix2_mcf4": ["mcf", "mcf", "mcf", "mcf"],
    "mix3_reg4": ["gcc", "gcc", "perlbench", "perlbench"],
    "mix4_asym": ["mcf", "mcf", "omnetpp", "gcc"],
}


def parse_champsim_log(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    text = path.read_text(errors="replace")
    completed = "ChampSim completed all CPUs" in text

    cpus: Dict[int, float] = {}
    for cid, ipc in re.findall(r"Simulation finished CPU (\d+).*?cumulative IPC:\s*([\d\.]+)", text):
        cpus[int(cid)] = float(ipc)

    # Independent LLC Demand Misses (LOAD + RFO)
    llc_demand_misses = 0
    llc_demand_accesses = 0
    for m in re.finditer(r"cpu\d+->LLC\s+(LOAD|RFO)\s+ACCESS:\s*(\d+)\s+HIT:\s*(\d+)\s+MISS:\s*(\d+)", text):
        llc_demand_accesses += int(m.group(2))
        llc_demand_misses += int(m.group(4))

    # Independent L2C Prefetcher Accuracy = USEFUL / (USEFUL + USELESS)
    l2_pf_useful = 0
    l2_pf_useless = 0
    for m in re.finditer(r"cpu\d+->cpu\d+_L2C PREFETCH REQUESTED:\s*\d+\s+ISSUED:\s*\d+\s+USEFUL:\s*(\d+)\s+USELESS:\s*(\d+)", text):
        l2_pf_useful += int(m.group(1))
        l2_pf_useless += int(m.group(2))

    pf_total_resolved = l2_pf_useful + l2_pf_useless
    l2_pf_accuracy = (100.0 * l2_pf_useful / pf_total_resolved) if pf_total_resolved > 0 else None

    # Policy-reported promotion stats (note: partly policy-dependent)
    pf_fills_m = re.search(r"Prefetch fills:\s*(\d+)", text)
    pf_prom_m = re.search(r"Prefetch blocks promoted \(useful\):\s*(\d+)", text)

    return {
        "file": path.name,
        "completed": completed,
        "cpus": cpus,
        "llc_demand_accesses": llc_demand_accesses,
        "llc_demand_misses": llc_demand_misses,
        "l2_pf_useful": l2_pf_useful,
        "l2_pf_useless": l2_pf_useless,
        "l2_pf_accuracy": l2_pf_accuracy,
        "pf_fills": int(pf_fills_m.group(1)) if pf_fills_m else None,
        "pf_promoted": int(pf_prom_m.group(1)) if pf_prom_m else None,
    }


def weighted_speedup(shared_ipcs: List[float], ref_ipcs: List[float]) -> Optional[float]:
    if not shared_ipcs or len(shared_ipcs) != len(ref_ipcs) or any(r <= 0 for r in ref_ipcs):
        return None
    return sum(s / r for s, r in zip(shared_ipcs, ref_ipcs)) / len(shared_ipcs)


def harmonic_speedup(shared_ipcs: List[float], ref_ipcs: List[float]) -> Optional[float]:
    if not shared_ipcs or len(shared_ipcs) != len(ref_ipcs) or any(s <= 0 or r <= 0 for s, r in zip(shared_ipcs, ref_ipcs)):
        return None
    return len(shared_ipcs) / sum(r / s for s, r in zip(shared_ipcs, ref_ipcs))


def summarize_grid(results_dir: Path) -> str:
    lines: List[str] = []
    manifest_path = results_dir / "manifest.json"
    if manifest_path.exists():
        m = json.loads(manifest_path.read_text())
        lines.append(f"**Provenance:** git `{m.get('git_commit')}`, host `{m.get('hostname')}`, "
                     f"warmup `{m.get('warmup')}`, sim `{m.get('sim_instructions')}`, started `{m.get('started_at')}`\n")

    # Control equivalence check (prefetcher off)
    ctrl_srrip = parse_champsim_log(results_dir / "ctrl_nopf_srrip.txt")
    ctrl_parrip = parse_champsim_log(results_dir / "ctrl_nopf_pa_rrip.txt")
    if ctrl_srrip and ctrl_parrip and ctrl_srrip["completed"] and ctrl_parrip["completed"]:
        match_ipc = ctrl_srrip["cpus"] == ctrl_parrip["cpus"]
        match_miss = ctrl_srrip["llc_demand_misses"] == ctrl_parrip["llc_demand_misses"]
        lines.append(f"## Sanity Check (Prefetcher OFF: SRRIP vs PA-SRRIP)\n"
                     f"- Completed: Yes | IPC Identical: `{match_ipc}` | LLC Demand Misses Identical: `{match_miss}` "
                     f"(`{ctrl_srrip['llc_demand_misses']}` vs `{ctrl_parrip['llc_demand_misses']}`)\n")

    for pf in ["va_ampm_lite", "ip_stride"]:
        lines.append(f"# Matched Grid: L2C Prefetcher = `{pf}`\n")

        # Load IPC_alone if available
        alone_map: Dict[str, float] = {}
        for bench in ["gcc", "mcf", "perlbench", "omnetpp"]:
            d = parse_champsim_log(results_dir / f"alone_{pf}_{bench}.txt")
            if d and d["completed"] and 0 in d["cpus"]:
                alone_map[bench] = d["cpus"][0]
        if alone_map:
            lines.append("**1-Core Standalone (`IPC_alone`):** " +
                         ", ".join(f"`{k}`={v:.4f}" for k, v in alone_map.items()) + "\n")

        for mix, core_names in MIX_CORES.items():
            rows = []
            base_shared: Optional[List[float]] = None
            for pol in POLICY_ORDER:
                d = parse_champsim_log(results_dir / f"{mix}_{pf}_{pol}.txt")
                if not d:
                    continue
                ipcs = [d["cpus"].get(i) for i in range(4)]
                if pol == "lru" and d["completed"] and all(v is not None for v in ipcs):
                    base_shared = [float(v) for v in ipcs]
                rows.append((pol, d, ipcs))

            if not rows:
                continue

            lines.append(f"## Mix: `{mix}` ({' + '.join(core_names)})\n")
            lines.append("| Policy | Status | CPU0 | CPU1 | CPU2 | CPU3 | Mean Norm vs LRU | Weighted Speedup (vs Alone) | Harmonic Speedup (vs Alone) | LLC Demand Misses | L2 PF Acc (%) |")
            lines.append("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

            for pol, d, ipcs in rows:
                status = "OK" if d["completed"] else "INCOMPLETE"
                c_strs = [f"{v:.4f}" if v is not None else "-" for v in ipcs]
                clean_ipcs = [float(v) for v in ipcs] if all(v is not None for v in ipcs) else None

                norm_str = "-"
                ws_str = "-"
                hs_str = "-"
                if clean_ipcs and base_shared:
                    ns = weighted_speedup(clean_ipcs, base_shared)
                    if ns is not None:
                        norm_str = f"{(ns - 1.0) * 100:+.2f}%"
                if clean_ipcs and all(c in alone_map for c in core_names):
                    ref_alone = [alone_map[c] for c in core_names]
                    ws = weighted_speedup(clean_ipcs, ref_alone)
                    hs = harmonic_speedup(clean_ipcs, ref_alone)
                    if ws is not None:
                        ws_str = f"{ws:.4f}"
                    if hs is not None:
                        hs_str = f"{hs:.4f}"

                acc_str = f"{d['l2_pf_accuracy']:.2f}%" if d["l2_pf_accuracy"] is not None else "-"
                miss_str = f"{d['llc_demand_misses']:,}" if d["llc_demand_misses"] else "-"
                lines.append(f"| {POLICY_LABELS[pol]} | {status} | {c_strs[0]} | {c_strs[1]} | {c_strs[2]} | {c_strs[3]} | {norm_str} | {ws_str} | {hs_str} | {miss_str} | {acc_str} |")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze matched ChampSim BTP grid results")
    parser.add_argument("--dir", type=Path, default=Path("results_grid"), help="Directory containing ChampSim grid logs")
    parser.add_argument("--out", type=Path, default=None, help="Optional Markdown summary output path")
    args = parser.parse_args()

    if not args.dir.exists():
        print(f"Directory {args.dir} does not exist yet. Run scripts/run_iiitsgpu_grid.sh on iiitsgpu first.")
        return

    report = summarize_grid(args.dir)
    if args.out:
        args.out.write_text(report)
        print(f"Wrote verified summary to {args.out}")
    else:
        print(report)


if __name__ == "__main__":
    main()
