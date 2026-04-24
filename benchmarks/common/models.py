from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RequestResult:
    success: bool
    latency_ms: float
    status_code: Optional[int] = None
    error: Optional[str] = None
    bytes_sent: int = 0
    bytes_received: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioExecutionConfig:
    cloud: str
    app: str
    scenario: str
    base_url: str
    concurrency: int
    iterations: int
    timeout_seconds: int
    retry_count: int
    warmup_iterations: int
    repeat_index: int
    mode: str = "single"
    worker_index: int = 0
    worker_count: int = 1
    cooldown_seconds: float = 0.0
    scenario_options: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioRunResult:
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    request_results: List[Dict[str, Any]]
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metadata": self.metadata,
            "metrics": self.metrics,
            "request_results": self.request_results,
            "notes": self.notes,
        }
