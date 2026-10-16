"""Saved decisions must survive importing; newly computed rows carry shared v1 reasons."""
import pytest
import json
from conftest import wait_job

from resense_web.decision import evaluate_decision, import_decision


def test_saved_decision_and_missing_reasons_are_preserved():
    saved = {"obstacle": False, "warning": True, "decision": "GO", "decision_policy": "v2"}
    original = saved.copy()
    import_decision(saved)
    assert saved == original
    assert "caution_reason" not in saved


def test_new_result_gets_shared_policy_metadata():
    result = {"obstacle": False, "warning": True, "health": {"level": "warn"}}
    expected = evaluate_decision(result).to_dict()
    import_decision(result)
    assert {k: result[k] for k in expected} == expected
    assert result["caution_reason"] == ["advisory_object", "health_warning"]


@pytest.mark.parametrize("fields", [{"caution_reason": None}, {"caution_reason": [1]},
                                   {"caution_reason": "health_warning"}, {"decision_policy": False},
                                   {"decision": "GREEN"}, {"decision": []}])
def test_bad_metadata_fails_instead_of_losing_explanations(fields):
    with pytest.raises(ValueError):
        import_decision({"obstacle": False, "decision": "GO", **fields})


def test_worker_storage_http_and_sim_preserve_historical_metadata(client, env):
    rows = [
        {"decision": "CAUTION", "caution_reason": ["advisory_object", "health_warning"], "decision_policy": "v1"},
        {"decision": "GO", "warning": True, "decision_policy": "v2"},
        {"decision": "STOP", "obstacle": True, "stop_held": True, "nearest_distance": 42},
        {"decision": "CAUTION", "caution_reason": ["<b>unknown</b>"]},
    ]
    path = env.server_root / "published.jsonl"
    path.write_text("\n".join(json.dumps({"obstacle": False, "warning": False, "frame": i,
        "stamp": i / 10, "detections": [], "warnings": [], "timing_ms": {"total": 1}, **r})
        for i, r in enumerate(rows)))
    rec = client.post("/api/recordings/from-server", json={"path": path.name})
    assert rec.status_code == 201, rec.text
    job = wait_job(client, client.post("/api/jobs", json={"recording_id": rec.json()["id"]}).json()["id"])
    assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
    run = job["run_id"]
    http = client.get(f"/api/runs/{run}/frames").json()["frames"]
    stored = [json.loads(s) for s in (env.runs_dir / run / "results.jsonl").read_text().splitlines()]
    with client.websocket_connect(f"/api/live/sim?run_id={run}&speed=10") as ws:
        simulated = [ws.receive_json() for _ in rows]
    for channel in (http, stored, simulated):
        for expected, actual in zip(rows, channel):
            assert all(actual[k] == v for k, v in expected.items())
        assert "caution_reason" not in channel[1]
    assert all(r["sim"] for r in simulated)
