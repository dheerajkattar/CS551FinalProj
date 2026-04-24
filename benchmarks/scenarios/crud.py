import time
import uuid
from typing import List

from benchmarks.common.executor import run_concurrent
from benchmarks.common.http_client import request_with_retries
from benchmarks.common.models import RequestResult, ScenarioExecutionConfig


def run_crud_read_heavy(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    endpoint = f"{cfg.base_url.rstrip('/')}/items"

    def op(_: int) -> RequestResult:
        return request_with_retries(
            method="GET",
            url=endpoint,
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(200,),
        )

    return run_concurrent(op, cfg.iterations, cfg.concurrency)


def run_crud_mixed_flow(cfg: ScenarioExecutionConfig) -> List[RequestResult]:
    base = cfg.base_url.rstrip("/")

    def op(iteration: int) -> RequestResult:
        start = time.perf_counter()
        trace_id = f"{cfg.cloud}-{cfg.repeat_index}-{iteration}-{uuid.uuid4().hex[:8]}"

        create_payload = {
            "name": f"bench-item-{trace_id}",
            "description": "benchmark flow item",
        }
        created_item_id = None
        steps = []

        create_result = request_with_retries(
            "POST",
            f"{base}/items",
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(201,),
            json_body=create_payload,
        )
        steps.append({"step": "create", "status_code": create_result.status_code, "success": create_result.success})
        if not create_result.success:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                status_code=create_result.status_code,
                error=create_result.error or "create failed",
                metadata={"steps": steps},
            )

        create_json = create_result.metadata.get("json") if create_result.metadata else None
        created_item_id = create_json.get("id") if isinstance(create_json, dict) else None
        if not created_item_id:
            return RequestResult(
                success=False,
                latency_ms=(time.perf_counter() - start) * 1000.0,
                status_code=create_result.status_code,
                error="create id capture failed",
                metadata={"steps": steps},
            )

        get_result = request_with_retries(
            "GET",
            f"{base}/items/{created_item_id}",
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(200,),
        )
        steps.append({"step": "get", "status_code": get_result.status_code, "success": get_result.success})

        update_result = request_with_retries(
            "PUT",
            f"{base}/items/{created_item_id}",
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(200,),
            json_body={"description": "benchmark updated"},
        )
        steps.append({"step": "update", "status_code": update_result.status_code, "success": update_result.success})

        delete_result = request_with_retries(
            "DELETE",
            f"{base}/items/{created_item_id}",
            timeout_seconds=cfg.timeout_seconds,
            retry_count=cfg.retry_count,
            expected_statuses=(200,),
        )
        steps.append({"step": "delete", "status_code": delete_result.status_code, "success": delete_result.success})

        success = all(step["success"] for step in steps)
        return RequestResult(
            success=success,
            latency_ms=(time.perf_counter() - start) * 1000.0,
            status_code=200 if success else 500,
            error=None if success else "one or more CRUD flow steps failed",
            metadata={"steps": steps},
        )

    return run_concurrent(op, cfg.iterations, cfg.concurrency)
