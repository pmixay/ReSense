"""Presets: the built-in standard, CRUD, validation through resense_web.params, and a job that
runs with a user preset."""
from __future__ import annotations

from conftest import random_clouds, wait_job, write_bag

from resense_web import params


def _float_spec():
    return next(s for s in params.PARAM_SPECS if s["type"] == "float")


def test_standard_and_schema(client):
    presets = client.get("/api/presets").json()
    assert presets[0]["id"] == "standard" and presets[0]["builtin"] is True and presets[0]["overrides"] == {}
    assert presets[0]["name"] == "Стандарт 1.0"
    schema = client.get("/api/presets/schema").json()
    assert 12 <= len(schema) <= 20
    for spec in schema:
        assert {"key", "group", "label", "help", "type", "default"} <= set(spec)
        assert spec["type"] in ("float", "int", "bool")
    r = client.patch("/api/presets/standard", json={"name": "x"})
    assert r.status_code == 403 and "копию" in r.json()["detail"]
    r = client.delete("/api/presets/standard")
    assert r.status_code == 403 and "Стандарт" in r.json()["detail"]
    r = client.get("/api/presets/nosuch")
    assert r.status_code == 404 and r.json()["detail"] == "Пресет не найден"


def test_crud_and_validation(client):
    spec = _float_spec()
    value = spec["min"]
    r = client.post("/api/presets", json={"name": "Осторожный", "description": "для жюри",
                                          "overrides": {spec["key"]: value}})
    assert r.status_code == 201, r.text
    p = r.json()
    assert p["builtin"] is False and p["overrides"] == {spec["key"]: value} and p["created_at"]
    assert [x["id"] for x in client.get("/api/presets").json()] == ["standard", p["id"]]
    assert client.get(f"/api/presets/{p['id']}").json()["name"] == "Осторожный"

    for body, status, needle in (
        ({"name": "A", "overrides": {"no.such_key": 1}}, 422, "Неизвестный параметр"),
        ({"name": "B", "overrides": {spec["key"]: spec["max"] + 1000}}, 422, "вне диапазона"),
        ({"name": "C", "overrides": {spec["key"]: "abc"}}, 422, "число"),
        ({"name": "  ", "overrides": {}}, 422, "название пресета"),
        ({"name": "осторожный", "overrides": {}}, 409, "Пресет с таким названием уже есть"),
        ({"name": "Стандарт 1.0", "overrides": {}}, 409, "уже есть"),
        ({"overrides": {}}, 422, "name"),
    ):
        r = client.post("/api/presets", json=body)
        assert r.status_code == status, (body, r.text)
        assert needle in r.json()["detail"], r.json()

    r = client.patch(f"/api/presets/{p['id']}", json={"description": "новое"})
    assert r.status_code == 200 and r.json()["description"] == "новое" and r.json()["overrides"] == p["overrides"]
    r = client.patch(f"/api/presets/{p['id']}", json={"overrides": {}})
    assert r.json()["overrides"] == {}
    r = client.patch(f"/api/presets/{p['id']}", json={"overrides": {"nope": 1}})
    assert r.status_code == 422
    r = client.patch(f"/api/presets/{p['id']}", json={"name": "Осторожный"})        # its own name is fine
    assert r.status_code == 200
    assert client.patch("/api/presets/nosuch", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/presets/{p['id']}").status_code == 204
    assert client.delete(f"/api/presets/{p['id']}").status_code == 404
    assert [x["id"] for x in client.get("/api/presets").json()] == ["standard"]


def test_job_with_a_preset(client, env):
    key = "tracking.confirm_time_s" if "tracking.confirm_time_s" in params.PARAM_KEYS else _float_spec()["key"]
    spec = next(s for s in params.PARAM_SPECS if s["key"] == key)
    value = spec["max"]
    preset = client.post("/api/presets", json={"name": "Медленный", "overrides": {key: value}}).json()
    write_bag(env.server_root / "tiny", random_clouds(3, 800))
    rec = client.post("/api/recordings/from-server", json={"path": "tiny"}).json()
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "preset_id": preset["id"]})
    assert r.status_code == 201 and r.json()["preset_name"] == "Медленный"
    # the preset may change or disappear later: the queued job keeps what it was created with
    client.delete(f"/api/presets/{preset['id']}")
    job = wait_job(client, r.json()["id"])
    assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
    run = client.get(f"/api/runs/{job['run_id']}").json()
    assert run["name"] == "tiny · Медленный" and run["preset"] == {"id": preset["id"], "name": "Медленный"}
    report = client.get(f"/api/runs/{job['run_id']}/download/report.json").json()
    section, name = key.split(".", 1)
    assert report["config"][section][name] == value and report["overrides"] == {key: value}
    assert client.post(f"/api/jobs/{job['id']}/retry").status_code == 409                # preset deleted
