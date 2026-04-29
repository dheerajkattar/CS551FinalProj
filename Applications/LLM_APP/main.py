import logging
import os
import time
import json
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import Deque, Dict, List, Optional

import google.generativeai as genai
import redis
from redis.exceptions import RedisError
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI(title="LLM FAQ Bot", version="1.0.0")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "20"))
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "30"))
CHAT_CONTEXT_MESSAGES = int(os.getenv("CHAT_CONTEXT_MESSAGES", "5"))
REDIS_URL = os.getenv("REDIS_URL", "")
REDIS_KEY_PREFIX = os.getenv("REDIS_KEY_PREFIX", "llm")
REDIS_TIMEOUT_SECONDS = float(os.getenv("REDIS_TIMEOUT_SECONDS", "2"))
REDIS_SESSION_TTL_SECONDS = int(os.getenv("REDIS_SESSION_TTL_SECONDS", "86400"))

logger = logging.getLogger("llm_app")
if not logger.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

# Stateful session storage for Kubernetes deployments + in-memory rate limiting
request_windows: Dict[str, Deque[float]] = defaultdict(deque)
request_windows_lock = Lock()
model = None
redis_client: Optional[redis.Redis] = None

class Question(BaseModel):
    """Request model for asking a question"""
    question: str
    session_id: str = "default"

class Answer(BaseModel):
    """Response model with answer"""
    question: str
    answer: str
    session_id: str
    timestamp: str

class ConversationRequest(BaseModel):
    """Request model for multi-turn conversation"""
    message: str
    session_id: str = "default"


@app.on_event("startup")
def startup_log_configuration():
    key_present = bool(os.getenv("GEMINI_API_KEY"))
    redis_configured = bool(REDIS_URL)
    if key_present:
        logger.info(
            "Startup config loaded: model=%s timeout_s=%s rate_limit_rpm=%s context_messages=%s redis_configured=%s",
            MODEL_NAME,
            REQUEST_TIMEOUT_SECONDS,
            RATE_LIMIT_RPM,
            CHAT_CONTEXT_MESSAGES,
            redis_configured,
        )
    else:
        logger.warning("GEMINI_API_KEY is not set; /ask and /chat will return 503 until configured.")
    if not redis_configured:
        logger.warning("REDIS_URL is not set; history endpoints and chat context are degraded.")


@app.middleware("http")
async def log_request_timing(request: Request, call_next):
    start = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request method=%s path=%s status=%s latency_ms=%.2f",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
        )


def enforce_rate_limit(session_id: str):
    if RATE_LIMIT_RPM <= 0:
        return

    now = time.time()
    cutoff = now - 60

    with request_windows_lock:
        window = request_windows[session_id]
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= RATE_LIMIT_RPM:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded for session {session_id}. Try again shortly.",
            )

        window.append(now)


def _session_key(session_id: str) -> str:
    return f"{REDIS_KEY_PREFIX}:session:{session_id}"


def get_redis_client() -> Optional[redis.Redis]:
    global redis_client
    if not REDIS_URL:
        return None
    if redis_client is not None:
        return redis_client
    try:
        redis_client = redis.Redis.from_url(
            REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
            socket_timeout=REDIS_TIMEOUT_SECONDS,
        )
        redis_client.ping()
    except RedisError as exc:
        logger.exception("Redis initialization failed")
        redis_client = None
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return redis_client


def append_history_entry(session_id: str, entry: dict) -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        key = _session_key(session_id)
        client.rpush(key, json.dumps(entry))
        client.expire(key, REDIS_SESSION_TTL_SECONDS)
        return True
    except RedisError as exc:
        logger.warning("Failed to append session history for session=%s error=%s", session_id, exc)
        return False


def get_session_history(session_id: str) -> List[dict]:
    client = get_redis_client()
    if client is None:
        return []
    try:
        raw_entries = client.lrange(_session_key(session_id), 0, -1)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc

    entries: List[dict] = []
    for raw_entry in raw_entries:
        try:
            parsed = json.loads(raw_entry)
            if isinstance(parsed, dict):
                entries.append(parsed)
        except json.JSONDecodeError:
            continue
    return entries


def clear_session_history(session_id: str) -> int:
    client = get_redis_client()
    if client is None:
        return 0
    key = _session_key(session_id)
    try:
        existing_count = client.llen(key)
        client.delete(key)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail=f"Redis unavailable: {exc}") from exc
    return int(existing_count)


