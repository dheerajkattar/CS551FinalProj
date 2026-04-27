# Simple CRUD API

A minimal CRUD application with Flask and configurable database support.

## Local Development

```bash
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:5000`

## API Endpoints

**Create** - POST `/items`
```bash
curl -X POST http://localhost:5000/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Item 1", "description": "A test item"}'
```

**Read All** - GET `/items`
```bash
curl http://localhost:5000/items
```

**Read One** - GET `/items/<id>`
```bash
curl http://localhost:5000/items/1
```

**Update** - PUT `/items/<id>`
```bash
curl -X PUT http://localhost:5000/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Item", "description": "Updated description"}'
```

**Delete** - DELETE `/items/<id>`
```bash
curl -X DELETE http://localhost:5000/items/1
```

**Health Check** - GET `/health`
```bash
curl http://localhost:5000/health
```

## Cloud Deployment

### AWS Lambda + API Gateway (Serverless)
This app includes a Serverless Framework config for Lambda deployment.

1. Install deployment tooling:
```bash
npm install -g serverless
```

2. Configure AWS credentials:
```bash
aws configure
```

3. Deploy with the default SQLite configuration:
```bash
pip install -r requirements.txt
serverless deploy
```

By default, Lambda uses:
```bash
DATABASE_URL=sqlite:////tmp/items.db
```

4. Test the deployed endpoint (replace with your API URL):
```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/health
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/items \
  -H "Content-Type: application/json" \
  -d '{"name":"Serverless Item","description":"created on lambda"}'
```

#### Benchmarking Notes for SQLite on Lambda
- SQLite storage under `/tmp` is ephemeral and tied to each Lambda execution environment.
- Data can be lost when environments are recycled.
- Separate Lambda instances do not share the same SQLite file.
- `reservedConcurrency: 1` is set in `serverless.yml` to keep benchmark behavior more consistent.

### AWS RDS PostgreSQL (Optional Advanced Setup)
If you later want persistent shared storage:
```bash
export DATABASE_URL=postgresql://username:password@your-rds-endpoint.rds.amazonaws.com:5432/dbname
serverless deploy
```

### GCP Cloud SQL PostgreSQL
1. Create a Cloud SQL PostgreSQL instance
2. Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL=postgresql://username:password@your-cloudsql-endpoint:5432/dbname
python main.py
```

Or use Cloud SQL Proxy (recommended):
```bash
cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432 &
export DATABASE_URL=postgresql://username:password@127.0.0.1:5432/dbname
python main.py
```

## Configuration

Copy `.env.example` to `.env` and customize:
```bash
cp .env.example .env
```

The app automatically uses the `DATABASE_URL` environment variable.
- Local default: `sqlite:///items.db`
- Lambda default (if unset): `sqlite:////tmp/items.db`

## Database Support

The app works with any SQLAlchemy-supported database:
- SQLite (default, local + simple Lambda benchmark mode)
- PostgreSQL (AWS RDS, GCP Cloud SQL)
- MySQL (AWS RDS, GCP Cloud SQL)
