import importlib

import numpy as np
import pytest


MODULE_NAME = "Applications.CPU_APP.main"


@pytest.fixture
def cpu_module():
    return importlib.import_module(MODULE_NAME)


@pytest.fixture
def client(cpu_module):
    cpu_module.app.config.update(TESTING=True)
    return cpu_module.app.test_client()


@pytest.fixture
def mock_metrics(monkeypatch, cpu_module):
    monkeypatch.setattr(cpu_module, "get_system_metrics", lambda: {"cpu_percent": 12.5, "memory_mb": 256.0})


@pytest.mark.api
def test_health_endpoint(client, mock_metrics):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "healthy"
    assert body["cpu_percent"] == 12.5


@pytest.mark.api
def test_matmul_success_with_mocked_numpy(client, cpu_module, mock_metrics, monkeypatch):
    monkeypatch.setattr(cpu_module.np.random, "rand", lambda *shape: np.ones(shape))
    monkeypatch.setattr(cpu_module.np, "matmul", lambda a, b: np.zeros((a.shape[0], b.shape[1])))

    response = client.post("/compute/matmul", json={"size": 3})
    assert response.status_code == 200
    body = response.get_json()
    assert body["operation"] == "matrix_multiplication"
    assert body["matrix_size"] == 3
    assert body["result_shape"] == "(3, 3)"


@pytest.mark.api
def test_matinv_success_with_mocked_numpy(client, cpu_module, mock_metrics, monkeypatch):
    monkeypatch.setattr(cpu_module.np.random, "rand", lambda *shape: np.eye(shape[0]))
    monkeypatch.setattr(cpu_module.np.linalg, "inv", lambda matrix: matrix)

    response = client.post("/compute/matinv", json={"size": 4})
    assert response.status_code == 200
    body = response.get_json()
    assert body["operation"] == "matrix_inversion"
    assert body["result_shape"] == "(4, 4)"


@pytest.mark.api
def test_eigenvalues_success_with_mocked_numpy(client, cpu_module, mock_metrics, monkeypatch):
    monkeypatch.setattr(cpu_module.np.random, "rand", lambda *shape: np.ones(shape))
    monkeypatch.setattr(
        cpu_module.np.linalg,
        "eig",
        lambda matrix: (np.array([1.0, 2.0, 3.0]), np.eye(3)),
    )

    response = client.post("/compute/eigenvalues", json={"size": 3})
    assert response.status_code == 200
    body = response.get_json()
    assert body["operation"] == "eigenvalue_decomposition"
    assert body["num_eigenvalues"] == 3


@pytest.mark.api
def test_fft_success_with_mocked_numpy(client, cpu_module, mock_metrics, monkeypatch):
    monkeypatch.setattr(cpu_module.np.random, "rand", lambda size: np.arange(size))
    monkeypatch.setattr(cpu_module.np.fft, "fft", lambda signal: signal)

    response = client.post("/compute/fft", json={"size": 5})
    assert response.status_code == 200
    body = response.get_json()
    assert body["operation"] == "fast_fourier_transform"
    assert body["signal_size"] == 5
    assert body["result_size"] == 5


@pytest.mark.api
@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("/compute/matmul", {"size": 0}),
        ("/compute/matinv", {"size": 0}),
        ("/compute/eigenvalues", {"size": 0}),
        ("/compute/fft", {"size": 0}),
    ],
)
def test_size_lower_bound_validation(client, endpoint, payload):
    response = client.post(endpoint, json=payload)
    assert response.status_code == 400


@pytest.mark.api
@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("/compute/matmul", {"size": 5001}),
        ("/compute/matinv", {"size": 3001}),
        ("/compute/eigenvalues", {"size": 3001}),
        ("/compute/fft", {"size": 10000001}),
    ],
)
def test_size_upper_bound_validation(client, endpoint, payload):
    response = client.post(endpoint, json=payload)
    assert response.status_code == 400
