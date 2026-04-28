import logging
import os
import time
from collections import defaultdict, deque
from datetime import datetime
from threading import Lock
from typing import Deque, Dict, List

import google.generativeai as genai
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Initialize FastAPI
app = FastAPI(title="LLM FAQ Bot", version="1.0.0")

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-latest")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("GEMINI_REQUEST_TIMEOUT_SECONDS", "20"))
RATE_LIMIT_RPM = int(os.getenv("RATE_LIMIT_RPM", "30"))
CHAT_CONTEXT_MESSAGES = int(os.getenv("CHAT_CONTEXT_MESSAGES", "5"))

logger = logging.getLogger("llm_app")
if not logger.handlers:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())

# In-memory conversation history/rate limiting (single-VM baseline design)
conversation_history: List[dict] = []
request_windows: Dict[str, Deque[float]] = defaultdict(deque)
request_windows_lock = Lock()
model = None

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
    if key_present:
        logger.info(
            "Startup config loaded: model=%s timeout_s=%s rate_limit_rpm=%s context_messages=%s",
            MODEL_NAME,
            REQUEST_TIMEOUT_SECONDS,
            RATE_LIMIT_RPM,
            CHAT_CONTEXT_MESSAGES,
        )
    else:
        logger.warning("GEMINI_API_KEY is not set; /ask and /chat will return 503 until configured.")


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
    except TypeError:
        # Test doubles or older SDK signatures may not accept request_options.
        response = llm_model.generate_content(prompt)

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
        conversation_history.append(entry)

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
            h for h in conversation_history
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
        conversation_history.append(entry)

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
    session_data = [
        h for h in conversation_history
        if h.get("session_id") == session_id
    ]

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
    global conversation_history
    initial_count = len(conversation_history)
    conversation_history = [
        h for h in conversation_history
        if h.get("session_id") != session_id
    ]
    removed = initial_count - len(conversation_history)

    return {
        "session_id": session_id,
        "messages_cleared": removed,
        "message": f"Cleared {removed} messages from session {session_id}"
    }

@app.get("/health")
def health_check():
    """Health check endpoint"""
    key_present = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy" if key_present else "degraded",
        "ready": key_present,
        "service": "LLM FAQ Bot",
        "model": MODEL_NAME,
        "model_initialized": model is not None,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
