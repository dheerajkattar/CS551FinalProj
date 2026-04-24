import time
from typing import Dict, Optional, Tuple

import requests

from benchmarks.common.models import RequestResult


def request_with_retries(
    method: str,
    url: str,
    timeout_seconds: int,
    retry_count: int,
    expected_statuses: Optional[Tuple[int, ...]] = None,
    json_body: Optional[Dict] = None,
    files: Optional[Dict] = None,
) -> RequestResult:
    attempts = max(1, retry_count + 1)
    last_error = None

    for attempt in range(attempts):
        start = time.perf_counter()
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=timeout_seconds,
                json=json_body,
                files=files,
            )
            latency_ms = (time.perf_counter() - start) * 1000.0
            ok = (
                response.status_code in expected_statuses
                if expected_statuses
                else 200 <= response.status_code < 300
            )
            if ok:
                metadata = {}
                try:
                    metadata["json"] = response.json()
                except ValueError:
                    metadata["json"] = None
                return RequestResult(
                    success=True,
                    latency_ms=latency_ms,
                    status_code=response.status_code,
                    bytes_received=len(response.content),
                    metadata=metadata,
                )

            last_error = f"Unexpected status {response.status_code}"
        except requests.RequestException as exc:
            latency_ms = (time.perf_counter() - start) * 1000.0
            last_error = str(exc)
            if attempt == attempts - 1:
                return RequestResult(success=False, latency_ms=latency_ms, error=last_error)

        if attempt < attempts - 1:
            time.sleep(min(0.3 * (attempt + 1), 1.0))

    return RequestResult(success=False, latency_ms=0.0, error=last_error or "Unknown error")
