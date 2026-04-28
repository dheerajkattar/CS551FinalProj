from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from datetime import datetime
from typing import Optional

# Initialize FastAPI
app = FastAPI(title="LLM FAQ Bot", version="1.0.0")

# Configure Gemini API
API_KEY = os.getenv('GEMINI_API_KEY')
if not API_KEY:
    raise ValueError("GEMINI_API_KEY environment variable not set. Get it from https://aistudio.google.com/app/apikeys")

genai.configure(api_key=API_KEY)

# Initialize Gemini model
model = genai.GenerativeModel('gemini-1.5-flash-latest')

# In-memory conversation history (can be replaced with database)
conversation_history = []

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

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(MODEL_NAME)
    return model

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

        # Call Gemini API
        llm_model = get_gemini_model()
        response = llm_model.generate_content(request.question)
        answer = response.text

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

        # Get conversation context for this session
        session_messages = [
            h for h in conversation_history
            if h.get("session_id") == request.session_id and h.get("role") != "faq"
        ]

        # Build context from previous messages
        context = "\n".join([
            f"User: {m['message']}\nAssistant: {m['answer']}"
            for m in session_messages[-5:]  # Last 5 messages for context
        ])

        # Create prompt with context
        if context:
            full_prompt = f"Previous conversation:\n{context}\n\nNew message: {request.message}"
        else:
            full_prompt = request.message

        # Call Gemini API
        llm_model = get_gemini_model()
        response = llm_model.generate_content(full_prompt)
        answer = response.text

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
    return {
        "status": "healthy",
        "service": "LLM FAQ Bot",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5003)
