import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from benchmarks.common.io_utils import write_csv, write_json
from benchmarks.runner import summarize_cloud_comparison


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge distributed worker benchmark outputs.")
    parser.add_argument("--input-runs", nargs="+", required=True, help="Run directories to merge")
    parser.add_argument("--output-dir", required=True, help="Directory for merged artifacts")
    return parser.parse_args()


def load_summary_rows(run_dir: Path) -> List[Dict[str, Any]]:
    summary_json = run_dir / "summary.json"
    if not summary_json.exists():
        return []
    with summary_json.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return payload.get("rows", [])


def main() -> None:
    args = parse_args()
    all_rows: List[Dict[str, Any]] = []
    for run in args.input_runs:
        all_rows.extend(load_summary_rows(Path(run)))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "summary.csv", all_rows)
    write_json(output_dir / "summary.json", {"rows": all_rows})

    comparisons = summarize_cloud_comparison(all_rows)
    write_csv(output_dir / "comparison.csv", comparisons)
    write_json(output_dir / "comparison.json", {"comparisons": comparisons})
    print(f"Merged {len(args.input_runs)} worker runs into {output_dir}")


if __name__ == "__main__":
    main()
