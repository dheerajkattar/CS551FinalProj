from dataclasses import dataclass
from typing import Callable, Dict, List

from benchmarks.common.models import RequestResult, ScenarioExecutionConfig
from benchmarks.scenarios.cpu import (
    run_cpu_eigen_small,
    run_cpu_fft_medium,
    run_cpu_matinv_medium,
    run_cpu_matmul_small,
)
from benchmarks.scenarios.crud import run_crud_mixed_flow, run_crud_read_heavy
from benchmarks.scenarios.llm import run_llm_ask, run_llm_chat_multiturn
from benchmarks.scenarios.queue import run_queue_upload_poll


@dataclass(frozen=True)
class ScenarioDefinition:
    name: str
    app: str
    endpoint_key: str
    runner: Callable[[ScenarioExecutionConfig], List[RequestResult]]


SCENARIO_DEFINITIONS: Dict[str, ScenarioDefinition] = {
    "crud_read_heavy": ScenarioDefinition(
        name="crud_read_heavy",
        app="crud",
        endpoint_key="crud_base_url",
        runner=run_crud_read_heavy,
    ),
    "crud_mixed_flow": ScenarioDefinition(
        name="crud_mixed_flow",
        app="crud",
        endpoint_key="crud_base_url",
        runner=run_crud_mixed_flow,
    ),
    "cpu_matmul_small": ScenarioDefinition(
        name="cpu_matmul_small",
        app="cpu",
        endpoint_key="cpu_base_url",
        runner=run_cpu_matmul_small,
    ),
    "cpu_matinv_medium": ScenarioDefinition(
        name="cpu_matinv_medium",
        app="cpu",
        endpoint_key="cpu_base_url",
        runner=run_cpu_matinv_medium,
    ),
    "cpu_eigen_small": ScenarioDefinition(
        name="cpu_eigen_small",
        app="cpu",
        endpoint_key="cpu_base_url",
        runner=run_cpu_eigen_small,
    ),
    "cpu_fft_medium": ScenarioDefinition(
        name="cpu_fft_medium",
        app="cpu",
        endpoint_key="cpu_base_url",
        runner=run_cpu_fft_medium,
    ),
    "queue_upload_poll": ScenarioDefinition(
        name="queue_upload_poll",
        app="queue",
        endpoint_key="queue_base_url",
        runner=run_queue_upload_poll,
    ),
    "llm_ask": ScenarioDefinition(
        name="llm_ask",
        app="llm",
        endpoint_key="llm_base_url",
        runner=run_llm_ask,
    ),
    "llm_chat_multiturn": ScenarioDefinition(
        name="llm_chat_multiturn",
        app="llm",
        endpoint_key="llm_base_url",
        runner=run_llm_chat_multiturn,
    ),
}


def get_scenarios_for_apps(apps: List[str]) -> List[ScenarioDefinition]:
    allowed = set(apps)
    return [definition for definition in SCENARIO_DEFINITIONS.values() if definition.app in allowed]
