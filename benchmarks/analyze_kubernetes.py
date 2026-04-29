#!/usr/bin/env python3
"""
Kubernetes Cluster (GCP) Performance Analysis - Clean Summary
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load kubernetes results
results_file = Path("benchmarks/results/KubernetesCluster-gcp/results.json")
with open(results_file) as f:
    data = json.load(f)

results = data["results"]

# Extract data
scenarios = [r["scenario"] for r in results]
throughput = [r["throughput_rps"] for r in results]
avg_latency = [r["latency_ms_avg"] for r in results]
p99_latency = [r["latency_ms_p99"] for r in results]
request_counts = [r["request_count"] for r in results]

# Simple 3-panel figure
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("KUBERNETES CLUSTER (GCP) - Performance", fontsize=16, fontweight='bold')

# Plot 1: Average Latency
ax = axes[0]
bars = ax.bar(range(len(scenarios)), avg_latency, color='#9b59b6', alpha=0.7, edgecolor='black')
ax.set_ylabel('Latency (ms)', fontweight='bold')
ax.set_title('Average Latency', fontweight='bold')
ax.set_xticks(range(len(scenarios)))
ax.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, avg_latency):
    ax.text(bar.get_x() + bar.get_width()/2, val + 50, f'{val:.0f}', ha='center', fontsize=9, fontweight='bold')

# Plot 2: Throughput
ax = axes[1]
bars = ax.bar(range(len(scenarios)), throughput, color='#1abc9c', alpha=0.7, edgecolor='black')
ax.set_ylabel('Throughput (rps)', fontweight='bold')
ax.set_title('Throughput', fontweight='bold')
ax.set_xticks(range(len(scenarios)))
ax.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, throughput):
    ax.text(bar.get_x() + bar.get_width()/2, val + 2, f'{val:.1f}', ha='center', fontsize=9, fontweight='bold')

# Plot 3: P99 Latency
ax = axes[2]
bars = ax.bar(range(len(scenarios)), p99_latency, color='#16a085', alpha=0.7, edgecolor='black')
ax.set_ylabel('P99 Latency (ms)', fontweight='bold')
ax.set_title('P99 Tail Latency', fontweight='bold')
ax.set_xticks(range(len(scenarios)))
ax.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax.grid(axis='y', alpha=0.3)
for bar, val in zip(bars, p99_latency):
    ax.text(bar.get_x() + bar.get_width()/2, val + 200, f'{val:.0f}', ha='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig("benchmarks/kubernetes_analysis.png", dpi=300, bbox_inches='tight')
print("✅ Kubernetes graph saved: benchmarks/kubernetes_analysis.png")
