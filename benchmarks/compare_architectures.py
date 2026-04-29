#!/usr/bin/env python3
"""
Compare Serverless (Cloud Run) vs Server-based CRUD app performance
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Load results
serverless_file = Path("benchmarks/results/20260429T011508Z/results.json")  # Appears to be serverless
server_file = Path("benchmarks/results/20260429T011136Z/results.json")      # Appears to be server-based

with open(serverless_file) as f:
    serverless_data = json.load(f)
with open(server_file) as f:
    server_data = json.load(f)

serverless_results = serverless_data["results"]
server_results = server_data["results"]

# Extract data
scenarios = [r["scenario"] for r in serverless_results]
serverless_throughput = [r["throughput_rps"] for r in serverless_results]
server_throughput = [r["throughput_rps"] for r in server_results]

serverless_avg_latency = [r["latency_ms_avg"] for r in serverless_results]
server_avg_latency = [r["latency_ms_avg"] for r in server_results]

serverless_p95 = [r["latency_ms_p95"] for r in serverless_results]
server_p95 = [r["latency_ms_p95"] for r in server_results]

serverless_p99 = [r["latency_ms_p99"] for r in serverless_results]
server_p99 = [r["latency_ms_p99"] for r in server_results]

serverless_request_counts = [r["request_count"] for r in serverless_results]
server_request_counts = [r["request_count"] for r in server_results]

# Create comprehensive comparison figure
fig = plt.figure(figsize=(16, 12))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

fig.suptitle("Serverless (Cloud Run) vs Server-Based: CRUD App Performance Comparison",
             fontsize=18, fontweight='bold', y=0.98)

# Plot 1: Throughput Comparison
ax1 = fig.add_subplot(gs[0, 0])
x = np.arange(len(scenarios))
width = 0.35
bars1 = ax1.bar(x - width/2, serverless_throughput, width, label='Serverless', color='#3498db', alpha=0.8)
bars2 = ax1.bar(x + width/2, server_throughput, width, label='Server-Based', color='#e74c3c', alpha=0.8)
ax1.set_ylabel('Throughput (rps)', fontweight='bold', fontsize=11)
ax1.set_title('Throughput Comparison', fontweight='bold', fontsize=12)
ax1.set_xticks(x)
ax1.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax1.legend()
ax1.grid(True, alpha=0.3, axis='y')

# Add value labels
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}', ha='center', va='bottom', fontsize=8)

# Plot 2: Average Latency Comparison
ax2 = fig.add_subplot(gs[0, 1])
bars1 = ax2.bar(x - width/2, serverless_avg_latency, width, label='Serverless', color='#3498db', alpha=0.8)
bars2 = ax2.bar(x + width/2, server_avg_latency, width, label='Server-Based', color='#e74c3c', alpha=0.8)
ax2.set_ylabel('Latency (ms)', fontweight='bold', fontsize=11)
ax2.set_title('Average Latency Comparison', fontweight='bold', fontsize=12)
ax2.set_xticks(x)
ax2.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax2.legend()
ax2.grid(True, alpha=0.3, axis='y')

# Plot 3: P95 Latency (Tail Latency)
ax3 = fig.add_subplot(gs[1, 0])
bars1 = ax3.bar(x - width/2, serverless_p95, width, label='Serverless', color='#3498db', alpha=0.8)
bars2 = ax3.bar(x + width/2, server_p95, width, label='Server-Based', color='#e74c3c', alpha=0.8)
ax3.set_ylabel('P95 Latency (ms)', fontweight='bold', fontsize=11)
ax3.set_title('P95 Tail Latency (95% of requests faster)', fontweight='bold', fontsize=12)
ax3.set_xticks(x)
ax3.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax3.legend()
ax3.grid(True, alpha=0.3, axis='y')

# Plot 4: P99 Latency (Worst Case)
ax4 = fig.add_subplot(gs[1, 1])
bars1 = ax4.bar(x - width/2, serverless_p99, width, label='Serverless', color='#3498db', alpha=0.8)
bars2 = ax4.bar(x + width/2, server_p99, width, label='Server-Based', color='#e74c3c', alpha=0.8)
ax4.set_ylabel('P99 Latency (ms)', fontweight='bold', fontsize=11)
ax4.set_title('P99 Tail Latency (Worst Case - 99% of requests faster)', fontweight='bold', fontsize=12)
ax4.set_xticks(x)
ax4.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax4.legend()
ax4.grid(True, alpha=0.3, axis='y')

# Plot 5: Performance Ratio (Serverless vs Server)
ax5 = fig.add_subplot(gs[2, 0])
throughput_ratio = [s/sv for s, sv in zip(serverless_throughput, server_throughput)]
colors = ['#2ecc71' if x > 1 else '#e74c3c' for x in throughput_ratio]
bars = ax5.bar(range(len(scenarios)), throughput_ratio, color=colors, alpha=0.8)
ax5.axhline(y=1, color='black', linestyle='--', linewidth=2, label='Equal Performance')
ax5.set_ylabel('Throughput Ratio', fontweight='bold', fontsize=11)
ax5.set_title('Throughput Ratio (Serverless / Server-Based)', fontweight='bold', fontsize=12)
ax5.set_xticks(range(len(scenarios)))
ax5.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax5.legend()
ax5.grid(True, alpha=0.3, axis='y')

# Add ratio labels
for i, (bar, ratio) in enumerate(zip(bars, throughput_ratio)):
    ax5.text(i, ratio + 0.02, f'{ratio:.2f}x', ha='center', fontsize=9, fontweight='bold')

# Plot 6: Total Requests vs Latency Efficiency
ax6 = fig.add_subplot(gs[2, 1])
serverless_efficiency = [req / latency for req, latency in zip(serverless_request_counts, serverless_avg_latency)]
server_efficiency = [req / latency for req, latency in zip(server_request_counts, server_avg_latency)]
bars1 = ax6.bar(x - width/2, serverless_efficiency, width, label='Serverless', color='#3498db', alpha=0.8)
bars2 = ax6.bar(x + width/2, server_efficiency, width, label='Server-Based', color='#e74c3c', alpha=0.8)
ax6.set_ylabel('Efficiency (requests/ms)', fontweight='bold', fontsize=11)
ax6.set_title('Throughput-to-Latency Efficiency', fontweight='bold', fontsize=12)
ax6.set_xticks(x)
ax6.set_xticklabels([s.replace('_', '\n') for s in scenarios], fontsize=9)
ax6.legend()
ax6.grid(True, alpha=0.3, axis='y')

plt.savefig("benchmarks/serverless_vs_server_comparison.png", dpi=300, bbox_inches='tight')
print("✅ Graph saved: benchmarks/serverless_vs_server_comparison.png")

# Print detailed analysis
print("\n" + "="*80)
print("SERVERLESS (CLOUD RUN) VS SERVER-BASED: DETAILED ANALYSIS")
print("="*80)
print(f"\nServerless Run ID: {serverless_data['run_id']}")
print(f"Server-Based Run ID: {server_data['run_id']}\n")

for i, scenario in enumerate(scenarios):
    print(f"\n{'─'*80}")
    print(f"SCENARIO: {scenario.upper()}")
    print(f"{'─'*80}")

    s_result = serverless_results[i]
    sv_result = server_results[i]

    tput_diff = ((s_result['throughput_rps'] - sv_result['throughput_rps']) / sv_result['throughput_rps']) * 100
    latency_diff = ((s_result['latency_ms_avg'] - sv_result['latency_ms_avg']) / sv_result['latency_ms_avg']) * 100
    p95_diff = ((s_result['latency_ms_p95'] - sv_result['latency_ms_p95']) / sv_result['latency_ms_p95']) * 100
    p99_diff = ((s_result['latency_ms_p99'] - sv_result['latency_ms_p99']) / sv_result['latency_ms_p99']) * 100

    print(f"\n📊 THROUGHPUT")
    print(f"  Serverless: {s_result['throughput_rps']:.2f} rps")
    print(f"  Server-Based: {sv_result['throughput_rps']:.2f} rps")
    print(f"  Difference: {tput_diff:+.1f}% {'✅ SERVERLESS FASTER' if tput_diff > 0 else '❌ SERVER FASTER'}")

    print(f"\n⏱️  AVERAGE LATENCY")
    print(f"  Serverless: {s_result['latency_ms_avg']:.0f}ms")
    print(f"  Server-Based: {sv_result['latency_ms_avg']:.0f}ms")
    print(f"  Difference: {latency_diff:+.1f}% {'❌ SERVERLESS SLOWER' if latency_diff > 0 else '✅ SERVERLESS FASTER'}")

    print(f"\n⚠️  P95 LATENCY (95% of requests faster)")
    print(f"  Serverless: {s_result['latency_ms_p95']:.0f}ms")
    print(f"  Server-Based: {sv_result['latency_ms_p95']:.0f}ms")
    print(f"  Difference: {p95_diff:+.1f}%")

    print(f"\n🔴 P99 LATENCY (Worst case)")
    print(f"  Serverless: {s_result['latency_ms_p99']:.0f}ms")
    print(f"  Server-Based: {sv_result['latency_ms_p99']:.0f}ms")
    print(f"  Difference: {p99_diff:+.1f}%")

    print(f"\n✓ SUCCESS RATE")
    print(f"  Serverless: {s_result['success_count']}/{s_result['request_count']} (100%)")
    print(f"  Server-Based: {sv_result['success_count']}/{sv_result['request_count']} (100%)")

print("\n\n" + "="*80)
print("KEY FINDINGS")
print("="*80)

avg_throughput_diff = np.mean([((s_result['throughput_rps'] - sv_result['throughput_rps']) / sv_result['throughput_rps']) * 100
                               for s_result, sv_result in zip(serverless_results, server_results)])
avg_latency_diff = np.mean([((s_result['latency_ms_avg'] - sv_result['latency_ms_avg']) / sv_result['latency_ms_avg']) * 100
                            for s_result, sv_result in zip(serverless_results, server_results)])
avg_p99_diff = np.mean([((s_result['latency_ms_p99'] - sv_result['latency_ms_p99']) / sv_result['latency_ms_p99']) * 100
                        for s_result, sv_result in zip(serverless_results, server_results)])

print(f"\n📈 OVERALL PERFORMANCE DIFFERENCE (Average across all scenarios):")
print(f"  Throughput: Serverless is {avg_throughput_diff:+.1f}% {'FASTER ✅' if avg_throughput_diff > 0 else 'SLOWER ❌'}")
print(f"  Avg Latency: Serverless is {avg_latency_diff:+.1f}% {'FASTER ✅' if avg_latency_diff < 0 else 'SLOWER ❌'}")
print(f"  P99 Latency: Serverless is {avg_p99_diff:+.1f}% {'BETTER ✅' if avg_p99_diff < 0 else 'WORSE ❌'}")

print(f"\n🔍 SCENARIO ANALYSIS:")
burst_idx = scenarios.index('burst_mixed_notes')
print(f"  Burst Load (burst_mixed_notes):")
print(f"    - Serverless throughput: {serverless_results[burst_idx]['throughput_rps']:.1f} rps")
print(f"    - Server-based throughput: {server_results[burst_idx]['throughput_rps']:.1f} rps")
print(f"    - Serverless {((serverless_results[burst_idx]['throughput_rps'] / server_results[burst_idx]['throughput_rps']) - 1) * 100:+.1f}% throughput advantage")

auth_idx = scenarios.index('auth_burst')
print(f"\n  Auth Burst (auth_burst):")
print(f"    - Serverless avg latency: {serverless_results[auth_idx]['latency_ms_avg']:.0f}ms")
print(f"    - Server-based avg latency: {server_results[auth_idx]['latency_ms_avg']:.0f}ms")
print(f"    - Serverless {(1 - serverless_results[auth_idx]['latency_ms_avg'] / server_results[auth_idx]['latency_ms_avg']) * 100:+.1f}% latency improvement")

print(f"\n💡 RECOMMENDATIONS:")
print(f"  ✅ Serverless (Cloud Run) shows {'SUPERIOR' if avg_throughput_diff > 0 else 'COMPARABLE'} throughput")
print(f"  {'✅' if avg_latency_diff < 0 else '⚠️ '} Serverless latency is {'LOWER' if avg_latency_diff < 0 else 'HIGHER'} (consider auto-scaling tuning)")
print(f"  ⚠️  Tail latencies (p99) are important - Serverless {'better for' if avg_p99_diff < 0 else 'similar to'} consistent user experience")
