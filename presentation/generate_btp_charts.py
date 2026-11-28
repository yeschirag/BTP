#!/usr/bin/env python3
"""
Generate zero-based, non-exaggerated ISCA/MICRO-style Matplotlib charts
directly from verified iiitsgpu ChampSim matched grid results.
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
    "font.sans-serif": ["Inter", "Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
    "axes.edgecolor": "#CBD5E1",
    "axes.linewidth": 0.8,
    "axes.grid": True,
    "grid.color": "#E2E8F0",
    "grid.linestyle": "--",
    "grid.linewidth": 0.6,
    "axes.axisbelow": True,
})

C_AMPM = "#1E3A8A"   # Deep Navy
C_IP   = "#0F766E"   # Deep Slate Teal
C_ALT  = "#64748B"   # Cool Slate
C_OURS = "#2563EB"   # Crisp Royal Blue
C_SOTA = "#0F172A"   # Obsidian Navy

LABELS = ["LRU", "SRRIP*", "DRRIP", "SHiP\n(2KB)", "PACMan\n-HM", "PA-LRU\n(Ours)", "PA-SRRIP\n(Ours)", "PA-Adapt\n(Ours)"]


def make_pct_speedup_chart(mix_key: str, title: str, ylim: tuple, out_name: str):
    ampm = DATA["va_ampm_lite"][mix_key]
    ips  = DATA["ip_stride"][mix_key]

    base_ampm = ampm[0]["ws"]
    base_ips  = ips[0]["ws"]

    pct_ampm = [((r["ws"] / base_ampm) - 1.0) * 100.0 for r in ampm]
    pct_ips  = [((r["ws"] / base_ips) - 1.0) * 100.0 for r in ips]

    x = np.arange(len(LABELS))
    w = 0.36

    fig, ax = plt.subplots(figsize=(7.0, 3.4), dpi=300)
    b1 = ax.bar(x - w/2, pct_ampm, w, label="L2 Prefetcher: va_ampm_lite", color=C_AMPM)
    b2 = ax.bar(x + w/2, pct_ips,  w, label="L2 Prefetcher: ip_stride",    color=C_IP)

    for idx in (6, 7):
        b1[idx].set_edgecolor("#0F172A")
        b1[idx].set_linewidth(0.9)
        b2[idx].set_edgecolor("#0F172A")
        b2[idx].set_linewidth(0.9)

    ax.axhline(0.0, color="#0F172A", linewidth=0.8)
    ax.set_ylabel("Weighted Speedup vs. LRU (%)", fontsize=8.8, fontweight="bold", color="#0F172A")
    ax.set_title(title + " (Zero-Based Scale)", fontsize=9.8, fontweight="bold", color="#0F172A", pad=10)
    ax.set_xticks(x)
    ax.set_xticklabels(LABELS, fontsize=7.6, color="#1E293B")
    ax.set_ylim(*ylim)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(frameon=True, facecolor="#F8FAFC", edgecolor="#CBD5E1", fontsize=7.6, loc="upper left")

    for rect, val in list(zip(b1, pct_ampm)) + list(zip(b2, pct_ips)):
        h = rect.get_height()
        va = "bottom" if h >= 0 else "top"
        dy = 3 if h >= 0 else -3
        ax.annotate(f"{val:+.2f}%" if abs(val) > 0.005 else "0%",
                    xy=(rect.get_x() + rect.get_width()/2, h),
                    xytext=(0, dy), textcoords="offset points", ha="center", va=va,
                    fontsize=5.8, rotation=40 if abs(val) > 0.005 else 0, color="#0F172A")

    plt.tight_layout()
    plt.savefig(OUT_DIR / out_name, dpi=300, bbox_inches="tight")
    plt.close()


def make_frontier_chart():
    rows = DATA["va_ampm_lite"]["mix1_het"]
    row_map = {r["key"]: r for r in rows}
    base_misses = row_map["lru"]["misses"]

    policies = ["Baseline\nLRU", "PA-LRU\n(0B)", "DRRIP\n(~16B)", "Baseline\nSRRIP*", "PA-Adapt\n(0.75B*/16KB)", "PA-SRRIP\n(0B)", "PACMan-HM\n(0B)", "SHiP\n(2KB)"]
    order_keys = ["lru", "pa_lru", "drrip", "srrip", "pa_adapt", "pa_srrip", "pacman", "ship"]

    pct_red = [((base_misses - row_map[k]["misses"]) / base_misses) * 100.0 for k in order_keys]
    colors  = [C_ALT, "#3B82F6", C_ALT, C_ALT, C_OURS, C_AMPM, C_IP, C_SOTA]

    fig, ax = plt.subplots(figsize=(6.4, 3.3), dpi=300)
    bars = ax.bar(np.arange(len(policies)), pct_red, width=0.58, color=colors)
    ax.axhline(0.0, color="#0F172A", linewidth=0.8)
    ax.set_ylabel("LLC Demand Miss Reduction vs. LRU (%)", fontsize=8.3, fontweight="bold", color="#0F172A")
    ax.set_title("Mix 1: LLC Demand Miss Reduction vs. Hardware Storage (Zero-Based)", fontsize=9.5, fontweight="bold", color="#0F172A", pad=10)
    ax.set_xticks(np.arange(len(policies)))
    ax.set_xticklabels(policies, fontsize=7.2, color="#1E293B")
    ax.set_ylim(0, 14.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for b, k, val in zip(bars, order_keys, pct_red):
        h = b.get_height()
        misses_m = row_map[k]["misses"] / 1e6
        ax.annotate(f"{val:.1f}%\n({misses_m:.3f}M)", xy=(b.get_x() + b.get_width()/2, h),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=6.4, fontweight="bold", color="#0F172A")

    plt.tight_layout()
    plt.savefig(OUT_DIR / "chart_storage_vs_misses.png", dpi=300, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
    make_pct_speedup_chart("mix1_het", "Heterogeneous Mix (gcc + mcf + perl + omnet)", (-0.6, 5.8), "chart_mix1_speedup.png")
    make_pct_speedup_chart("mix2_mcf4", "Contention Stress (mcf x 4 Pointer-Chasing)", (-0.8, 17.5), "chart_mix2_mcf4.png")
    make_frontier_chart()
    print("Generated zero-based % improvement charts cleanly.")
