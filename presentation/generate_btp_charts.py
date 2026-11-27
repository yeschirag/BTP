#!/usr/bin/env python3
"""
Generate cohesive ISCA/MICRO-style Matplotlib charts directly from verified
iiitsgpu ChampSim matched grid results (results/iiitsgpu_grid_a341cc5.json).
"""
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "results" / "iiitsgpu_grid_a341cc5.json"
OUT_DIR = Path(__file__).resolve().parent

with open(DATA_PATH, "r") as f:
    DATA = json.load(f)

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Fira Sans", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
})

# Cohesive academic slate/navy/steel/teal palette
C_AMPM = "#1E3A8A"   # Deep Navy
C_IP   = "#0F766E"   # Deep Slate Teal
C_ALT  = "#64748B"   # Cool Slate
C_OURS = "#2563EB"   # Crisp Royal Blue
C_SOTA = "#0F172A"   # Obsidian Navy

LABELS = ["LRU", "SRRIP", "DRRIP", "SHiP\n(2KB)", "PACMan\n-HM", "PA-LRU\n(Ours)", "PA-SRRIP\n(Ours)", "PA-Adapt\n(Ours)"]


def make_mix_chart(mix_key: str, title: str, ylim: tuple, out_name: str, legend_loc="upper left"):
    ampm = DATA["va_ampm_lite"][mix_key]
    ips  = DATA["ip_stride"][mix_key]

    ws_ampm = [r["ws"] for r in ampm]
    ws_ips  = [r["ws"] for r in ips]

    x = np.arange(len(LABELS))
    w = 0.36

    fig, ax = plt.subplots(figsize=(6.4, 3.4), dpi=300)
    b1 = ax.bar(x - w/2, ws_ampm, w, label="L2 Prefetcher: va_ampm_lite", color=C_AMPM, edgecolor="none")
    b2 = ax.bar(x + w/2, ws_ips,  w, label="L2 Prefetcher: ip_stride",    color=C_IP,   edgecolor="none")

    # Subtle highlight outline on our proposed policies (indices 5, 6, 7)
    for idx in (6, 7):
        b1[idx].set_edgecolor("#0F172A")
        b1[idx].set_linewidth(0.9)
        b2[idx].set_edgecolor("#0F172A")
        b2[idx].set_linewidth(0.9)

    ax.set_ylabel("Weighted Speedup (vs. Alone)", fontsize=9, fontweight="bold", color="#0F172A")
    ax.set_title(title, fontsize=10, fontweight="bold", color="#0F172A", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(LABELS, fontsize=7.8, color="#1E293B")
    ax.set_ylim(*ylim)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#CBD5E1", fontsize=7.8, loc=legend_loc)

    for rect in b1:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=6.2, color="#0F172A")
    for rect in b2:
        h = rect.get_height()
        ax.annotate(f"{h:.3f}", xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, 2), textcoords="offset points", ha="center", va="bottom", fontsize=6.2, color="#0F172A")

    plt.tight_layout()
    plt.savefig(OUT_DIR / out_name, dpi=300, bbox_inches="tight")
    plt.close()


def make_frontier_chart():
    rows = DATA["va_ampm_lite"]["mix1_het"]
    # Plot Zero-Overhead vs SRAM-backed Miss Reduction on Mix 1 (va_ampm_lite)
    policies = ["Baseline\nLRU", "DRRIP\n(~16B)", "PA-LRU\n(0B)", "Baseline\nSRRIP", "PA-Adaptive\n(0.75B*/16KB)", "PA-SRRIP\n(0B)", "PACMan-HM\n(0B)", "SHiP\n(2KB)"]
    order_keys = ["lru", "drrip", "pa_lru", "srrip", "pa_adapt", "pa_srrip", "pacman", "ship"]
    row_map = {r["key"]: r for r in rows}

    misses_k = [row_map[k]["misses"] / 1000.0 for k in order_keys]
    colors   = [C_ALT, C_ALT, "#3B82F6", C_ALT, C_OURS, C_AMPM, C_IP, C_SOTA]

    fig, ax = plt.subplots(figsize=(6.4, 3.3), dpi=300)
    bars = ax.bar(np.arange(len(policies)), misses_k, width=0.58, color=colors, edgecolor="none")
    ax.set_ylabel("LLC Demand Misses (Thousands, Lower=Better)", fontsize=8.5, fontweight="bold", color="#0F172A")
    ax.set_title("Heterogeneous Mix 1: LLC Demand Misses vs. Extra Hardware Cost", fontsize=9.8, fontweight="bold", color="#0F172A", pad=10)
    ax.set_xticks(np.arange(len(policies)))
    ax.set_xticklabels(policies, fontsize=7.3, color="#1E293B")
    ax.set_ylim(1000, 1255)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for b, k in zip(bars, order_keys):
        h = b.get_height()
        ax.annotate(f"{row_map[k]['misses']:,}", xy=(b.get_x() + b.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=6.5, fontweight="bold", color="#0F172A")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "chart_storage_vs_misses.png", dpi=300, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    make_mix_chart("mix1_het", "Heterogeneous Mix (gcc + mcf + perlbench + omnetpp)", (0.88, 0.965), "chart_mix1_speedup.png", "upper left")
    make_mix_chart("mix2_mcf4", "Contention Stress (mcf x 4 Pointer-Chasing)", (0.65, 0.805), "chart_mix2_mcf4.png", "upper left")
    make_frontier_chart()
    print("Generated matched publication charts cleanly.")
