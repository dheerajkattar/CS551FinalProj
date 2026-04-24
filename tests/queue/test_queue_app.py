import importlib
import io
import json
import sys
from pathlib import Path

import pytest


MODULE_NAME = "Applications.QUEUE_APP.main"


@pytest.fixture
def queue_module(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SKIP_QUEUE_DIR_INIT", "1")

    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]

    module = importlib.import_module(MODULE_NAME)
    module.app.config.update(TESTING=True)
    module.initialize_storage_dirs()
    return module


@pytest.fixture
def client(queue_module):
    return queue_module.app.test_client()


@pytest.mark.api
@pytest.mark.asyncmock
def test_upload_validates_missing_file(client):
    response = client.post("/upload", data={}, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"] == "No file provided"


@pytest.mark.api
@pytest.mark.asyncmock
def test_upload_rejects_non_csv(client):
    payload = {"file": (io.BytesIO(b"plain text"), "data.txt")}
    response = client.post("/upload", data=payload, content_type="multipart/form-data")
    assert response.status_code == 400
    assert response.get_json()["error"] == "Only CSV files allowed"


@pytest.mark.api
@pytest.mark.asyncmock
def test_upload_queues_task(client, queue_module, monkeypatch):
    class DummyTask:
        id = "fake-task-id"

    monkeypatch.setattr(queue_module.process_csv_etl, "delay", lambda *_: DummyTask())

    payload = {"file": (io.BytesIO(b"id,name\n1,item"), "data.csv")}
    response = client.post("/upload", data=payload, content_type="multipart/form-data")
    assert response.status_code == 202

    body = response.get_json()
    assert body["message"] == "File uploaded successfully"
    assert body["task_id"] == "fake-task-id"
    assert body["filename"] == "data.csv"


@pytest.mark.api
def test_status_processing_when_no_result_or_error(client):
    response = client.get("/status/job-123")
    assert response.status_code == 202
    assert response.get_json()["status"] == "processing"


@pytest.mark.api
def test_status_completed_when_result_exists(client):
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    result_payload = {"original_rows": 3, "processed_rows": 2}
    (results_dir / "job-abc_result.json").write_text(json.dumps(result_payload), encoding="utf-8")

    response = client.get("/status/job-abc")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "completed"
    assert body["result"]["processed_rows"] == 2


@pytest.mark.api
def test_status_failed_when_error_exists(client):
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    error_payload = {"error": "bad file"}
    (results_dir / "job-err_error.json").write_text(json.dumps(error_payload), encoding="utf-8")

    response = client.get("/status/job-err")
    assert response.status_code == 400
    body = response.get_json()
    assert body["status"] == "failed"
    assert body["error"]["error"] == "bad file"


@pytest.mark.api
def test_results_download_missing(client):
    response = client.get("/results/job-missing")
    assert response.status_code == 404
