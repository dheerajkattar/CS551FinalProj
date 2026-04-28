# QUEUE_APP AWS Fargate Deployment

This directory adds an AWS container-serverless deployment path for `Applications/QUEUE_APP` while preserving existing local microservice deployment.

## What this stack provisions

- ECS cluster
- Two Fargate services using the same image:
  - API service (`python main.py`)
  - Worker service (`celery -A tasks worker --loglevel=info`)
- Application Load Balancer for the API service
- ElastiCache Redis for Celery broker and result backend
- EFS shared volume mounted to:
  - `/app/uploads`
  - `/app/results`

The environment-variable contract matches current app code:

- `CELERY_BROKER_URL=redis://<redis-endpoint>:6379/0`
- `CELERY_RESULT_BACKEND=redis://<redis-endpoint>:6379/0`

## 1) Build and push image

From repo root:

```bash
aws ecr create-repository --repository-name queue-app || true

aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com

docker build -t queue-app ./Applications/QUEUE_APP
docker tag queue-app:latest 123456789012.dkr.ecr.us-east-1.amazonaws.com/queue-app:latest
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/queue-app:latest
```

Replace `123456789012` with your AWS account ID.

## 2) Prepare CloudFormation parameters

Copy and edit:

```bash
cp infra/queue-aws-fargate/parameters.example.json infra/queue-aws-fargate/parameters.json
```

Set:

- `VpcId`
- `PublicSubnetA`, `PublicSubnetB` (same VPC)
- `AppImageUri`

## 3) Deploy stack

```bash
aws cloudformation deploy \
  --stack-name queue-app-fargate \
  --template-file infra/queue-aws-fargate/cloudformation.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides "$(jq -r '.[] | "\(.ParameterKey)=\(.ParameterValue)"' infra/queue-aws-fargate/parameters.json | xargs)"
```

## 4) Get queue API URL

```bash
aws cloudformation describe-stacks \
  --stack-name queue-app-fargate \
  --query "Stacks[0].Outputs[?OutputKey=='QueueApiBaseUrl'].OutputValue" \
  --output text
```

Set:

```bash
export QUEUE_URL="http://<alb-dns-name>"
```

## 5) Smoke test

```bash
curl "$QUEUE_URL/health"

curl -X POST -F "file=@sample.csv" "$QUEUE_URL/upload"

curl "$QUEUE_URL/status/<job_id>"

curl "$QUEUE_URL/results/<job_id>" -o output.csv
```

## 6) Benchmark wiring

After deploy, update:

- `benchmarks/config.json`
  - `environments.aws.queue_base_url=<QueueApiBaseUrl>`
