import time
import uuid
from typing import List

import requests

from benchmarks.common.executor import RateLimiter, run_concurrent
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig


def run_llm_ask(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    url = f"{cfg.base_url.rstrip('/')}/ask"
    rpm_cap = float(cfg.scenario_options.get("requests_per_minute_cap", 12))
    limiter = RateLimiter(rpm_cap)

    def op(iteration: int) -> RequestResult:
        limiter.wait()
        payload = {
            "question": f"What is cloud benchmarking? Iteration {iteration}",
            "session_id": f"bench-ask-{uuid.uuid4().hex[:8]}",
        }
        start = time.perf_counter()
        try:
            response = requests.post(url, json=payload, timeout=cfg.timeout_seconds)
            latency_ms = (time.perf_counter() - start) * 1000.0
        except requests.RequestException as exc:
            return RequestResult(success=False, latency_ms=(time.perf_counter() - start) * 1000.0, error=str(exc))

        success = response.status_code == 200
        return RequestResult(
            success=success,
            latency_ms=latency_ms,
            status_code=response.status_code,
            error=None if success else f"status={response.status_code}",
        )

    return run_concurrent(op, cfg.iterations, cfg.concurrency)


def run_llm_chat_multiturn(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    url = f"{cfg.base_url.rstrip('/')}/chat"
    rpm_cap = float(cfg.scenario_options.get("requests_per_minute_cap", 10))
    limiter = RateLimiter(rpm_cap)

    def op(iteration: int) -> RequestResult:
        session_id = f"bench-chat-{uuid.uuid4().hex[:8]}"
        start = time.perf_counter()

        for message in (
            f"Explain autoscaling in one sentence. Iteration {iteration}.",
            "Now provide one concrete AWS and one GCP example.",
        ):
            limiter.wait()
            payload = {"message": message, "session_id": session_id}
            try:
                response = requests.post(url, json=payload, timeout=cfg.timeout_seconds)
            except requests.RequestException as exc:
                return RequestResult(
                    success=False,
                    latency_ms=(time.perf_counter() - start) * 1000.0,
                    error=str(exc),
                    metadata={"session_id": session_id},
                )
            if response.status_code != 200:
                return RequestResult(
                    success=False,
                    latency_ms=(time.perf_counter() - start) * 1000.0,
                    status_code=response.status_code,
                    error=f"chat status={response.status_code}",
                    metadata={"session_id": session_id},
                )

        latency_ms = (time.perf_counter() - start) * 1000.0
        return RequestResult(
            success=True,
            latency_ms=latency_ms,
            status_code=200,
            metadata={"session_id": session_id, "turns": 2},
        )

    return run_concurrent(op, cfg.iterations, cfg.concurrency)
