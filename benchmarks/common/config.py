import json
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str) -> Dict[str, Any]:
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    required_top_keys = {"environments", "defaults", "scenarios"}
    missing = required_top_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing config keys: {sorted(missing)}")

    for env in ("aws", "gcp"):
        if env not in data["environments"]:
            raise ValueError(f"Missing environments.{env} in config")
        for app_key in ("crud_base_url", "cpu_base_url", "queue_base_url", "llm_base_url"):
            if app_key not in data["environments"][env]:
                raise ValueError(f"Missing environments.{env}.{app_key} in config")

    return data
