from typing import List

from benchmarks.common.executor import run_concurrent
from benchmarks.common.http_client import request_with_retries
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig


def _run_cpu_endpoint(cfg: ScenarioExecutionConfig, endpoint: str, default_size: int) -> List[RequestResult]:
    size = int(cfg.scenario_options.get("size", default_size))
    url = f"{cfg.base_url.rstrip('/')}{endpoint}"

    def op(_: int) -> RequestResult:
        return request_with_retries(
            method="POST",
            url=url,
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(200,),
            json_body={"size": size},
        )

    return run_concurrent(op, cfg.iterations, cfg.concurrency)


def run_cpu_matmul_small(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    return _run_cpu_endpoint(cfg, "/compute/matmul", default_size=500)


def run_cpu_matinv_medium(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    return _run_cpu_endpoint(cfg, "/compute/matinv", default_size=400)


def run_cpu_eigen_small(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    return _run_cpu_endpoint(cfg, "/compute/eigenvalues", default_size=300)


def run_cpu_fft_medium(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    return _run_cpu_endpoint(cfg, "/compute/fft", default_size=200000)
