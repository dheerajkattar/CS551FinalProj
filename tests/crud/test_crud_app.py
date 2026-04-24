import importlib
import sys

import pytest


MODULE_NAME = "Applications.CRUD_APP.main"


@pytest.fixture
def crud_module(monkeypatch, tmp_path):
    db_path = tmp_path / "crud_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SKIP_DB_INIT", "1")

    if MODULE_NAME in sys.modules:
        del sys.modules[MODULE_NAME]

    module = importlib.import_module(MODULE_NAME)
    module.app.config.update(TESTING=True)

    with module.app.app_context():
        module.db.drop_all()
        module.db.create_all()

    yield module

    with module.app.app_context():
        module.db.session.remove()
        module.db.drop_all()


@pytest.fixture
def client(crud_module):
    return crud_module.app.test_client()


@pytest.mark.unit
def test_item_to_dict(crud_module):
    item = crud_module.Item(id=7, name="n1", description="d1")
    assert item.to_dict() == {"id": 7, "name": "n1", "description": "d1"}


@pytest.mark.api
def test_crud_lifecycle(client):
    create_resp = client.post("/items", json={"name": "Item 1", "description": "A test item"})
    assert create_resp.status_code == 201
    created = create_resp.get_json()
    assert created["name"] == "Item 1"
    item_id = created["id"]

    list_resp = client.get("/items")
    assert list_resp.status_code == 200
    items = list_resp.get_json()
    assert len(items) == 1
    assert items[0]["id"] == item_id

    get_resp = client.get(f"/items/{item_id}")
    assert get_resp.status_code == 200
    assert get_resp.get_json()["description"] == "A test item"

    update_resp = client.put(f"/items/{item_id}", json={"name": "Updated"})
    assert update_resp.status_code == 200
    assert update_resp.get_json()["name"] == "Updated"

    delete_resp = client.delete(f"/items/{item_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.get_json()["id"] == item_id

    not_found_resp = client.get(f"/items/{item_id}")
    assert not_found_resp.status_code == 404


@pytest.mark.api
def test_read_update_delete_not_found(client):
    assert client.get("/items/9999").status_code == 404
    assert client.put("/items/9999", json={"name": "x"}).status_code == 404
    assert client.delete("/items/9999").status_code == 404
