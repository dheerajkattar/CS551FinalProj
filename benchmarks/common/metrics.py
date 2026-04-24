import math
from typing import Dict, Iterable, List

from benchmarks.common.models import RequestResult


def percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    if pct <= 0:
        return float(min(values))
    if pct >= 100:
        return float(max(values))

    sorted_values = sorted(values)
    rank = (len(sorted_values) - 1) * (pct / 100.0)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return float(sorted_values[low])
    weight = rank - low
    return float(sorted_values[low] * (1 - weight) + sorted_values[high] * weight)


def build_metrics(results: Iterable[RequestResult], total_duration_seconds: float) -> Dict[str, float]:
    rows = list(results)
    latencies = [r.latency_ms for r in rows]
    successes = sum(1 for r in rows if r.success)
    failures = len(rows) - successes
    duration = max(total_duration_seconds, 0.001)

    return {
        "request_count": len(rows),
        "success_count": successes,
        "failure_count": failures,
        "failure_rate": failures / len(rows) if rows else 0.0,
        "throughput_rps": len(rows) / duration,
        "latency_ms_min": min(latencies) if latencies else 0.0,
        "latency_ms_max": max(latencies) if latencies else 0.0,
        "latency_ms_avg": sum(latencies) / len(latencies) if latencies else 0.0,
        "latency_ms_p50": percentile(latencies, 50),
        "latency_ms_p90": percentile(latencies, 90),
        "latency_ms_p95": percentile(latencies, 95),
        "latency_ms_p99": percentile(latencies, 99),
        "total_duration_seconds": duration,
    }
