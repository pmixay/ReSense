"""The quality wrapper must supply mandatory raw input and expose history failures."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("quality_screen", ROOT / "scripts/quality_screen.py")
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


def fake_pipeline(monkeypatch, history_rc=0):
    commands = []
    totals = {"histories": 33, "stop_frames": 204, "stop_events": 55}

    def run(command, _log):
        commands.append(command)
        output = Path(command[command.index("--out") + 1])
        if command[1] == "scripts/history_stress.py":
            if history_rc == 0:
                output.write_text(json.dumps({"schema": "resense-history-stress-v2", "totals": totals}))
            return history_rc, 0.0
        output.write_text(json.dumps({"set_O": {}}))
        return 0, 0.0

    monkeypatch.setattr(screen, "_run", run)
    return commands, totals


def arguments(tmp_path):
    return ["--name", "candidate", "--work", str(tmp_path), "--no-lock",
            "--reference", str(tmp_path / "absent-reference")]


def test_missing_raw_bag_rejected_before_any_heavy_stage(tmp_path, monkeypatch):
    commands, _ = fake_pipeline(monkeypatch)
    with pytest.raises(SystemExit) as error:
        screen.main(arguments(tmp_path))
    assert error.value.code == 2
    assert commands == []


def test_history_receives_original_bag_and_v2_totals_survive_summary(tmp_path, monkeypatch):
    commands, totals = fake_pipeline(monkeypatch)
    bag = str(tmp_path / "original roundT_doubleT")
    assert screen.main([*arguments(tmp_path), "--bag", bag, "--set", "tracking.stop_keep_low_s=0.3"]) == 0
    history = next(c for c in commands if c[1] == "scripts/history_stress.py")
    assert history[history.index("--bag") + 1] == bag
    assert history[history.index("--set") + 1] == "tracking.stop_keep_low_s=0.3"
    summary = json.loads((tmp_path / "candidate/summary.json").read_text())
    assert summary["p4_history"] == totals
    assert summary["history_execution"] == {"exit_code": 0, "passed": True}


def test_no_history_does_not_require_raw_bag(tmp_path, monkeypatch):
    commands, _ = fake_pipeline(monkeypatch)
    assert screen.main([*arguments(tmp_path), "--no-history"]) == 0
    assert [c[1] for c in commands] == ["scripts/regression_gate.py"]


def test_history_failure_is_nonzero_and_cannot_reuse_stale_totals(tmp_path, monkeypatch):
    fake_pipeline(monkeypatch, history_rc=2)
    work = tmp_path / "candidate"
    work.mkdir()
    (work / "history.json").write_text(json.dumps({"totals": {"histories": 33}}))
    assert screen.main([*arguments(tmp_path), "--bag", str(tmp_path / "bag")]) == 2
    summary = json.loads((work / "summary.json").read_text())
    assert summary["history_execution"] == {"exit_code": 2, "passed": False}
    assert "p4_history" not in summary
