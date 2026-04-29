import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Tuple

from benchmarks.common.http_client import request_with_retries
from benchmarks.common.metrics import build_metrics
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig

DEFAULT_SHORT_PROMPTS = [
    "What is cloud computing?",
    "Define latency in one sentence.",
    "What is horizontal scaling?",
]

DEFAULT_LONG_PROMPTS = [
    (
        "Explain tradeoffs between vertical and horizontal scaling for a web API. "
        "Include cost, operational complexity, fault tolerance, and typical bottlenecks. "
        "End with a concise recommendation for a small team running two cloud VMs."
    ),
    (
        "Describe how request rate limiting works in API servers. Cover token bucket, "
        "sliding window, and fixed window approaches, then compare when each is preferred."
    ),
]


def _prompt_for_iteration(prompts: List[str], user_index: int, iteration: int) -> str:
    if not prompts:
        return "Summarize cloud benchmarking in two bullet points."
    prompt_index = (user_index + iteration) % len(prompts)
    return prompts[prompt_index]


def run_llm_ask_workload(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    base = cfg.base_url.rstrip("/")
    all_request_results: List[RequestResult] = []
    prompts = cfg.scenario_options.get("prompts", DEFAULT_SHORT_PROMPTS)
    session_policy = cfg.scenario_options.get("session_policy", "new_per_request")

    def user_operations(user_index: int) -> List[RequestResult]:
        user_results: List[RequestResult] = []
        pooled_session = f"llm-ask-{user_index}-{uuid.uuid4().hex[:8]}"

        for iteration in range(cfg.iterations):
            session_id = (
                pooled_session
                if session_policy == "pooled"
                else f"llm-ask-{user_index}-{iteration}-{uuid.uuid4().hex[:8]}"
            )
            prompt = _prompt_for_iteration(prompts, user_index, iteration)
            response = request_with_retries(
                "POST",
                f"{base}/ask",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(200,),
                json_body={"question": prompt, "session_id": session_id},
            )
            user_results.append(response)

        return user_results

    with ThreadPoolExecutor(max_workers=max(1, cfg.concurrency)) as executor:
        futures = [executor.submit(user_operations, i) for i in range(cfg.concurrency)]
        for future in as_completed(futures):
            all_request_results.extend(future.result())

    return all_request_results


def run_llm_chat_workload(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    base = cfg.base_url.rstrip("/")
    all_request_results: List[RequestResult] = []
    prompts = cfg.scenario_options.get("prompts", DEFAULT_SHORT_PROMPTS)
    turn_depth = int(cfg.scenario_options.get("chat_turn_depth", 3))
    session_policy = cfg.scenario_options.get("session_policy", "pooled")

    def user_operations(user_index: int) -> List[RequestResult]:
        user_results: List[RequestResult] = []
        pooled_session = f"llm-chat-{user_index}-{uuid.uuid4().hex[:8]}"

        for iteration in range(cfg.iterations):
            session_id = (
                pooled_session
                if session_policy == "pooled"
                else f"llm-chat-{user_index}-{iteration}-{uuid.uuid4().hex[:8]}"
            )
            prompt_seed = _prompt_for_iteration(prompts, user_index, iteration)

            for turn in range(turn_depth):
                message = f"{prompt_seed} (turn {turn + 1}/{turn_depth})"
                response = request_with_retries(
                    "POST",
                    f"{base}/chat",
                    timeout_seconds=cfg.timeout_seconds,
                    retry_count=cfg.retry_count,
                    expected_statuses=(200,),
                    json_body={"message": message, "session_id": session_id},
                )
                user_results.append(response)
                if not response.success:
                    break

        return user_results

    with ThreadPoolExecutor(max_workers=max(1, cfg.concurrency)) as executor:
        futures = [executor.submit(user_operations, i) for i in range(cfg.concurrency)]
        for future in as_completed(futures):
            all_request_results.extend(future.result())

    return all_request_results


def run_all_llm(base_url: str) -> List[Tuple[str, Dict[str, float]]]:
    scenarios = [
        (
            "llm_ask_short_low_concurrency",
            run_llm_ask_workload,
            6,
            3,
            {"prompts": DEFAULT_SHORT_PROMPTS, "session_policy": "new_per_request"},
        ),
        (
            "llm_ask_short_high_concurrency",
            run_llm_ask_workload,
            8,
            8,
            {"prompts": DEFAULT_SHORT_PROMPTS, "session_policy": "new_per_request"},
        ),
        (
            "llm_chat_multiturn_pooled_sessions",
            run_llm_chat_workload,
            4,
            4,
            {
                "prompts": DEFAULT_SHORT_PROMPTS,
                "chat_turn_depth": 3,
                "session_policy": "pooled",
            },
        ),
        (
            "llm_ask_long_prompt",
            run_llm_ask_workload,
            4,
            3,
            {"prompts": DEFAULT_LONG_PROMPTS, "session_policy": "new_per_request"},
        ),
    ]

    results: List[Tuple[str, Dict[str, float]]] = []

    for scenario_name, runner_fn, iterations, concurrency, scenario_options in scenarios:
        cfg = ScenarioExecutionConfig(
            cloud="gcp",
            app="llm",
            scenario=scenario_name,
            base_url=base_url,
            concurrency=concurrency,
            iterations=iterations,
            timeout_seconds=30,
            retry_count=1,
            warmup_iterations=0,
            cooldown_seconds=0,
            repeat_index=0,
            mode="single",
            worker_index=0,
            worker_count=1,
            scenario_options=scenario_options,
        )

        warmup_cfg = ScenarioExecutionConfig(**{**cfg.to_dict(), "iterations": 1})
        runner_fn(warmup_cfg)

        started = time.perf_counter()
        request_results = runner_fn(cfg)
        duration = time.perf_counter() - started

        metrics = build_metrics(request_results, duration)
        results.append((scenario_name, metrics))

    return results
