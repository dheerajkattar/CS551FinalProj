import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmarks.common.models import RequestResult, ScenarioExecutionConfig
from benchmarks.scenarios import llm as llm_scenarios


def _ok_result() -> RequestResult:
    return RequestResult(success=True, latency_ms=10.0, status_code=200, metadata={"json": {"answer": "ok"}})


def test_run_all_llm_returns_expected_scenarios(monkeypatch):
    monkeypatch.setattr(llm_scenarios, "request_with_retries", lambda *args, **kwargs: _ok_result())

    scenario_results = llm_scenarios.run_all_llm("http://localhost:5003")
    scenario_names = [name for name, _ in scenario_results]

    assert scenario_names == [
        "llm_ask_short_low_concurrency",
        "llm_ask_short_high_concurrency",
        "llm_chat_multiturn_pooled_sessions",
        "llm_ask_long_prompt",
    ]
    assert all(metrics["request_count"] > 0 for _, metrics in scenario_results)


def test_run_llm_ask_workload_request_count(monkeypatch):
    call_count = {"n": 0}

    def fake_request(*args, **kwargs):
        call_count["n"] += 1
        return _ok_result()

    monkeypatch.setattr(llm_scenarios, "request_with_retries", fake_request)

    cfg = ScenarioExecutionConfig(
        cloud="local",
        app="llm",
        scenario="ask_count",
        base_url="http://localhost:5003",
        concurrency=2,
        iterations=3,
        timeout_seconds=10,
        retry_count=0,
        warmup_iterations=0,
        repeat_index=0,
        mode="single",
        worker_index=0,
        worker_count=1,
        cooldown_seconds=0.0,
        scenario_options={"prompts": ["a", "b"], "session_policy": "new_per_request"},
    )

    results = llm_scenarios.run_llm_ask_workload(cfg)
    assert len(results) == 6
    assert call_count["n"] == 6


def test_run_llm_chat_workload_request_count(monkeypatch):
    call_count = {"n": 0}

    def fake_request(*args, **kwargs):
        call_count["n"] += 1
        return _ok_result()

    monkeypatch.setattr(llm_scenarios, "request_with_retries", fake_request)

    cfg = ScenarioExecutionConfig(
        cloud="local",
        app="llm",
        scenario="chat_count",
        base_url="http://localhost:5003",
        concurrency=2,
        iterations=3,
        timeout_seconds=10,
        retry_count=0,
        warmup_iterations=0,
        repeat_index=0,
        mode="single",
        worker_index=0,
        worker_count=1,
        cooldown_seconds=0.0,
        scenario_options={
            "prompts": ["chat-prompt"],
            "chat_turn_depth": 4,
            "session_policy": "pooled",
        },
    )

    results = llm_scenarios.run_llm_chat_workload(cfg)
    assert len(results) == 24
    assert call_count["n"] == 24


def test_run_all_llm_records_failures(monkeypatch):
    def fake_request(*args, **kwargs):
        return RequestResult(success=False, latency_ms=5.0, status_code=503, error="upstream")

    monkeypatch.setattr(llm_scenarios, "request_with_retries", fake_request)

    scenario_results = llm_scenarios.run_all_llm("http://localhost:5003")
    assert scenario_results
    assert all(metrics["failure_count"] > 0 for _, metrics in scenario_results)
    assert all(metrics["failure_rate"] > 0 for _, metrics in scenario_results)
