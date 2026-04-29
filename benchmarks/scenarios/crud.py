import random
import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Tuple

from benchmarks.common.http_client import request_with_retries
from benchmarks.common.metrics import build_metrics
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig


def run_users(
    cfg: ScenarioExecutionConfig,
    user_fn: Callable[[int], List[RequestResult]],
    stagger_seconds: float = 0.2,
) -> List[RequestResult]:
    all_results: List[RequestResult] = []
    lock = threading.Lock()

    def wrapped_user(user_index: int) -> None:
        if stagger_seconds > 0:
            time.sleep(random.uniform(0, stagger_seconds))

        results = user_fn(user_index)

        with lock:
            all_results.extend(results)

    with ThreadPoolExecutor(max_workers=cfg.concurrency) as executor:
        futures = [executor.submit(wrapped_user, i) for i in range(cfg.concurrency)]
        for future in as_completed(futures):
            future.result()

    return all_results


def auth_user(base: str, cfg: ScenarioExecutionConfig) -> Tuple[Dict[str, str], List[RequestResult]]:
    results: List[RequestResult] = []

    unique_id = uuid.uuid4().hex[:10]
    username = f"testuser-{unique_id}"
    email = f"test-{unique_id}@example.com"
    password = "testpass123"

    register = request_with_retries(
        "POST",
        f"{base}/auth/register",
        timeout_seconds=cfg.timeout_seconds,
        retry_count=cfg.retry_count,
        expected_statuses=(201,),
        json_body={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    results.append(register)

    if not register.success:
        return {}, results

    login = request_with_retries(
        "POST",
        f"{base}/auth/login",
        timeout_seconds=cfg.timeout_seconds,
        retry_count=cfg.retry_count,
        expected_statuses=(200,),
        json_body={
            "username": username,
            "password": password,
        },
    )
    results.append(login)

    if not login.success:
        return {}, results

    login_json = login.metadata.get("json") if login.metadata else {}
    token = login_json.get("session_token") if isinstance(login_json, dict) else None

    if not token:
        return {}, results

    return {"Authorization": f"Bearer {token}"}, results


def make_note(
    base: str,
    cfg: ScenarioExecutionConfig,
    headers: Dict[str, str],
    title: str,
    body: str,
) -> RequestResult:
    return request_with_retries(
        "POST",
        f"{base}/notes",
        timeout_seconds=cfg.timeout_seconds,
        retry_count=cfg.retry_count,
        expected_statuses=(201,),
        headers=headers,
        json_body={"title": title, "body": body},
    )


def extract_note_id(response: RequestResult):
    response_json = response.metadata.get("json") if response.metadata else {}
    if not isinstance(response_json, dict):
        return None
    return response_json.get("id")


# -------------------------
# 1. COLD-ish STATELESS TEST
# -------------------------
def run_cold_health(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Small number of spaced-out health checks.
    Useful for seeing first-request / cold-ish behavior.
    """
    base = cfg.base_url.rstrip("/")
    results: List[RequestResult] = []

    for _ in range(cfg.iterations):
        res = request_with_retries(
            "GET",
            f"{base}/health",
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(200,),
        )
        results.append(res)

        # spacing makes Cloud Run more likely to show cold/idle behavior
        time.sleep(1.0)

    return results


# -------------------------
# 2. WARM STATELESS TEST
# -------------------------
def run_warm_health(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Stateless repeated health checks.
    Tests HTTP routing/runtime overhead without DB.
    """
    base = cfg.base_url.rstrip("/")

    def user_fn(user_index: int) -> List[RequestResult]:
        results = []
        for _ in range(cfg.iterations):
            res = request_with_retries(
                "GET",
                f"{base}/health",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(200,),
            )
            results.append(res)
        return results

    return run_users(cfg, user_fn, stagger_seconds=0.0)


# -------------------------
# 3. AUTH / SESSION TEST
# -------------------------
def run_auth_burst(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Tests user creation, password hashing, login, and DB-backed session creation.
    """
    base = cfg.base_url.rstrip("/")

    def user_fn(user_index: int) -> List[RequestResult]:
        results = []
        for _ in range(cfg.iterations):
            _, auth_results = auth_user(base, cfg)
            results.extend(auth_results)
            time.sleep(random.uniform(0.02, 0.1))
        return results

    return run_users(cfg, user_fn)


# -------------------------
# 4. WRITE-HEAVY TEST
# -------------------------
def run_write_notes(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Tests DB insert pressure after one login per user.
    """
    base = cfg.base_url.rstrip("/")

    def user_fn(user_index: int) -> List[RequestResult]:
        headers, results = auth_user(base, cfg)

        if not headers:
            return results

        for i in range(cfg.iterations):
            res = make_note(
                base,
                cfg,
                headers,
                title=f"Write note {user_index}-{i}",
                body="Insert-heavy benchmark note.",
            )
            results.append(res)
            time.sleep(random.uniform(0.01, 0.08))

        return results

    return run_users(cfg, user_fn)


# -------------------------
# 5. READ-HEAVY TEST
# -------------------------
def run_read_notes(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Seeds a few notes per user, then repeatedly reads /notes.
    Tests DB read/query behavior.
    """
    base = cfg.base_url.rstrip("/")

    def user_fn(user_index: int) -> List[RequestResult]:
        headers, results = auth_user(base, cfg)

        if not headers:
            return results

        for i in range(5):
            seed = make_note(
                base,
                cfg,
                headers,
                title=f"Seed note {user_index}-{i}",
                body="Seed data for read-heavy benchmark.",
            )
            results.append(seed)

        for _ in range(cfg.iterations):
            res = request_with_retries(
                "GET",
                f"{base}/notes",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(200,),
                headers=headers,
            )
            results.append(res)
            time.sleep(random.uniform(0.01, 0.06))

        return results

    return run_users(cfg, user_fn)


# -------------------------
# 6. MIXED USER FLOW
# -------------------------
def run_mixed_notes(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Realistic flow:
    create note -> get note -> list notes -> delete note.
    """
    base = cfg.base_url.rstrip("/")

    def user_fn(user_index: int) -> List[RequestResult]:
        headers, results = auth_user(base, cfg)

        if not headers:
            return results

        for i in range(cfg.iterations):
            create = make_note(
                base,
                cfg,
                headers,
                title=f"Mixed note {user_index}-{i}",
                body="Realistic create-read-list-delete benchmark.",
            )
            results.append(create)

            if not create.success:
                continue

            note_id = extract_note_id(create)
            if not note_id:
                continue

            time.sleep(random.uniform(0.02, 0.12))

            get_one = request_with_retries(
                "GET",
                f"{base}/notes/{note_id}",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(200,),
                headers=headers,
            )
            results.append(get_one)

            get_all = request_with_retries(
                "GET",
                f"{base}/notes",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(200,),
                headers=headers,
            )
            results.append(get_all)

            delete = request_with_retries(
                "DELETE",
                f"{base}/notes/{note_id}",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(200,),
                headers=headers,
            )
            results.append(delete)

            time.sleep(random.uniform(0.02, 0.12))

        return results

    return run_users(cfg, user_fn)


# -------------------------
# SCENARIO RUNNER
# -------------------------
def run_all_crud(base_url: str) -> List[Tuple[str, dict]]:
    scenarios = [
        # Cold-ish/serverless startup behavior.
        ("cold_health", run_cold_health, 5, 1),

        # Warm stateless routing/runtime overhead.
        ("warm_health", run_warm_health, 30, 20),

        # DB writes + password hashing + session creation.
        ("auth_burst", run_auth_burst, 5, 10),

        # Insert-heavy DB pressure.
        ("write_notes", run_write_notes, 25, 10),

        # Query-heavy DB pressure.
        ("read_notes", run_read_notes, 30, 10),

        # Realistic normal user flow.
        ("mixed_notes", run_mixed_notes, 10, 10),

        # Sudden high-concurrency spike.
        ("burst_mixed", run_mixed_notes, 5, 40),

        # Longer steady load.
        ("sustained_mixed", run_mixed_notes, 20, 15),
    ]

    results = []

    for scenario_name, runner_fn, iterations, concurrency in scenarios:
        cfg = ScenarioExecutionConfig(
            cloud="gcp",
            app="notes",
            scenario=scenario_name,
            base_url=base_url,
            concurrency=concurrency,
            iterations=iterations,
            timeout_seconds=45,
            retry_count=2,
            warmup_iterations=0,
            cooldown_seconds=3,
            repeat_index=0,
            mode="single",
            worker_index=0,
            worker_count=1,
            scenario_options={},
        )

        # Warmup except for cold test, because warming would hide cold behavior.
        if scenario_name != "cold_health":
            warmup_cfg = ScenarioExecutionConfig(
                **{**cfg.to_dict(), "iterations": 1, "concurrency": 1}
            )
            runner_fn(warmup_cfg)

        started = time.perf_counter()
        request_results = runner_fn(cfg)
        duration = time.perf_counter() - started

        metrics = build_metrics(request_results, duration)
        results.append((scenario_name, metrics))

        time.sleep(cfg.cooldown_seconds)

    return results