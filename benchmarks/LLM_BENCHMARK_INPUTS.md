# LLM Benchmark Inputs (EC2 vs GCE)

Fill this in before executing the benchmark matrix.

## Target endpoints

- EC2 base URL:
- GCE base URL:
- Endpoint mix:
  - `% /ask`
  - `% /chat`

## Runtime parity (must match across clouds)

- `GEMINI_MODEL`:
- `UVICORN_WORKERS`:
- `GEMINI_REQUEST_TIMEOUT_SECONDS`:
- `RATE_LIMIT_RPM`:
- `CHAT_CONTEXT_MESSAGES`:
- VM specs:
  - AWS instance type:
  - GCP instance type:
  - region pair:

## Load profile

- Warmup:
  - duration or request count:
- Test window:
  - duration or request count:
- Concurrency levels:
- Ramp strategy:
  - step, linear, or spike:
- Cooldown window:

## Prompt dataset

- Prompt set ID/version:
- Prompt size buckets:
  - short
  - medium
  - long
- Chat turn depth:
- Session reuse policy:
  - new session per request or pooled sessions:

## Metrics to collect

- Throughput (RPS)
- Latency (p50/p90/p95/p99)
- HTTP error rate by status code
- Gemini failures/timeouts
- VM CPU / memory / network usage

## Operational constraints

- Allowed benchmark source CIDR:
- Rate-limit policy during benchmark:
- Any manual throttles or pauses:

## Result metadata

- Run ID:
- Git commit SHA:
- Start timestamp (UTC):
- End timestamp (UTC):
- Notes (incidents, retries, key observations):
