#!/usr/bin/env python3
"""
Server-Based (VM) Performance Analysis
Focused graphs showing key metrics
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load server-based results
results_file = Path("benchmarks/results/20260429T011136Z/results.json")
with open(results_file) as f:
    data = json.load(f)

results = data["results"]

# Extract data
scenarios = [r["scenario"] for r in results]
throughput = [r["throughput_rps"] for r in results]
avg_latency = [r["latency_ms_avg"] for r in results]
p99_latency = [r["latency_ms_p99"] for r in results]
p95_latency = [r["latency_ms_p95"] for r in results]
p50_latency = [r["latency_ms_p50"] for r in results]
min_latency = [r["latency_ms_min"] for r in results]
max_latency = [r["latency_ms_max"] for r in results]
request_counts = [r["request_count"] for r in results]

# Create focused figure with key metrics
fig = plt.figure(figsize=(16, 10))
fig.suptitle("SERVER-BASED (VM) - CRUD App Performance Analysis",
             fontsize=20, fontweight='bold', color='#e74c3c')

# Plot 1: Average Latency (MOST IMPORTANT)
ax1 = plt.subplot(2, 3, 1)
colors = ['#e74c3c', '#c0392b', '#e74c3c', '#e74c3c', '#e74c3c', '#e74c3c']
bars = ax1.bar(range(len(scenarios)), avg_latency, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
ax1.set_ylabel('Latency (ms)', fontweight='bold', fontsize=12)
ax1.set_title('1. Average Latency by Scenario', fontweight='bold', fontsize=13)
ax1.set_xticks(range(len(scenarios)))
ax1.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax1.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, avg_latency):
    ax1.text(bar.get_x() + bar.get_width()/2, val + 50, f'{val:.0f}ms',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

# Plot 2: Throughput Line Chart
ax2 = plt.subplot(2, 3, 2)
ax2.plot(range(len(scenarios)), throughput, marker='o', linewidth=2.5, markersize=10,
         color='#e74c3c', label='Throughput')
ax2.fill_between(range(len(scenarios)), throughput, alpha=0.3, color='#e74c3c')
ax2.set_ylabel('Throughput (rps)', fontweight='bold', fontsize=12)
ax2.set_title('2. Throughput by Scenario', fontweight='bold', fontsize=13)
ax2.set_xticks(range(len(scenarios)))
ax2.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax2.grid(True, alpha=0.3)
for i, val in enumerate(throughput):
    ax2.text(i, val + 20, f'{val:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

# Plot 3: P99 Latency (Tail Latency)
ax3 = plt.subplot(2, 3, 3)
bars = ax3.bar(range(len(scenarios)), p99_latency, color=['#c0392b' if x > 3000 else '#e74c3c' for x in p99_latency],
              alpha=0.8, edgecolor='black', linewidth=1.5)
ax3.set_ylabel('P99 Latency (ms)', fontweight='bold', fontsize=12)
ax3.set_title('3. P99 Tail Latency (Critical)', fontweight='bold', fontsize=13)
ax3.set_xticks(range(len(scenarios)))
ax3.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax3.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, p99_latency):
    ax3.text(bar.get_x() + bar.get_width()/2, val + 100, f'{val:.0f}ms',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

# Plot 4: Latency Percentiles Comparison
ax4 = plt.subplot(2, 3, 4)
x = np.arange(len(scenarios))
width = 0.15
ax4.bar(x - 1.5*width, p50_latency, width, label='p50', color='#3498db', alpha=0.8)
ax4.bar(x - 0.5*width, p95_latency, width, label='p95', color='#f39c12', alpha=0.8)
ax4.bar(x + 0.5*width, p99_latency, width, label='p99', color='#e74c3c', alpha=0.8)
ax4.set_ylabel('Latency (ms)', fontweight='bold', fontsize=11)
ax4.set_title('4. Latency Percentiles', fontweight='bold', fontsize=12)
ax4.set_xticks(x)
ax4.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax4.legend(fontsize=9)
ax4.grid(True, alpha=0.3, axis='y')

# Plot 5: Latency Distribution (Min, Avg, Max)
ax5 = plt.subplot(2, 3, 5)
ax5.scatter(avg_latency, throughput, s=[r*3 for r in request_counts], c=range(len(scenarios)),
           cmap='Reds', alpha=0.6, edgecolor='black', linewidth=2)
ax5.set_xlabel('Avg Latency (ms)', fontweight='bold', fontsize=11)
ax5.set_ylabel('Throughput (rps)', fontweight='bold', fontsize=11)
ax5.set_title('5. Latency vs Throughput Trade-off\n(bubble size = requests)', fontweight='bold', fontsize=12)
for i, scenario in enumerate(scenarios):
    ax5.annotate(scenario[:3], (avg_latency[i], throughput[i]), fontsize=8, ha='center')
ax5.grid(True, alpha=0.3)

# Plot 6: Tail Latency Impact (p99 vs p50)
ax6 = plt.subplot(2, 3, 6)
tail_impact = [(p99 / p50 - 1) * 100 for p99, p50 in zip(p99_latency, p50_latency)]
bars = ax6.bar(range(len(scenarios)), tail_impact, color=['#c0392b' if x > 1500 else '#e74c3c' for x in tail_impact],
              alpha=0.8, edgecolor='black', linewidth=1.5)
ax6.set_ylabel('% Increase', fontweight='bold', fontsize=11)
ax6.set_title('6. Tail Latency Impact\n(p99 vs p50 increase %)', fontweight='bold', fontsize=12)
ax6.set_xticks(range(len(scenarios)))
ax6.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax6.grid(True, alpha=0.3, axis='y')
for bar, val in zip(bars, tail_impact):
    ax6.text(bar.get_x() + bar.get_width()/2, val + 50, f'{val:.0f}%',
            ha='center', va='bottom', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig("benchmarks/server_based_detailed_analysis.png", dpi=300, bbox_inches='tight')
print("✅ Server-based graph saved: benchmarks/server_based_detailed_analysis.png")

# Print summary
print("\n" + "="*80)
print("SERVER-BASED (VM) - PERFORMANCE SUMMARY")
print("="*80)
print(f"\nRun ID: {data['run_id']}")
print(f"Timestamp: {data['timestamp']}\n")

print(f"{'Scenario':<20} {'Requests':<12} {'Throughput':<15} {'Avg Latency':<15} {'P99 Latency':<15}")
print("-" * 80)
for scenario, req, tput, latency, p99 in zip(scenarios, request_counts, throughput, avg_latency, p99_latency):
    print(f"{scenario:<20} {req:<12} {tput:>6.1f} rps    {latency:>6.0f} ms       {p99:>6.0f} ms")

print("\n" + "="*80)
print("KEY METRICS")
print("="*80)
print(f"Total Requests: {sum(request_counts)}")
print(f"Avg Throughput: {np.mean(throughput):.2f} rps")
print(f"Avg Latency: {np.mean(avg_latency):.0f} ms")
print(f"Overall P99: {np.mean(p99_latency):.0f} ms")
print(f"Best Scenario: {scenarios[np.argmax(throughput)]} ({np.max(throughput):.1f} rps)")
print(f"Fastest Scenario: {scenarios[np.argmin(avg_latency)]} ({np.min(avg_latency):.0f} ms avg)")
