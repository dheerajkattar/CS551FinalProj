import importlib

import pytest
from fastapi.testclient import TestClient


MODULE_NAME = "Applications.LLM_APP.main"


class FakeRedis:
    def __init__(self):
        self._store = {}

    def ping(self):
        return True

    def rpush(self, key, value):
        self._store.setdefault(key, []).append(value)

    def expire(self, key, _ttl):
        return True

    def lrange(self, key, start, end):
        values = self._store.get(key, [])
        if end == -1:
            end = len(values) - 1
        return values[start : end + 1]

    def llen(self, key):
        return len(self._store.get(key, []))

    def delete(self, key):
        self._store.pop(key, None)


class DummyResponse:
    def __init__(self, text):
        self.text = text


class DummyModel:
    def generate_content(self, prompt, request_options=None):
        return DummyResponse(f"echo:{prompt}")


@pytest.fixture
def llm_module(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://fake-redis:6379/0")
    module = importlib.import_module(MODULE_NAME)
    module = importlib.reload(module)
    module.request_windows.clear()
    module.model = None
    module.redis_client = FakeRedis()
    monkeypatch.setattr(module, "get_redis_client", lambda: module.redis_client)
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
    assert llm_module.redis_client.llen(llm_module._session_key("s1")) == 1


@pytest.mark.api
def test_ask_endpoint_empty_question(client):
    response = client.post("/ask", json={"question": "   ", "session_id": "s1"})
    assert response.status_code == 400


@pytest.mark.api
def test_chat_endpoint_empty_message(client):
    response = client.post("/chat", json={"message": "  ", "session_id": "s1"})
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


@pytest.mark.api
def test_rate_limit_returns_429(client, llm_module, monkeypatch):
    monkeypatch.setattr(llm_module, "RATE_LIMIT_RPM", 1)
    llm_module.request_windows.clear()
    monkeypatch.setattr(llm_module, "get_gemini_model", lambda: DummyModel())

    first = client.post("/ask", json={"question": "first", "session_id": "rate"})
    assert first.status_code == 200

    second = client.post("/ask", json={"question": "second", "session_id": "rate"})
    assert second.status_code == 429


@pytest.mark.api
def test_health_degraded_when_key_missing(client, llm_module, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["ready"] is False


@pytest.mark.api
def test_health_degraded_when_redis_unavailable(client, llm_module, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")

    def redis_unavailable():
        raise llm_module.HTTPException(status_code=503, detail="Redis unavailable")

    monkeypatch.setattr(llm_module, "get_redis_client", redis_unavailable)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["ready"] is False
    assert body["redis_ready"] is False


@pytest.mark.api
def test_gemini_model_init_uses_configured_model_name(llm_module, monkeypatch):
    captured = {}
    monkeypatch.setenv("GEMINI_API_KEY", "dummy-key")
    llm_module.model = None
    llm_module.MODEL_NAME = "gemini-test-model"

    def fake_configure(api_key):
        captured["api_key"] = api_key

    class FakeGenerativeModel:
        def __init__(self, model_name):
            captured["model_name"] = model_name

        def generate_content(self, prompt, request_options=None):
            return DummyResponse(prompt)

    monkeypatch.setattr(llm_module.genai, "configure", fake_configure)
    monkeypatch.setattr(llm_module.genai, "GenerativeModel", FakeGenerativeModel)

    model = llm_module.get_gemini_model()
    assert model is not None
    assert captured["api_key"] == "dummy-key"
    assert captured["model_name"] == "gemini-test-model"
