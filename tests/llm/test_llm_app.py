import importlib

import pytest
from fastapi.testclient import TestClient


MODULE_NAME = "Applications.LLM_APP.main"


class DummyResponse:
    def __init__(self, text):
        self.text = text


class DummyModel:
    def generate_content(self, prompt):
        return DummyResponse(f"echo:{prompt}")


@pytest.fixture
def llm_module(monkeypatch):
    module = importlib.import_module(MODULE_NAME)
    module.conversation_history = []
    module.model = None
    return module


@pytest.fixture
def client(llm_module):
    return TestClient(llm_module.app)


@pytest.mark.api
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "LLM FAQ Bot"


@pytest.mark.api
@pytest.mark.asyncmock
def test_ask_endpoint_success(client, llm_module, monkeypatch):
    monkeypatch.setattr(llm_module, "get_gemini_model", lambda: DummyModel())

    response = client.post("/ask", json={"question": "What is ML?", "session_id": "s1"})
    assert response.status_code == 200
    body = response.json()
    assert body["question"] == "What is ML?"
    assert body["answer"].startswith("echo:")
    assert body["session_id"] == "s1"
    assert len(llm_module.conversation_history) == 1


@pytest.mark.api
def test_ask_endpoint_empty_question(client):
    response = client.post("/ask", json={"question": "   ", "session_id": "s1"})
    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.asyncmock
def test_chat_history_and_clear_flow(client, llm_module, monkeypatch):
    monkeypatch.setattr(llm_module, "get_gemini_model", lambda: DummyModel())

    first = client.post("/chat", json={"message": "Explain Docker", "session_id": "chat1"})
    assert first.status_code == 200

    second = client.post("/chat", json={"message": "How do I start?", "session_id": "chat1"})
    assert second.status_code == 200

    history = client.get("/history/chat1")
    assert history.status_code == 200
    history_body = history.json()
    assert history_body["message_count"] == 2
    assert len(history_body["history"]) == 2

    clear = client.delete("/history/chat1")
    assert clear.status_code == 200
    assert clear.json()["messages_cleared"] == 2

    after_clear = client.get("/history/chat1")
    assert after_clear.status_code == 404


@pytest.mark.api
def test_missing_gemini_key_returns_503(client, llm_module, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    llm_module.model = None

    response = client.post("/ask", json={"question": "Hi", "session_id": "s1"})
    assert response.status_code == 503


@pytest.mark.api
@pytest.mark.asyncmock
def test_gemini_error_returns_500(client, llm_module, monkeypatch):
    class ExplodingModel:
        def generate_content(self, _):
            raise RuntimeError("upstream failure")

    monkeypatch.setattr(llm_module, "get_gemini_model", lambda: ExplodingModel())

    response = client.post("/ask", json={"question": "Hi", "session_id": "s1"})
    assert response.status_code == 500
