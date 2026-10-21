#!/usr/bin/env python3
import sys
import re
import os

def parse_log(filepath):
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'r') as f:
        content = f.read()

    data = {
        'filename': os.path.basename(filepath),
        'cpus': {},
        'llc_prefetch_fills': None,
        'llc_demand_fills': None,
        'llc_promoted': None,
        'llc_usefulness': None
    }

    matches = re.findall(r'Simulation finished CPU (\d+).*?cumulative IPC:\s*([\d\.]+)', content)
    for cpu_id, ipc in matches:
        data['cpus'][int(cpu_id)] = float(ipc)

    # Match LLC stats
    pf_match = re.search(r'Prefetch fills:\s*(\d+)', content)
    df_match = re.search(r'Demand fills:\s*(\d+)', content)
    prom_match = re.search(r'Prefetch blocks promoted \(useful\):\s*(\d+)', content)
    use_match = re.search(r'Prefetch usefulness:\s*([\d\.]+)%', content)

    if pf_match: data['llc_prefetch_fills'] = int(pf_match.group(1))
    if df_match: data['llc_demand_fills'] = int(df_match.group(1))
    if prom_match: data['llc_promoted'] = int(prom_match.group(1))
    if use_match: data['llc_usefulness'] = float(use_match.group(1))

    return data

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 parse_results.py <log1.txt> [log2.txt ...]")
        sys.exit(1)

    print("| Log File | CPU 0 IPC (gcc) | CPU 1 IPC (mcf) | CPU 2 IPC (perl) | CPU 3 IPC (omnet) | Prefetch Fills | Useful Promoted | Usefulness (%) |")
    print("|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|")

    for path in sys.argv[1:]:
        d = parse_log(path)
        if not d:
            continue
        c0 = f"{d['cpus'].get(0, 0.0):.4f}" if 0 in d['cpus'] else "-"
        c1 = f"{d['cpus'].get(1, 0.0):.4f}" if 1 in d['cpus'] else "-"
        c2 = f"{d['cpus'].get(2, 0.0):.4f}" if 2 in d['cpus'] else "-"
        c3 = f"{d['cpus'].get(3, 0.0):.4f}" if 3 in d['cpus'] else "-"
        pf = str(d['llc_prefetch_fills']) if d['llc_prefetch_fills'] is not None else "-"
        prom = str(d['llc_promoted']) if d['llc_promoted'] is not None else "-"
        use = f"{d['llc_usefulness']:.2f}%" if d['llc_usefulness'] is not None else "-"
        print(f"| `{d['filename']}` | {c0} | {c1} | {c2} | {c3} | {pf} | {prom} | {use} |")

if __name__ == "__main__":
    main()