def get_gemini_model():
    global model
    if model is not None:
        return model

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY environment variable not set. Get it from https://aistudio.google.com/app/apikeys",
        )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as exc:
        logger.exception("Failed to initialize Gemini model")
        raise HTTPException(status_code=503, detail=f"Gemini initialization failed: {exc}") from exc

    return model


def generate_answer(prompt: str) -> str:
    llm_model = get_gemini_model()

    try:
        response = llm_model.generate_content(
            prompt,
            request_options={"timeout": REQUEST_TIMEOUT_SECONDS},
        )
    except Exception as exc:
        # Older SDKs can reject request_options with non-TypeError exceptions.
        error_text = str(exc)
        if "request_options" in error_text or "Unknown field" in error_text:
            logger.warning("Falling back to generate_content without request_options")
            response = llm_model.generate_content(prompt)
        else:
            raise

    answer = getattr(response, "text", "")
    if not answer:
        raise HTTPException(status_code=502, detail="Gemini returned an empty response.")
    return answer

@app.get("/")
def read_root():
    """Root endpoint"""
    return {
        "message": "LLM FAQ Bot API",
        "endpoints": {
            "ask": "POST /ask - Single question",
            "chat": "POST /chat - Multi-turn conversation",
            "history": "GET /history/{session_id} - Get conversation history",
            "health": "GET /health - Health check"
        }
    }

@app.post("/ask", response_model=Answer)
def ask_question(request: Question):
    """
    Ask a single question to Gemini

    Example:
    ```
    {
        "question": "What is the capital of France?",
        "session_id": "user123"
    }
    ```
    """
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        enforce_rate_limit(request.session_id)
        answer = generate_answer(request.question)

        # Store in conversation history
        entry = {
            "session_id": request.session_id,
            "question": request.question,
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "role": "faq"
        }
        append_history_entry(request.session_id, entry)

        return Answer(
            question=request.question,
            answer=answer,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Gemini API: {str(e)}")

@app.post("/chat", response_model=Answer)
def chat_conversation(request: ConversationRequest):
    """
    Multi-turn conversation with Gemini
    Maintains context within a session

    Example:
    ```
    {
        "message": "Tell me about machine learning",
        "session_id": "user123"
    }
    ```
    """
    try:
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        enforce_rate_limit(request.session_id)

        # Get conversation context for this session
        session_messages = [
            h for h in get_session_history(request.session_id)
            if h.get("session_id") == request.session_id and h.get("role") != "faq"
        ]

        # Build context from previous messages
        context = "\n".join([
            f"User: {m['message']}\nAssistant: {m['answer']}"
            for m in session_messages[-CHAT_CONTEXT_MESSAGES:]
        ])

        # Create prompt with context
        if context:
            full_prompt = f"Previous conversation:\n{context}\n\nNew message: {request.message}"
        else:
            full_prompt = request.message

        answer = generate_answer(full_prompt)

        # Store in conversation history
        entry = {
            "session_id": request.session_id,
            "message": request.message,
            "answer": answer,
            "timestamp": datetime.now().isoformat(),
            "role": "chat"
        }
        append_history_entry(request.session_id, entry)

        return Answer(
            question=request.message,
            answer=answer,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calling Gemini API: {str(e)}")

@app.get("/history/{session_id}")
def get_conversation_history(session_id: str):
    """
    Get conversation history for a specific session
    """
    session_data = get_session_history(session_id)

    if not session_data:
        raise HTTPException(status_code=404, detail=f"No conversation history found for session {session_id}")

    return {
        "session_id": session_id,
        "message_count": len(session_data),
        "history": session_data
    }

@app.delete("/history/{session_id}")
def clear_conversation_history(session_id: str):
    """
    Clear conversation history for a specific session
    """
    removed = clear_session_history(session_id)

    return {
        "session_id": session_id,
        "messages_cleared": removed,
        "message": f"Cleared {removed} messages from session {session_id}"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    key_present = bool(os.getenv("GEMINI_API_KEY"))
    redis_ready = False
    redis_error = None
    try:
        redis_client_ref = get_redis_client()
        redis_ready = redis_client_ref is not None
    except HTTPException as exc:
        redis_error = exc.detail

    ready = key_present and redis_ready
    return {
        "status": "healthy" if ready else "degraded",
        "ready": ready,
        "service": "LLM FAQ Bot",
        "model": MODEL_NAME,
        "model_initialized": model is not None,
        "redis_configured": bool(REDIS_URL),
        "redis_ready": redis_ready,
        "redis_error": redis_error,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
