import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List

from benchmarks.common.models import RequestResult


class RateLimiter:
    def __init__(self, requests_per_minute: float):
        self._interval = 60.0 / requests_per_minute if requests_per_minute > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def wait(self) -> None:
        if self._interval <= 0:
            return

        with self._lock:
            now = time.monotonic()
            sleep_for = self._next_allowed - now

            if sleep_for > 0:
                time.sleep(sleep_for)
                now = time.monotonic()

            self._next_allowed = now + self._interval


def run_concurrent_users(
    operation: Callable[[int, int], RequestResult],
    iterations_per_user: int,
    concurrency: int,
    requests_per_minute: float = 0,
) -> List[RequestResult]:
    """
    Simulates multiple users.

    concurrency = number of concurrent users
    iterations_per_user = number of requests each user sends

    operation(user_id, iteration_id) should perform one I/O request
    and return a RequestResult.
    """

    results: List[RequestResult] = []
    results_lock = threading.Lock()
    rate_limiter = RateLimiter(requests_per_minute)

    def user_worker(user_id: int) -> None:
        user_results: List[RequestResult] = []

        for iteration_id in range(iterations_per_user):
            rate_limiter.wait()
            result = operation(user_id, iteration_id)
            user_results.append(result)

        with results_lock:
            results.extend(user_results)

    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = [
            executor.submit(user_worker, user_id)
            for user_id in range(concurrency)
        ]

        for future in as_completed(futures):
            future.result()

    return results