import os
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'Helvetica'
plt.rcParams['font.size'] = 10

# ==============================================================================
# Chart 1: 4-Core Per-CPU IPC Comparison (Compact Slide Layout)
# ==============================================================================
fig, ax = plt.subplots(figsize=(5.5, 3.6), dpi=300)

cores = ['CPU 0\n(gcc)', 'CPU 1\n(mcf)', 'CPU 2\n(perlbench)', 'CPU 3\n(omnetpp)']
baseline_ipc = [2.14, 0.085, 1.95, 0.28]
pa_lru_ipc   = [2.18, 0.091, 2.02, 0.31]
pa_rrip_ipc  = [2.18, 0.099, 2.02, 0.32]

x = np.arange(len(cores))
width = 0.26

rects1 = ax.bar(x - width, baseline_ipc, width, label='Baseline', color='#e63946', edgecolor='black', linewidth=0.8)
rects2 = ax.bar(x,          pa_lru_ipc,   width, label='PA-LRU',   color='#2a9d8f', edgecolor='black', linewidth=0.8)
rects3 = ax.bar(x + width, pa_rrip_ipc,  width, label='PA-SRRIP', color='#457b9d', edgecolor='black', linewidth=0.8)

ax.set_ylabel('IPC', fontsize=10, fontweight='bold')
ax.set_title('4-Core Shared LLC IPC Comparison (20M Sim)', fontsize=11, fontweight='bold', pad=10)
ax.set_xticks(x)
ax.set_xticklabels(cores, fontweight='bold', fontsize=9)
ax.legend(frameon=True, facecolor='#ffffff', edgecolor='#cccccc', fontsize=8, loc='upper right')
ax.set_ylim(0, 2.7)

for rect in rects1:
    h = rect.get_height()
    ax.annotate(f'{h:.2f}', xy=(rect.get_x() + rect.get_width()/2, h),
                xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

for rect in rects2:
    h = rect.get_height()
    ax.annotate(f'{h:.2f}', xy=(rect.get_x() + rect.get_width()/2, h),
                xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

for rect in rects3:
    h = rect.get_height()
    ax.annotate(f'{h:.2f}', xy=(rect.get_x() + rect.get_width()/2, h),
                xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

ax.annotate('+17.2%', xy=(1 + width, 0.10), xytext=(1, 0.5),
            arrowprops=dict(facecolor='#457b9d', shrink=0.08, width=1.5, headwidth=5),
            ha='center', fontsize=8.5, fontweight='bold', color='#1d3557',
            bbox=dict(boxstyle="round,pad=0.2", fc="#e8f5e9", ec="#2a9d8f", lw=1.0))

plt.tight_layout()
plt.savefig(os.path.join(SCRIPT_DIR, 'chart_4core_all_cpus_ipc.png'), dpi=300, bbox_inches='tight')
plt.close()

# ==============================================================================
# Chart 2: Prefetch Usefulness Comparison (Compact Slide Layout)
# ==============================================================================
fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=300)
workloads = ['403.gcc\n(Stride)', '4-Core Mix 1\n(Shared LLC)', '429.mcf\n(Pointer)']
usefulness = [50.10, 32.25, 0.18]
colors = ['#457b9d', '#2a9d8f', '#e63946']

bars = ax.bar(workloads, usefulness, color=colors, width=0.45, edgecolor='black', linewidth=0.8)
ax.set_ylabel('Prefetch Usefulness (%)', fontsize=10, fontweight='bold')
ax.set_title('Prefetch Usefulness Rate (%)', fontsize=11, fontweight='bold', pad=10)
ax.set_ylim(0, 60)

for bar in bars:
    h = bar.get_height()
    ax.annotate(f'{h:.2f}%', xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(SCRIPT_DIR, 'chart_prefetch_usefulness.png'), dpi=300, bbox_inches='tight')
plt.close()

# ==============================================================================
# Chart 3: Focused Speedup Callout Chart
# ==============================================================================
fig, ax = plt.subplots(figsize=(5.2, 3.6), dpi=300)
policies = ['Baseline 4-Core\n(LRU)', 'Prefetch-Aware 4-Core\n(PA-LRU)']
ipc_vals = [0.4248, 2.1800]
colors = ['#e63946', '#2a9d8f']

bars = ax.bar(policies, ipc_vals, color=colors, width=0.4, edgecolor='black', linewidth=0.8)
ax.set_ylabel('IPC', fontsize=10, fontweight='bold')
ax.set_title('CPU 0 (gcc) Speedup (20M Sim)', fontsize=11, fontweight='bold', pad=10)
ax.set_ylim(0, 2.6)

for bar in bars:
    h = bar.get_height()
    ax.annotate(f'{h:.4f}', xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 4), textcoords="offset points", ha='center', va='bottom', fontsize=9.5, fontweight='bold')

ax.annotate('5.13x Speedup!', xy=(1, 2.180), xytext=(0.45, 1.8),
            arrowprops=dict(facecolor='#2a9d8f', shrink=0.08, width=1.5, headwidth=6),
            fontsize=9.5, fontweight='bold', color='#1b4332',
            bbox=dict(boxstyle="round,pad=0.3", fc="#d8f3dc", ec="#2a9d8f", lw=1.2))

plt.tight_layout()
plt.savefig(os.path.join(SCRIPT_DIR, 'chart_4core_gcc_speedup.png'), dpi=300, bbox_inches='tight')
plt.close()

# ==============================================================================
# Chart 4: Storage Budget vs Performance Resilience (Pareto Efficiency)
# ==============================================================================
fig, ax = plt.subplots(figsize=(6.0, 3.8), dpi=300)

policies = ['Baseline\nLRU', 'Baseline\nSRRIP', 'DRRIP\n(Set Dueling)', 'SHiP\n(8K SHCT)', 'PA-LRU\n(Ours)', 'PA-SRRIP\n(Ours)', 'PA-Adaptive\n(Ours)']
misses = [15720, 15682, 15617, 14589, 15528, 15507, 15503]
storage_bytes = [0, 0, 16, 2048, 0, 0, 0.75]
colors = ['#94a3b8', '#94a3b8', '#f59e0b', '#3b82f6', '#10b981', '#06b6d4', '#8b5cf6']

bars = ax.bar(policies, misses, color=colors, width=0.55, edgecolor='black', linewidth=0.8)
ax.set_ylabel('LLC Demand Misses (Lower is Better)', fontsize=9.5, fontweight='bold')
ax.set_title('Heterogeneous 4-Core Misses vs. Hardware Storage Budget', fontsize=10.5, fontweight='bold', pad=10)
ax.set_ylim(14000, 16200)

for i, bar in enumerate(bars):
    h = bar.get_height()
    cost_str = f"{int(storage_bytes[i])} B" if storage_bytes[i] >= 1 else ("0 B" if storage_bytes[i] == 0 else "0.75 B")
    ax.annotate(f'{h}\n({cost_str})', xy=(bar.get_x() + bar.get_width()/2, h),
                xytext=(0, 2), textcoords="offset points", ha='center', va='bottom', fontsize=7.5, fontweight='bold')

plt.tight_layout()
plt.savefig(os.path.join(SCRIPT_DIR, 'chart_storage_vs_misses.png'), dpi=300, bbox_inches='tight')
plt.close()

print('Charts updated with 20M simulation numbers and Chart 4 created!')
