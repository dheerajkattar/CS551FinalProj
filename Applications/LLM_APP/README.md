# LLM FAQ Bot with Gemini API

A simple FastAPI application that uses Google's Gemini API (free tier) to answer user questions. Perfect for learning LLM integration and testing on cloud platforms.

## Getting Started

### 1. Get Free Gemini API Key

1. Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Click "Create API Key" → "Create API key in new project"
3. Copy your API key (no credit card required for free tier)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Environment Variable

```bash
export GEMINI_API_KEY="your-api-key-here"
```

Or create a `.env` file:
```bash
GEMINI_API_KEY=your-api-key-here
```

### 4. Run the Application

```bash
python main.py
```

API runs on `http://localhost:5003`

Access interactive docs at `http://localhost:5003/docs`

## API Endpoints

### 1. Ask a Question (Single Turn)
```bash
curl -X POST http://localhost:5003/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "session_id": "user123"
  }'
```

**Response:**
```json
{
  "question": "What is machine learning?",
  "answer": "Machine learning is...",
  "session_id": "user123",
  "timestamp": "2026-04-23T10:30:45.123456"
}
```

### 2. Multi-Turn Conversation (Chat)
```bash
curl -X POST http://localhost:5003/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain neural networks",
    "session_id": "user123"
  }'
```

Maintains conversation context within a session.

### 3. Get Conversation History
```bash
curl http://localhost:5003/history/user123
```

**Response:**
```json
{
  "session_id": "user123",
  "message_count": 5,
  "history": [
    {
      "session_id": "user123",
      "question": "What is ML?",
      "answer": "...",
      "timestamp": "2026-04-23T10:00:00"
    }
  ]
}
```

### 4. Clear Conversation History
```bash
curl -X DELETE http://localhost:5003/history/user123
```

### 5. Health Check
```bash
curl http://localhost:5003/health
```

## Quick Examples

### Example 1: Simple FAQ
```bash
curl -X POST http://localhost:5003/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is Python?", "session_id": "faq1"}'
```

### Example 2: Multi-Turn Conversation
```bash
# First message
curl -X POST http://localhost:5003/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me about Docker", "session_id": "dev1"}'

# Follow-up (maintains context)
curl -X POST http://localhost:5003/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I get started with it?", "session_id": "dev1"}'
```

### Example 3: View Session History
```bash
curl http://localhost:5003/history/dev1
```

## Free Tier Limits

**Gemini 1.5 Flash (Free Tier):**
- 15 requests per minute
- 1 million tokens per day
- Input: free
- Output: free

For more details: [Gemini API Pricing](https://ai.google.dev/pricing)

## Cloud Deployment

### AWS Lambda
```bash
# Use AWS Lambda with FastAPI adapter (Mangum)
pip install mangum

# Deploy with Serverless Framework or CDK
```

### AWS EC2
```bash
# SSH into EC2 instance
ssh -i key.pem ec2-user@your-instance-ip

# Install and run
git clone your-repo
cd your-repo
pip install -r requirements.txt
export GEMINI_API_KEY="your-key"
python main.py &
```

### Google Cloud Run
```bash
# Create Dockerfile (included separately)
gcloud run deploy llm-faq-bot \
  --source . \
  --platform managed \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY="your-key" \
  --allow-unauthenticated
```

### ECS/Fargate
1. Build Docker image
2. Push to ECR
3. Create ECS task definition
4. Set `GEMINI_API_KEY` environment variable
5. Deploy to Fargate

## Features

- ✅ Single-turn Q&A endpoint
- ✅ Multi-turn conversation with context
- ✅ Conversation history tracking
- ✅ Session management
- ✅ Free tier support (Gemini 1.5 Flash)
- ✅ Fast API with interactive docs
- ✅ Error handling
- ✅ Cloud-ready (Lambda, EC2, Cloud Run, ECS, etc.)

## Next Steps

1. Extend with database (PostgreSQL) for persistent storage
2. Add authentication (API keys, JWT)
3. Implement rate limiting
4. Add conversation analytics
5. Deploy to your cloud provider
6. Add caching for repeated questions

## Troubleshooting

**"GEMINI_API_KEY environment variable not set"**
- Make sure to set the environment variable before running the app
- Check with: `echo $GEMINI_API_KEY`

**"Error calling Gemini API"**
- Verify your API key is valid
- Check your rate limit (15 requests/min on free tier)
- Check token usage (1M tokens/day free)

**"Connection refused"**
- Ensure the app is running on port 5003
- Check if port is already in use: `lsof -i :5003`

## Testing

Run from the repository root:

```bash
# LLM API tests
pytest tests/llm -m "api or asyncmock"
```

Notes:
- Tests mock Gemini `generate_content` calls, so a real key is not required.
- A dedicated test validates the `503` response when `GEMINI_API_KEY` is missing.
