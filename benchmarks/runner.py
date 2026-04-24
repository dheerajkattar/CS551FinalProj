import argparse
import statistics
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from benchmarks.common.config import load_config
from benchmarks.common.io_utils import ensure_dir, write_csv, write_json
from benchmarks.common.metrics import build_metrics, percentile
from benchmarks.common.models import ScenarioExecutionConfig, ScenarioRunResult
from benchmarks.scenarios.registry import get_scenarios_for_apps


def get_git_sha() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def split_iterations(total: int, worker_count: int, worker_index: int) -> int:
    if worker_count <= 1:
        return total
    base = total // worker_count
    remainder = total % worker_count
    return base + (1 if worker_index < remainder else 0)


def aggregate_special_metrics(request_rows: List[Dict[str, Any]]) -> Dict[str, float]:
    e2e = [
        row.get("metadata", {}).get("e2e_time_seconds")
        for row in request_rows
        if isinstance(row.get("metadata"), dict) and row["metadata"].get("e2e_time_seconds") is not None
    ]
    if not e2e:
        return {}
    e2e_ms = [float(value) * 1000.0 for value in e2e]
    return {
        "e2e_time_ms_avg": sum(e2e_ms) / len(e2e_ms),
        "e2e_time_ms_p95": percentile(e2e_ms, 95),
    }


def run_one_scenario(
    scenario_def,
    cfg: ScenarioExecutionConfig,
    run_id: str,
    output_dir: Path,
    git_sha: str,
) -> Tuple[ScenarioRunResult, Dict[str, Any]]:
    notes: List[str] = []

    # Warmup to reduce cold-start skew.
    if cfg.warmup_iterations > 0:
        warmup_cfg = ScenarioExecutionConfig(**{**cfg.to_dict(), "iterations": cfg.warmup_iterations})
        scenario_def.runner(warmup_cfg)

    started = time.perf_counter()
    request_results = scenario_def.runner(cfg)
    duration = time.perf_counter() - started

    metrics = build_metrics(request_results, duration)
    request_dicts = [row.to_dict() for row in request_results]
    metrics.update(aggregate_special_metrics(request_dicts))

    if cfg.app == "llm":
        notes.append("LLM results include external API latency and quota effects.")
    if metrics["failure_count"] > 0:
        notes.append("Failures detected; review raw request results for transient errors.")

    metadata = {
        "run_id": run_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "cloud": cfg.cloud,
        "app": cfg.app,
        "scenario": cfg.scenario,
        "base_url": cfg.base_url,
        "mode": cfg.mode,
        "worker_index": cfg.worker_index,
        "worker_count": cfg.worker_count,
        "repeat_index": cfg.repeat_index,
        "config": cfg.to_dict(),
    }

    result = ScenarioRunResult(
        metadata=metadata,
        metrics=metrics,
        request_results=request_dicts,
        notes=notes,
    )

    raw_path = output_dir / "raw" / f"{cfg.cloud}_{cfg.scenario}_repeat{cfg.repeat_index}_worker{cfg.worker_index}.json"
    write_json(raw_path, result.to_dict())

    if cfg.cooldown_seconds > 0:
        time.sleep(cfg.cooldown_seconds)

    row = {
        "run_id": run_id,
        "timestamp_utc": metadata["timestamp_utc"],
        "git_sha": git_sha,
        "cloud": cfg.cloud,
        "app": cfg.app,
        "scenario": cfg.scenario,
        "repeat_index": cfg.repeat_index,
        "mode": cfg.mode,
        "worker_index": cfg.worker_index,
        "worker_count": cfg.worker_count,
        **metrics,
    }
    return result, row


