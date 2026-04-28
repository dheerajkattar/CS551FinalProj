import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from benchmarks.common.executor import run_concurrent
from benchmarks.common.http_client import request_with_retries
from benchmarks.common.metrics import build_metrics
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig


def run_simple_notes_user(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    """
    Each concurrent user registers, logs in, then makes CRUD requests independently.
    Returns a list of RequestResult for EACH HTTP REQUEST (not per user).
    """
    base = cfg.base_url.rstrip("/")
    all_request_results: List[RequestResult] = []

    def user_operations(user_index: int) -> List[RequestResult]:
        """Single user: register -> login -> CRUD operations. Returns all HTTP request results."""
        user_results: List[RequestResult] = []

        # Each user gets unique credentials
        unique_id = uuid.uuid4().hex[:8]
        username = f"testuser-{unique_id}"
        email = f"test-{unique_id}@example.com"
        password = "testpass123"

        # -------------------------
        # REGISTER
        # -------------------------
        register_response = request_with_retries(
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
        user_results.append(register_response)

        if not register_response.success:
            return user_results

        # -------------------------
        # LOGIN
        # -------------------------
        login_response = request_with_retries(
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
        user_results.append(login_response)

        if not login_response.success:
            return user_results

        login_json = login_response.metadata.get("json") if login_response.metadata else {}
        session_token = login_json.get("session_token") if isinstance(login_json, dict) else None

        if not session_token:
            return user_results

        auth_headers = {"Authorization": f"Bearer {session_token}"}

        def make_auth_request(method: str, endpoint: str, json_body=None, expected_status=200):
            return request_with_retries(
                method,
                f"{base}{endpoint}",
                timeout_seconds=cfg.timeout_seconds,
                retry_count=cfg.retry_count,
                expected_statuses=(expected_status,),
                json_body=json_body,
                headers=auth_headers,
            )

        # This user makes multiple CRUD operations
        for iteration in range(cfg.iterations):
            # -------------------------
            # CREATE NOTE
            # -------------------------
            create_response = make_auth_request(
                "POST",
                "/notes",
                expected_status=201,
                json_body={
                    "title": f"Note {iteration}",
                    "body": f"Test note content {iteration}",
                },
            )
            user_results.append(create_response)

            if not create_response.success:
                return user_results

            response_json = create_response.metadata.get("json") if create_response.metadata else {}
            note_id = response_json.get("id") if isinstance(response_json, dict) else None

            if not note_id:
                return user_results

            time.sleep(random.uniform(0.05, 0.2))

            # -------------------------
            # READ ONE NOTE
            # -------------------------
            fetch_response = make_auth_request(
                "GET",
                f"/notes/{note_id}",
                expected_status=200,
            )
            user_results.append(fetch_response)

            if not fetch_response.success:
                return user_results

            time.sleep(random.uniform(0.05, 0.2))

            # -------------------------
            # READ ALL NOTES
            # -------------------------
            list_response = make_auth_request(
                "GET",
                "/notes",
                expected_status=200,
            )
            user_results.append(list_response)

            if not list_response.success:
                return user_results

            time.sleep(random.uniform(0.05, 0.2))

            # -------------------------
            # DELETE NOTE
            # -------------------------
            delete_response = make_auth_request(
                "DELETE",
                f"/notes/{note_id}",
                expected_status=200,
            )
            user_results.append(delete_response)

            time.sleep(random.uniform(0.05, 0.2))

        return user_results

    # Run concurrent users and flatten all results
    with ThreadPoolExecutor(max_workers=cfg.concurrency) as executor:
        futures = [executor.submit(user_operations, i) for i in range(cfg.concurrency)]
        for future in as_completed(futures):
            all_request_results.extend(future.result())

    return all_request_results


def run_all_crud(base_url: str) -> List[Tuple[str, dict]]:
    """
    Runs the notes workload with multiple concurrent users.

    Workload:
    - 20 concurrent users, each user makes 10 CRUD operations
    - Each user: register -> login -> repeated create/read/list/delete notes
    - Total: 20 users * 10 ops = 200 requests
    """
    scenarios = [
        ("notes_concurrent_users", run_simple_notes_user, 10, 20),  # 10 ops per user, 20 concurrent users
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
            timeout_seconds=30,
            retry_count=1,
            warmup_iterations=0,
            cooldown_seconds=0,
            repeat_index=0,
            mode="single",
            worker_index=0,
            worker_count=1,
            scenario_options={},
        )

        warmup_cfg = ScenarioExecutionConfig(
            **{**cfg.to_dict(), "iterations": 1}
        )
        runner_fn(warmup_cfg)

        started = time.perf_counter()
        request_results = runner_fn(cfg)
        duration = time.perf_counter() - started

        metrics = build_metrics(request_results, duration)
        results.append((scenario_name, metrics))

    return results