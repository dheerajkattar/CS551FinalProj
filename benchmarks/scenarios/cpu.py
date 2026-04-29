import time
from typing import List, Tuple, Dict, Any

from benchmarks.common.executor import run_concurrent
from benchmarks.common.http_client import request_with_retries
from benchmarks.common.metrics import build_metrics
from benchmarks.common.models import RequestResult


def _run_cpu_endpoint(
    base_url: str,
    scenario_name: str,
    endpoint: str,
    size: int,
    iterations: int = 20,
    concurrency: int = 5,
) -> Tuple[str, Dict[str, Any]]:

    url = f"{base_url.rstrip('/')}{endpoint}"

    def op(_: int) -> RequestResult:
        return request_with_retries(
            method="POST",
            url=url,
            timeout_seconds=120,
            retry_count=1,
            expected_statuses=(200,),
            json_body={"size": size},
        )

    start = time.perf_counter()
    request_results = run_concurrent(op, iterations, concurrency)
    duration = time.perf_counter() - start

    metrics = build_metrics(request_results, duration)

    return scenario_name, metrics


def run_all_cpu(base_url: str) -> List[Tuple[str, Dict[str, Any]]]:
    return [
        _run_cpu_endpoint(
            base_url=base_url,
            scenario_name="cpu_matmul_small",
            endpoint="/compute/matmul",
            size=500,
            iterations=20,
            concurrency=5,
        ),
        _run_cpu_endpoint(
            base_url=base_url,
            scenario_name="cpu_matinv_medium",
            endpoint="/compute/matinv",
            size=400,
            iterations=20,
            concurrency=5,
        ),
        _run_cpu_endpoint(
            base_url=base_url,
            scenario_name="cpu_eigen_small",
            endpoint="/compute/eigenvalues",
            size=300,
            iterations=20,
            concurrency=5,
        ),
        _run_cpu_endpoint(
            base_url=base_url,
            scenario_name="cpu_fft_medium",
            endpoint="/compute/fft",
            size=200000,
            iterations=20,
            concurrency=5,
        ),
    ]