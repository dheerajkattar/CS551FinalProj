import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List

from benchmarks.common.io_utils import ensure_dir, write_json
from benchmarks.scenarios.crud import run_all_crud
from benchmarks.scenarios.cpu import run_all_cpu
from benchmarks.scenarios.queue import run_all_queue
from benchmarks.scenarios.llm import run_all_llm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profile cloud applications.")
    parser.add_argument("--crud-url", default="", help="CRUD app base URL")
    parser.add_argument("--cpu-url", default="", help="CPU app base URL")
    parser.add_argument("--queue-url", default="", help="Queue app base URL")
    parser.add_argument("--llm-url", default="", help="LLM app base URL")
    parser.add_argument("--results-dir", default="benchmarks/results", help="Output directory")
    parser.add_argument("--run-label", default="", help="Custom run label")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Check that at least one URL is provided
    urls = {
        "crud": args.crud_url,
        "cpu": args.cpu_url,
        "queue": args.queue_url,
        "llm": args.llm_url,
    }
    urls = {app: url for app, url in urls.items() if url}

    if not urls:
        print("Error: At least one app URL is required (--crud-url, --cpu-url, --queue-url, or --llm-url)")
        return

    # Setup output directory
    run_id = args.run_label or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.results_dir) / run_id
    ensure_dir(output_dir)

    # Map app names to runner functions
    runners: Dict[str, Callable[[str], List]] = {
        "crud": run_all_crud,
        "cpu": run_all_cpu,
        "queue": run_all_queue,
        "llm": run_all_llm,
    }

    # Collect all results
    results: List[Dict[str, Any]] = []

    for app_name, base_url in urls.items():
        print(f"\nRunning {app_name} benchmarks...")
        runner = runners[app_name]
        scenario_results = runner(base_url)
        if not scenario_results:
            print(f"  ! Warning: no benchmark scenarios returned for app '{app_name}'")
            continue

        for scenario_name, metrics in scenario_results:
            row = {
                "app": app_name,
                "scenario": scenario_name,
                "request_count": metrics["request_count"],
                "success_count": metrics["success_count"],
                "failure_count": metrics["failure_count"],
                "failure_rate": metrics["failure_rate"],
                "throughput_rps": metrics["throughput_rps"],
                "latency_ms_min": metrics["latency_ms_min"],
                "latency_ms_max": metrics["latency_ms_max"],
                "latency_ms_avg": metrics["latency_ms_avg"],
                "latency_ms_p50": metrics["latency_ms_p50"],
                "latency_ms_p90": metrics["latency_ms_p90"],
                "latency_ms_p95": metrics["latency_ms_p95"],
                "latency_ms_p99": metrics["latency_ms_p99"],
            }
            results.append(row)
            print(f"  ✓ {scenario_name}: p95={metrics['latency_ms_p95']:.1f}ms, rps={metrics['throughput_rps']:.2f}")

    # Write results to JSON
    output_file = output_dir / "results.json"
    write_json(output_file, {"run_id": run_id, "timestamp": datetime.now(timezone.utc).isoformat(), "results": results})
    print(f"\nResults: {output_file}")


if __name__ == "__main__":
    main()
