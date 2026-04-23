# Queue-Based ETL Application

An event-driven ETL (Extract, Transform, Load) pipeline that processes CSV files asynchronously using a message queue. Perfect for cloud-based data processing workflows.

## Architecture

- **Flask API**: Accepts file uploads and provides job status endpoints
- **Celery**: Distributed task queue for async processing
- **Redis**: Message broker for job queue
- **Pandas**: Data processing and transformation

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start Redis (message broker)

**Option A: Docker (Recommended)**
```bash
docker run -d -p 6379:6379 redis:latest
```

**Option B: Local Installation**
```bash
# macOS
brew install redis
redis-server

# Ubuntu/Debian
sudo apt-get install redis-server
redis-server
```

### 3. Start the Application

**Terminal 1 - Flask API:**
```bash
python main.py
```

**Terminal 2 - Celery Worker:**
```bash
celery -A tasks worker --loglevel=info
```

API runs on `http://localhost:5002`

## API Endpoints

### Upload CSV File
```bash
curl -X POST -F "file=@data.csv" http://localhost:5002/upload
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "task_id": "abc123...",
  "filename": "data.csv",
  "timestamp": "2026-04-23T10:30:45.123456"
}
```

### Check Job Status
```bash
curl http://localhost:5002/status/550e8400-e29b-41d4-a716-446655440000
```

**Response (Processing):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "Job is still being processed"
}
```

**Response (Completed):**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "result": {
    "original_rows": 1000,
    "processed_rows": 950,
    "duplicate_rows_removed": 50,
    "columns": ["id", "name", "value", ...],
    "statistics": {
      "value": {
        "mean": 42.5,
        "median": 40.0,
        "std": 15.3,
        "min": 0,
        "max": 100
      }
    }
  }
}
```

### Download Processed Results
```bash
curl http://localhost:5002/results/550e8400-e29b-41d4-a716-446655440000 \
  -o output.csv
```

### Health Check
```bash
curl http://localhost:5002/health
```

## ETL Pipeline Steps

### Extract
- Reads CSV file from upload

### Transform
1. **Deduplication**: Removes duplicate rows
2. **Cleaning**: Removes completely empty rows
3. **Missing Values**: Fills numeric columns with mean, categorical with "Unknown"
4. **Normalization**: Scales numeric columns to 0-1 range
5. **Enrichment**: Adds `processed_at` timestamp to all rows
6. **Statistics**: Calculates mean, median, std, min, max for numeric columns

### Load
- Saves processed CSV to `results/` folder
- Saves metadata and statistics to JSON

## Environment Variables

```bash
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

For cloud deployment (AWS/GCP):
```bash
# AWS ElastiCache
export CELERY_BROKER_URL=redis://your-elasticache-endpoint:6379/0

# GCP Memorystore
export CELERY_BROKER_URL=redis://your-memorystore-endpoint:6379/0
```

## Cloud Deployment

### AWS
1. Set up **ElastiCache Redis** instance
2. Deploy Flask app on **EC2** or **ECS**
3. Run Celery workers on **EC2** or **ECS**
4. Store results in **S3**

### GCP
1. Set up **Cloud Memorystore** (Redis) instance
2. Deploy Flask app on **Cloud Run** or **App Engine**
3. Run Celery workers on **Compute Engine** or **Cloud Tasks**
4. Store results in **Cloud Storage**

## Example Workflow

```bash
# 1. Create a sample CSV
cat > sample.csv << EOF
id,name,value,category
1,Item A,42,A
2,Item B,58,B
3,Item A,42,A
4,Item C,,C
5,,100,A
EOF

# 2. Upload file
RESPONSE=$(curl -s -X POST -F "file=@sample.csv" http://localhost:5002/upload)
JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
echo "Job ID: $JOB_ID"

# 3. Check status (wait a moment for processing)
sleep 2
curl http://localhost:5002/status/$JOB_ID | jq .

# 4. Download results
curl http://localhost:5002/results/$JOB_ID -o results.csv
cat results.csv
```

## Scaling Considerations

- **Horizontal Scaling**: Add more Celery workers to process jobs in parallel
- **Job Queue**: Large files will queue and be processed by available workers
- **Monitoring**: Use Flower for Celery monitoring: `flower -A tasks --port=5555`
- **Error Handling**: Failed jobs create error JSON files with details
