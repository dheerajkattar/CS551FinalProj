# AWS vs GCP Benchmarking Suite

This directory contains benchmarking scripts for comparing the deployed AWS and GCP versions of:

- `CRUD_APP`
- `CPU_APP`
- `QUEUE_APP`
- `LLM_APP`

The suite writes machine-readable artifacts for analysis:

- Raw per-scenario JSON files
- Run-level `summary.csv` and `summary.json`
- Cloud comparison `comparison.csv` and `comparison.json`

## 1) Setup

From repository root:

```bash
python3 -m pip install -r benchmarks/requirements-bench.txt
```

Create a real config from the template:

```bash
cp benchmarks/config.example.json benchmarks/config.json
```

Then update each base URL in `benchmarks/config.json` for both `aws` and `gcp`.

## 2) Single-Client Baseline Run

```bash
python3 -m benchmarks.runner \
  --config benchmarks/config.json \
  --clouds aws gcp \
  --apps crud cpu queue llm \
  --mode single
```

Artifacts are written under:

```text
benchmarks/results/<run_id>/
```

## 3) Optional Distributed Mode

Run one worker per load generator:

```bash
# Worker 0
python3 -m benchmarks.runner --config benchmarks/config.json --mode distributed --worker-index 0 --worker-count 2

# Worker 1
python3 -m benchmarks.runner --config benchmarks/config.json --mode distributed --worker-index 1 --worker-count 2
```

Merge outputs afterward:

```bash
python3 -m benchmarks.merge_distributed \
  --input-runs benchmarks/results/<run_worker0> benchmarks/results/<run_worker1> \
  --output-dir benchmarks/results/<merged_run_id>
```

## 4) Scenario Coverage

- `crud_read_heavy`: repeated `GET /items`
- `crud_mixed_flow`: create + read + update + delete flow
- `cpu_matmul_small`, `cpu_matinv_medium`, `cpu_eigen_small`, `cpu_fft_medium`
- `queue_upload_poll`: upload CSV and poll until terminal state
- `llm_ask`: single-turn prompt
- `llm_chat_multiturn`: two-turn chat sequence

Concurrency/iterations/repeats are controlled in config (`scenarios` + `defaults`).

## 5) Methodology Notes

What is measured:

- Request success/failure counts
- Throughput (requests/sec)
- Latency distribution (`p50`, `p90`, `p95`, `p99`)
- Failure rate
- Queue end-to-end completion time when available

What is intentionally not measured here:

- Cross-region network path analysis
- Host-level CPU/memory counters from the load generator
- Full distributed orchestration/auto-scaling testbed management

## 6) Fair AWS vs GCP Comparison Checklist

- Use matching instance/service sizes and runtime settings.
- Use identical benchmark config parameters for both clouds.
- Include warmup iterations before measured runs.
- Run multiple repeats and compare averages, not single runs.
- Watch for confounders:
  - cold starts
  - transient 5xx spikes
  - LLM external API quota/rate throttling

## 7) Output Interpretation

- Lower latency percentiles are better (`latency_ms_p95` especially).
- Higher throughput is better.
- Lower failure rate is better.
- `comparison.csv` includes AWS vs GCP deltas and winner flags by metric.
