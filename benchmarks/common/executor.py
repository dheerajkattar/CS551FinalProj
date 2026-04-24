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
            if now < self._next_allowed:
                time.sleep(self._next_allowed - now)
                now = time.monotonic()
            self._next_allowed = now + self._interval


def run_concurrent(
    operation: Callable[[int], RequestResult],
    iterations: int,
    concurrency: int,
) -> List[RequestResult]:
    results: List[RequestResult] = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        futures = [executor.submit(operation, i) for i in range(iterations)]
        for future in as_completed(futures):
            results.append(future.result())
    return results
