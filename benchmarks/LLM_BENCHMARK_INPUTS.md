# LLM Benchmark Inputs (AWS EC2 vs GKE)

Fill this in before executing the benchmark matrix.

## Target endpoints (frozen)

- AWS EC2 base URL: `http://13.218.182.144:5003`
- GKE ingress base URL: `http://34.111.116.109`
- Endpoint mix from built-in scenario suite:
  - `/ask`: `llm_ask_short_low_concurrency`, `llm_ask_short_high_concurrency`, `llm_ask_long_prompt`
  - `/chat`: `llm_chat_multiturn_pooled_sessions`

## Runtime parity (must match across clouds; frozen)

- `GEMINI_MODEL`: `gemini-2.5-flash`
- `UVICORN_WORKERS`: `2`
- `GEMINI_REQUEST_TIMEOUT_SECONDS`: `20`
- `RATE_LIMIT_RPM`: `60`
- `CHAT_CONTEXT_MESSAGES`: `5`
- `REDIS_KEY_PREFIX`: `llm`
- `REDIS_TIMEOUT_SECONDS`: `2`
- `REDIS_SESSION_TTL_SECONDS`: `86400`
- Infra footprint:
  - AWS EC2: `t3.small` (single VM, `us-east-1`)
  - GKE: `e2-standard-2 x2` (single regional cluster/service ingress)

## Load profile (frozen)

- Warmup: 1 iteration per scenario (implemented in `run_all_llm`)
- Test window: fixed iteration counts per scenario:
  - `llm_ask_short_low_concurrency`: `concurrency=3`, `iterations=6`
  - `llm_ask_short_high_concurrency`: `concurrency=8`, `iterations=8`
  - `llm_chat_multiturn_pooled_sessions`: `concurrency=4`, `iterations=4`, `chat_turn_depth=3`
  - `llm_ask_long_prompt`: `concurrency=3`, `iterations=4`
- Ramp strategy: scenario-level stepped matrix (low/high/chat/long)
- Cooldown: `0s`

## Prompt dataset (frozen)

- Prompt set source: `benchmarks/scenarios/llm.py`
- Prompt size buckets:
  - short: 3 prompts (`DEFAULT_SHORT_PROMPTS`)
  - long: 2 prompts (`DEFAULT_LONG_PROMPTS`)
- Chat turn depth: `3` (chat scenario only)
- Session reuse policy:
  - `/ask`: `new_per_request`
  - `/chat`: `pooled`

## Metrics to collect

- Throughput (RPS)
- Latency (p50/p90/p95/p99)
- HTTP error rate by status code
- Gemini failures/timeouts
- Pod CPU / memory / network usage
- Redis saturation/latency
- Ingress 4xx/5xx

## Operational constraints

- Allowed benchmark source CIDR:
- Rate-limit policy during benchmark:
- Any manual throttles or pauses:

## Result metadata

- EC2 run ID: `ec2-hybrid-baseline`
- GKE run ID: `gke-hybrid-baseline`
- Git commit SHA: `d80d405`
- Start timestamp (UTC): `2026-04-29T18:45:16Z`
- End timestamp (UTC): `2026-04-29T18:58:02Z`
- Notes:
  - Both runs completed with `0` failures for all scenarios.
  - EC2 Redis path uses local `redis6` service for this baseline.
  - GKE Redis path uses Kubernetes secret-provided managed endpoint.