def summarize_cloud_comparison(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["cloud"], row["app"], row["scenario"])].append(row)

    cloud_agg = {}
    for key, cloud_rows in grouped.items():
        cloud, app, scenario = key
        cloud_agg[key] = {
            "cloud": cloud,
            "app": app,
            "scenario": scenario,
            "latency_ms_p95_avg": statistics.mean(r["latency_ms_p95"] for r in cloud_rows),
            "throughput_rps_avg": statistics.mean(r["throughput_rps"] for r in cloud_rows),
            "failure_rate_avg": statistics.mean(r["failure_rate"] for r in cloud_rows),
        }

    comparisons: List[Dict[str, Any]] = []
    scenario_keys = {(app, scenario) for (_, app, scenario) in cloud_agg}
    for app, scenario in sorted(scenario_keys):
        aws = cloud_agg.get(("aws", app, scenario))
        gcp = cloud_agg.get(("gcp", app, scenario))
        if not aws or not gcp:
            continue

        def pct_delta(base: float, other: float) -> float:
            if base == 0:
                return 0.0
            return ((other - base) / base) * 100.0

        row = {
            "app": app,
            "scenario": scenario,
            "aws_latency_ms_p95_avg": aws["latency_ms_p95_avg"],
            "gcp_latency_ms_p95_avg": gcp["latency_ms_p95_avg"],
            "latency_delta_pct_gcp_vs_aws": pct_delta(aws["latency_ms_p95_avg"], gcp["latency_ms_p95_avg"]),
            "latency_winner": "aws" if aws["latency_ms_p95_avg"] < gcp["latency_ms_p95_avg"] else "gcp",
            "aws_throughput_rps_avg": aws["throughput_rps_avg"],
            "gcp_throughput_rps_avg": gcp["throughput_rps_avg"],
            "throughput_delta_pct_gcp_vs_aws": pct_delta(aws["throughput_rps_avg"], gcp["throughput_rps_avg"]),
            "throughput_winner": "aws" if aws["throughput_rps_avg"] > gcp["throughput_rps_avg"] else "gcp",
            "aws_failure_rate_avg": aws["failure_rate_avg"],
            "gcp_failure_rate_avg": gcp["failure_rate_avg"],
            "failure_rate_delta_pct_gcp_vs_aws": pct_delta(aws["failure_rate_avg"], gcp["failure_rate_avg"]),
            "reliability_winner": "aws" if aws["failure_rate_avg"] < gcp["failure_rate_avg"] else "gcp",
        }
        comparisons.append(row)
    return comparisons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AWS vs GCP benchmark suite.")
    parser.add_argument("--config", default="benchmarks/config.example.json", help="Path to benchmark config JSON")
    parser.add_argument("--clouds", nargs="+", default=["aws", "gcp"], choices=["aws", "gcp"])
    parser.add_argument("--apps", nargs="+", default=["crud", "cpu", "queue", "llm"], choices=["crud", "cpu", "queue", "llm"])
    parser.add_argument("--mode", choices=["single", "distributed"], default="single")
    parser.add_argument("--worker-index", type=int, default=0)
    parser.add_argument("--worker-count", type=int, default=1)
    parser.add_argument("--results-dir", default="benchmarks/results")
    parser.add_argument("--run-label", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    run_id = args.run_label or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.results_dir) / run_id
    ensure_dir(output_dir / "raw")

    scenarios = get_scenarios_for_apps(args.apps)
    git_sha = get_git_sha()

    summary_rows: List[Dict[str, Any]] = []
    manifest = {
        "run_id": run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_sha": git_sha,
        "clouds": args.clouds,
        "apps": args.apps,
        "mode": args.mode,
        "worker_index": args.worker_index,
        "worker_count": args.worker_count,
        "config_path": args.config,
    }

    for cloud in args.clouds:
        env_cfg = config["environments"][cloud]
        for scenario in scenarios:
            scenario_settings = config["scenarios"].get(scenario.name, {})
            defaults = config["defaults"]
            repeats = int(scenario_settings.get("repeats", defaults.get("repeats", 1)))
            total_iterations = int(scenario_settings.get("iterations", 1))
            per_worker_iterations = (
                split_iterations(total_iterations, args.worker_count, args.worker_index)
                if args.mode == "distributed"
                else total_iterations
            )

            if per_worker_iterations <= 0:
                continue

            for repeat_index in range(repeats):
                exec_cfg = ScenarioExecutionConfig(
                    cloud=cloud,
                    app=scenario.app,
                    scenario=scenario.name,
                    base_url=env_cfg[scenario.endpoint_key],
                    concurrency=int(scenario_settings.get("concurrency", 1)),
                    iterations=per_worker_iterations,
                    timeout_seconds=int(defaults.get("timeout_seconds", 30)),
                    retry_count=int(defaults.get("retry_count", 1)),
                    warmup_iterations=int(defaults.get("warmup_iterations", 0)),
                    cooldown_seconds=float(defaults.get("cooldown_seconds", 0.0)),
                    repeat_index=repeat_index,
                    mode=args.mode,
                    worker_index=args.worker_index,
                    worker_count=args.worker_count,
                    scenario_options=scenario_settings,
                )

                _, summary_row = run_one_scenario(
                    scenario_def=scenario,
                    cfg=exec_cfg,
                    run_id=run_id,
                    output_dir=output_dir,
                    git_sha=git_sha,
                )
                summary_rows.append(summary_row)

    summary_path = output_dir / "summary.csv"
    summary_json_path = output_dir / "summary.json"
    write_csv(summary_path, summary_rows)
    write_json(summary_json_path, {"manifest": manifest, "rows": summary_rows})

    comparisons = summarize_cloud_comparison(summary_rows)
    write_csv(output_dir / "comparison.csv", comparisons)
    write_json(output_dir / "comparison.json", {"manifest": manifest, "comparisons": comparisons})
    write_json(output_dir / "manifest.json", manifest)

    print(f"Benchmark run complete. Artifacts written to: {output_dir}")


if __name__ == "__main__":
    main()
