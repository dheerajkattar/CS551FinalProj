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

### AWS RDS PostgreSQL
1. Create an RDS PostgreSQL instance
2. Set the `DATABASE_URL` environment variable:
```bash
export DATABASE_URL=postgresql://username:password@your-rds-endpoint.rds.amazonaws.com:5432/dbname
python main.py
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

The app automatically uses the `DATABASE_URL` environment variable. If not set, it defaults to SQLite for local development.

## Database Support

The app works with any SQLAlchemy-supported database:
- SQLite (default, local development)
- PostgreSQL (AWS RDS, GCP Cloud SQL)
- MySQL (AWS RDS, GCP Cloud SQL)

## Testing

Run from the repository root:

```bash
# CRUD tests only
pytest tests/crud -m "unit or api"
```

Notes:
- Tests use an isolated SQLite database per test run.
- If you run the app locally and see stale data behavior, remove `items.db`.
