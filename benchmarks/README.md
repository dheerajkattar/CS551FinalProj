# Cloud Application Profiler

Simple performance testing for cloud applications deployed on different architectures (serverless, EC2, Kubernetes, etc.).

## Quick Start

```bash
# Install dependencies
python3 -m pip install -r benchmarks/requirements-bench.txt

# Run benchmark against CRUD app
python3 -m benchmarks.runner --crud-url https://your-crud-endpoint
```

Results saved to `benchmarks/results/<timestamp>/results.json`.

## Usage

```bash
# Single app
python3 -m benchmarks.runner --crud-url http://localhost:5000

# Multiple apps
python3 -m benchmarks.runner \
  --crud-url http://localhost:5000 \
  --cpu-url http://localhost:5001 \
  --queue-url http://localhost:5002 \
  --llm-url http://localhost:5003

# Custom output location
python3 -m benchmarks.runner \
  --crud-url http://localhost:5000 \
  --results-dir /tmp/results \
  --run-label my-test
```

## What's Tested

Each app has predefined scenarios that run automatically when you provide the URL:

**CRUD** (`--crud-url`)
- `notes_concurrent_users`: concurrent user flow that registers, logs in, and runs repeated create/read/list/delete note operations.

**CPU** (`--cpu-url`) — Coming soon

**Queue** (`--queue-url`) — Coming soon

**LLM** (`--llm-url`)
- `llm_ask_short_low_concurrency`: `/ask` with short prompts and light concurrency.
- `llm_ask_short_high_concurrency`: `/ask` with short prompts and higher concurrency.
- `llm_chat_multiturn_pooled_sessions`: `/chat` multi-turn workload with pooled sessions.
- `llm_ask_long_prompt`: `/ask` with longer prompts to exercise token-heavy requests.

## Output

```
benchmarks/results/<run_id>/
└── results.json  # Detailed results with latency percentiles and throughput
```

### Result Fields
- `app`, `scenario` — test metadata
- `request_count`, `success_count`, `failure_count`, `failure_rate` — reliability
- `throughput_rps` — requests per second
- `latency_ms_min/max/avg/p50/p90/p95/p99` — latency percentiles

## Examples

### Run and compare across deployments
```bash
# Test deployment A
python3 -m benchmarks.runner --crud-url https://deployment-a.example.com --run-label deployment-a

# Test deployment B
python3 -m benchmarks.runner --crud-url https://deployment-b.example.com --run-label deployment-b

# Compare results
cat benchmarks/results/deployment-a/results.json
cat benchmarks/results/deployment-b/results.json
```

## Customizing Tests

Edit `benchmarks/scenarios/<app>.py` to modify test parameters:
- Each scenario function includes hardcoded `iterations`, `concurrency`, and think times
- Modify the `run_all_<app>()` function to change defaults
- For LLM, scenario matrix dimensions are controlled via `scenario_options` (prompt list, session policy, chat turn depth).

LLM benchmarking input checklist:
- `benchmarks/LLM_BENCHMARK_INPUTS.md`

