# Stateful CRUD API with User Sessions

A Flask application with user authentication, session management, and per-user item storage.

## Features

- User registration and login with password hashing
- Session-based authentication (24-hour expiry)
- Per-user item storage (items are isolated by user)
- Persistent SQLite database (or PostgreSQL)
- Comprehensive logging
- Deployed on GCP Compute Engine with Nginx reverse proxy

## Local Development

```bash
pip install -r requirements.txt
python main.py
```

The API runs on `http://localhost:5000`

## Authentication Flow

### 1. Register a new user

```bash
curl -X POST http://localhost:5000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "securepass123"
  }'
```

Response:
```json
{
  "message": "User registered successfully",
  "user": {"id": 1, "username": "alice", "email": "alice@example.com"}
}
```

### 2. Login

```bash
curl -X POST http://localhost:5000/auth/login \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "username": "alice",
    "password": "securepass123"
  }'
```

This sets an HTTP-only session cookie. Use `-c cookies.txt` to save and `-b cookies.txt` to send on subsequent requests.

Response:
```json
{
  "message": "Login successful",
  "user": {"id": 1, "username": "alice", "email": "alice@example.com"}
}
```

### 3. Get current user info

```bash
curl http://localhost:5000/auth/me -b cookies.txt
```

### 4. Logout

```bash
curl -X POST http://localhost:5000/auth/logout -b cookies.txt
```

## Item Management (Requires Login)

All item operations require an active session. Items are stored per-user.

**Create** - POST `/items`
```bash
curl -X POST http://localhost:5000/items \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name": "Buy groceries", "description": "Milk, eggs, bread"}'
```

**Read All** - GET `/items`
```bash
curl http://localhost:5000/items -b cookies.txt
```

Returns only items owned by the logged-in user.

**Read One** - GET `/items/<id>`
```bash
curl http://localhost:5000/items/1 -b cookies.txt
```

**Update** - PUT `/items/<id>`
```bash
curl -X PUT http://localhost:5000/items/1 \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name": "Buy groceries", "description": "Milk, eggs, bread, cheese"}'
```

**Delete** - DELETE `/items/<id>`
```bash
curl -X DELETE http://localhost:5000/items/1 -b cookies.txt
```

**Health Check** - GET `/health` (no auth required)
```bash
curl http://localhost:5000/health
```

## Database

The app uses SQLite by default for local development. For production on Lambda/GCP, set `DATABASE_URL` to a PostgreSQL endpoint:

```bash
export DATABASE_URL=postgresql://user:password@host:5432/dbname
python main.py
```

## GCP Compute Engine VM Deployment

### VM Setup

```bash
# On GCP (gcloud CLI)
gcloud compute instances create stateful-crud \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2204-lts \
  --tags=crud-app

# Open firewall
gcloud compute firewall-rules create allow-crud-http \
  --allow tcp:80 \
  --target-tags crud-app
```

### Install on VM

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git nginx

cd ~/CS551FinalProj
python3 -m venv .venv
source .venv/bin/activate
pip install -r Applications/CRUD_APP/requirements.txt
pip install gunicorn
```

### Run on VM

Start the app:
```bash
cd Applications/CRUD_APP
gunicorn -b 127.0.0.1:5000 main:app
```

Configure Nginx (see example below), then:
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
```

### Nginx Configuration

Create `/etc/nginx/sites-available/crud_app`:

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cookie_path / "/";
    }
}
```

Enable and reload:
```bash
sudo ln -s /etc/nginx/sites-available/crud_app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Testing

Test from the VM public IP:

```bash
# Register
curl -X POST http://YOUR_VM_IP/auth/register \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"username":"testuser","email":"test@example.com","password":"pass123"}'

# Login
curl -X POST http://YOUR_VM_IP/auth/login \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -c cookies.txt \
  -d '{"username":"testuser","password":"pass123"}'

# Create item
curl -X POST http://YOUR_VM_IP/items \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"Test Item","description":"A test item"}'

# Read items
curl http://YOUR_VM_IP/items -b cookies.txt

# Health check
curl http://YOUR_VM_IP/health
```

## Configuration

Set environment variables:

- `SECRET_KEY`: Session encryption key (required for production)
- `DATABASE_URL`: Database connection string
- `PORT`: Server port (default 5000)
- `FLASK_DEBUG`: Debug mode (set to '1' to enable)
- `SKIP_DB_INIT`: Skip database initialization on startup

Example:
```bash
export SECRET_KEY="your-secret-key-here"
export DATABASE_URL="postgresql://user:pass@localhost/crud_db"
export PORT=5000
python main.py
```

## Architecture

### Models

**User**
- `id` (Integer, Primary Key)
- `username` (String, Unique)
- `email` (String, Unique)
- `password_hash` (String)
- `items` (Relationship)

**Item**
- `id` (Integer, Primary Key)
- `user_id` (Integer, Foreign Key to User)
- `name` (String)
- `description` (String)
- `created_at` (DateTime)

### Session

Sessions are stored using Flask's filesystem session (suitable for single-instance deployment). For distributed deployments, consider:
- Redis-based sessions (Flask-Session + redis)
- JWT tokens
- Database-backed sessions (Flask-Session + SQLAlchemy)

### Security

- Passwords are hashed using werkzeug's PBKDF2 with SHA-256
- Sessions expire after 24 hours
- Items are checked for ownership on every read/update/delete
- HTTP-only session cookies prevent JavaScript access

## Notes

- Data in `/tmp` on Lambda is ephemeral; use persistent PostgreSQL for multi-instance deployments.
- For HTTPS, place Nginx behind a load balancer with TLS termination or use Certbot with Let's Encrypt.
- Monitor session storage size on the VM; for production, migrate to Redis or database-backed sessions.

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

### GCP Compute Engine VM
If you want to run the CRUD app directly on a GCP VM and accept external traffic:

1. Create a Compute Engine VM and open the firewall for the port you will use, usually `5000` for direct Flask testing or `80`/`443` if you place Nginx in front.
2. Install Python and dependencies on the VM.
3. Start the app bound to all interfaces:
```bash
export PORT=5000
python main.py
```
4. Make sure the VM firewall and any `ufw` rules allow inbound traffic to that port.

For a production-style setup, run Gunicorn instead of the Flask development server:
```bash
pip install gunicorn
gunicorn -b 0.0.0.0:5000 main:app
```

If you want the app reachable on the public internet, the key pieces are:
- bind to `0.0.0.0`
- open the VM firewall for the listening port
- optionally place Nginx in front and expose `80`/`443`

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

## Testing

Run from the repository root:

```bash
# CRUD tests only
pytest tests/crud -m "unit or api"
```

Notes:
- Tests use an isolated SQLite database per test run.
- If you run the app locally and see stale data behavior, remove `items.db`.
