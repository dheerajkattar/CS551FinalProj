import time
import uuid
from typing import List

import requests

from benchmarks.common.executor import run_concurrent
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig


def run_queue_upload_poll(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    upload_url = f"{cfg.base_url.rstrip('/')}/upload"
    status_url_template = f"{cfg.base_url.rstrip('/')}/status/{{job_id}}"
    poll_interval = float(cfg.scenario_options.get("poll_interval_seconds", 1.0))
    max_poll_seconds = float(cfg.scenario_options.get("max_poll_seconds", 60.0))

    def op(iteration: int) -> RequestResult:
        csv_payload = (
            "id,name,value\n"
            f"{iteration},item-{uuid.uuid4().hex[:6]},42\n"
            f"{iteration + 1},item-{uuid.uuid4().hex[:6]},58\n"
        )
        files = {"file": (f"bench_{iteration}.csv", csv_payload.encode("utf-8"), "text/csv")}

        start = time.perf_counter()
        try:
            upload_resp = requests.post(upload_url, files=files, timeout=cfg.timeout_seconds)
        except requests.RequestException as exc:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                error=f"upload error: {exc}",
            )

        if upload_resp.status_code != 202:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                status_code=upload_resp.status_code,
                error=f"upload status {upload_resp.status_code}",
            )

        try:
            upload_json = upload_resp.json()
        except ValueError:
            upload_json = {}

        job_id = upload_json.get("job_id")
        if not job_id:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                status_code=upload_resp.status_code,
                error="missing job_id in upload response",
            )

        poll_start = time.perf_counter()
        final_status = "processing"
        final_http = 202
        while time.perf_counter() - poll_start < max_poll_seconds:
            try:
                status_resp = requests.get(
                    status_url_template.format(job_id=job_id),
                    timeout=cfg.timeout_seconds,
                )
            except requests.RequestException:
                time.sleep(poll_interval)
                continue

            final_http = status_resp.status_code
            try:
                status_payload = status_resp.json()
            except ValueError:
                status_payload = {}

            final_status = status_payload.get("status", "unknown")
            if final_status in {"completed", "failed"}:
                break
            time.sleep(poll_interval)

        total_latency_ms = (time.perf_counter() - start) * 1000.0
        completed = final_status == "completed"
        return RequestResult(
            success=completed,
            latency_ms=total_latency_ms,
            status_code=final_http,
            error=None if completed else f"terminal_status={final_status}",
            metadata={
                "job_id": job_id,
                "terminal_status": final_status,
                "e2e_time_seconds": total_latency_ms / 1000.0,
            },
        )

    return run_concurrent(op, cfg.iterations, cfg.concurrency)
