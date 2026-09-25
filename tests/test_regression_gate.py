"""The comparison logic of the regression gate (scripts/regression_gate.py) on synthetic result
dicts: which metrics gate, better / same / worse, --allow, the optional sets (a gated metric of
the baseline missing in this run fails unless allowed), the exit code.
No data needed."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "regression_gate.py"
SPEC = importlib.util.spec_from_file_location("resense_regression_gate", PATH)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

EMPTY = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
         "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"]


def _recording(frames, alarm_frames, events, episodes, first=None, labelled=None):
    return {"frames": frames, "alarm_frames": alarm_frames, "alarm_events": events, "stop_episodes": episodes,
            "first_alarm_frame": first, "advisory_frames": 10, "alarm_dist": None,
            "health": {"ok": frames, "warn": 0, "error": 0}, "monitored_range_median": 150.0,
            "labelled": labelled}


def _inside(stop, first_m, held_m, visible=100, advisory=0):
    return {"in_gauge": True, "visible_frames": visible, "first_visible_m": 120.0, "frames_in_envelope": visible,
            "stop_frames": stop, "advisory_frames": advisory, "first_stop_m": first_m,
            "first_stop_frame": None if first_m is None else 10, "held_from_m": held_m,
            "verdict": "detected" if stop else "missed", "bins": {}}


def _outside(false_stop, visible=100, advisory=5):
    return {"in_gauge": False, "visible_frames": visible, "first_visible_m": 120.0, "frames_in_envelope": 0,
            "stop_frames": false_stop, "advisory_frames": advisory, "false_stop_frames": false_stop,
            "false_stop_from_m": None, "verdict": "false alarm" if false_stop else "advisory", "bins": {}}


def result():
    """A complete gate JSON as scripts/regression_gate.py writes it (numbers of 25.09, set O cut
    to three objects)."""
    rec = {"doubleT_obstacle": _recording(201, 188, 2, 3, first=11, labelled={
        "per_label": {"object_on_rail": {"hits": 127, "frames": 185},
                      "person_crossing": {"hits": 58, "frames": 61},
                      "object_on_rail_from_frame_75": {"hits": 124, "frames": 126}},
        "hits": 185, "frames": 246, "fp_frames": 0, "fp_events": 0, "distance_error_max_m": 0.23})}
    for bag, (fr, af, ev, ep) in zip(EMPTY, [(345, 4, 4, 1), (252, 2, 1, 1), (268, 0, 0, 0), (545, 0, 0, 0),
                                             (877, 101, 15, 25)]):
        rec[bag] = _recording(fr, af, ev, ep)
    objects = {"big_center": _inside(207, 98.0, 98.7), "small_center": _inside(19, 34.0, 37.4),
               "thin_hanging": _inside(0, None, None), "big_outside": _outside(6)}
    return {
        "schema": gate.SCHEMA, "created": "2026-09-25T00:00:00+00:00",
        "code": {"commit": "abc", "branch": "x", "version": "0.6.3", "uncommitted_detector_changes": []},
        "config": {"path": "configs/default.yaml", "set": [], "sha256": "0" * 64, "file_sha256": "1" * 64},
        "native": {"path": "native", "status": "native (_resense_native.so)"},
        "run": {"cache": "/data/cache", "jobs": 2, "nominal_stamps": False, "wall_s": 1.0, "machine": {}},
        "recordings": rec,
        "five_empty": {"frames": 2287, "alarm_frames": 107, "alarm_events": 20, "stop_episodes": 27,
                       "advisory_frames": 50},
        "ride": {"available": False, "reason": "no cache in /data/cache/new_data"},
        "set_O": {"available": True, "frames": 1510, "alarm_frames": 342, "inside_stop_frames": 226,
                  "inside_visible_frames": 300, "inside_objects_with_stop": 2, "inside_objects": 3,
                  "outside_false_stop_frames": 6, "background": {"alarm_frames": 3, "track_ids": 2},
                  "objects": objects},
        "set_F_straight": {"available": False, "reason": "no cache in /data/cache/new_data"},
        "latency_ms": {"note": "informational", "doubleT_obstacle": {"mean_ms": 40.0, "p95_ms": 50.0, "max_ms": 60.0}},
    }


def with_ride(r, events=47, episodes=39, alarm_frames=204, frames=11271):
    r = copy.deepcopy(r)
    r["ride"] = {"available": True, "chunks": 8, "frames": frames, "alarm_frames": alarm_frames,
                 "alarm_events": events, "stop_episodes": episodes, "first_alarm_frame": 3,
                 "advisory_frames": 4737}
    return r


def with_set_f(r, detected=6, median=147.5, false=9):
    r = copy.deepcopy(r)
    r["set_F_straight"] = {"available": True, "parameters": dict(gate.SET_F_STRAIGHT), "kinds": {
        "person": {"sequences": 6, "detected": detected, "first_detection_median_m": median,
                   "sustained_median_m": 149.4, "false_detections": false, "recall_by_bin": {}}}}
    return r


def rows_by_metric(base, new, allow=()):
    return {r["metric"]: r for r in gate.compare(base, new, allow)}


def failing(base, new, allow=()):
    return [r["metric"] for r in gate.compare(base, new, allow) if r["fails"]]


# ---------------------------------------------------------------------------------------------
def test_identical_runs_pass_with_every_row_same():
    base = result()
    rows = gate.compare(base, copy.deepcopy(base))
    assert rows and all(r["verdict"] == "same" for r in rows)
    assert not any(r["fails"] for r in rows)
    assert gate.gate_summary(rows, base, "b.json", [])["passed"]


def test_the_gated_metrics_are_exactly_the_documented_ones():
    gated = {k for k, (_, _, g) in gate.metrics(with_set_f(with_ride(result()))).items() if g}
    expected = {f"recordings.{b}.frames" for b in ["doubleT_obstacle"] + EMPTY}
    expected |= {f"recordings.{b}.{k}" for b in EMPTY for k in ("alarm_events", "stop_episodes")}
    k = "recordings.doubleT_obstacle"
    expected |= {f"{k}.first_alarm_frame", f"{k}.labelled.fp_events", f"{k}.labelled.object_on_rail.hits",
                 f"{k}.labelled.person_crossing.hits", f"{k}.labelled.object_on_rail_from_frame_75.hits"}
    expected |= {"ride.frames", "ride.alarm_events", "ride.stop_episodes", "set_O.frames",
                 "set_O.background.alarm_frames", "set_O.background.track_ids"}
    expected |= {f"set_O.objects.{o}.{m}" for o in ("big_center", "small_center", "thin_hanging")
                 for m in ("stop_frames", "first_stop_m")}
    expected |= {"set_O.objects.big_outside.false_stop_frames"}
    expected |= {f"set_F_straight.person.{m}" for m in ("detected", "first_detection_median_m", "false_detections")}
    assert gated == expected
    assert not any(k.startswith("latency_ms") for k in gated)


@pytest.mark.parametrize("key", ["alarm_events", "stop_episodes"])
def test_more_false_alarms_on_an_obstacle_free_recording_fail(key):
    base = result()
    new = copy.deepcopy(base)
    new["recordings"]["roundT_doubleT"][key] += 1
    assert failing(base, new) == [f"recordings.roundT_doubleT.{key}"]
    new["recordings"]["roundT_doubleT"][key] -= 2
    row = rows_by_metric(base, new)[f"recordings.roundT_doubleT.{key}"]
    assert row["verdict"] == "better" and not row["fails"]


def test_alarm_frames_advisory_frames_and_totals_are_information_only():
    base = result()
    new = copy.deepcopy(base)
    new["recordings"]["doubleT_platform"]["alarm_frames"] += 30
    new["recordings"]["doubleT_platform"]["advisory_frames"] += 30
    new["five_empty"]["alarm_frames"] += 30
    new["recordings"]["doubleT_obstacle"]["alarm_events"] += 1      # the labelled recording: fp_events gates there
    new["recordings"]["doubleT_obstacle"]["stop_episodes"] += 1
    rows = rows_by_metric(base, new)
    assert rows["recordings.doubleT_platform.alarm_frames"]["verdict"] == "worse"
    assert not rows["recordings.doubleT_platform.alarm_frames"]["gated"]
    assert failing(base, new) == []


def test_labelled_recording_hits_first_alarm_and_false_events():
    base = result()
    new = copy.deepcopy(base)
    new["recordings"]["doubleT_obstacle"]["labelled"]["per_label"]["person_crossing"]["hits"] = 57
    assert failing(base, new) == ["recordings.doubleT_obstacle.labelled.person_crossing.hits"]
    new = copy.deepcopy(base)
    new["recordings"]["doubleT_obstacle"]["first_alarm_frame"] = 12
    assert failing(base, new) == ["recordings.doubleT_obstacle.first_alarm_frame"]
    new["recordings"]["doubleT_obstacle"]["first_alarm_frame"] = None       # never alarmed: the worst
    assert failing(base, new) == ["recordings.doubleT_obstacle.first_alarm_frame"]
    new["recordings"]["doubleT_obstacle"]["first_alarm_frame"] = 9
    assert rows_by_metric(base, new)["recordings.doubleT_obstacle.first_alarm_frame"]["verdict"] == "better"
    new = copy.deepcopy(base)
    new["recordings"]["doubleT_obstacle"]["labelled"]["fp_events"] = 1
    assert failing(base, new) == ["recordings.doubleT_obstacle.labelled.fp_events"]
    new = copy.deepcopy(base)
    new["recordings"]["doubleT_obstacle"]["labelled"]["distance_error_max_m"] = 0.5
    assert failing(base, new) == []


def test_set_o_inside_objects_stop_frames_and_first_stop():
    base = result()
    new = copy.deepcopy(base)
    new["set_O"]["objects"]["small_center"]["stop_frames"] = 18
    assert failing(base, new) == ["set_O.objects.small_center.stop_frames"]
    new = copy.deepcopy(base)
    new["set_O"]["objects"]["big_center"]["first_stop_m"] = 97.9                 # a later first STOP
    assert failing(base, new) == ["set_O.objects.big_center.first_stop_m"]
    new["set_O"]["objects"]["big_center"]["first_stop_m"] = None                 # no STOP at all
    assert failing(base, new) == ["set_O.objects.big_center.first_stop_m"]
    new = copy.deepcopy(base)
    new["set_O"]["objects"]["thin_hanging"].update(stop_frames=3, first_stop_m=10.0)   # a missed object found
    rows = rows_by_metric(base, new)
    assert rows["set_O.objects.thin_hanging.first_stop_m"]["verdict"] == "better"
    assert rows["set_O.objects.thin_hanging.stop_frames"]["verdict"] == "better"
    new["set_O"]["objects"]["small_center"]["held_from_m"] = 20.0                # held-from: information
    new["set_O"]["objects"]["small_center"]["advisory_frames"] = 5
    rows = rows_by_metric(base, new)
    assert rows["set_O.objects.small_center.held_from_m"]["verdict"] == "worse"
    assert rows["set_O.objects.small_center.advisory_frames"]["verdict"] == "changed"
    assert failing(base, new) == []


def test_set_o_outside_objects_and_background():
    base = result()
    new = copy.deepcopy(base)
    new["set_O"]["objects"]["big_outside"]["false_stop_frames"] = 7
    assert failing(base, new) == ["set_O.objects.big_outside.false_stop_frames"]
    new = copy.deepcopy(base)
    new["set_O"]["background"] = {"alarm_frames": 4, "track_ids": 3}
    assert failing(base, new) == ["set_O.background.alarm_frames", "set_O.background.track_ids"]


def test_allow_patterns_turn_an_intended_trade_off_into_a_pass():
    base = result()
    new = copy.deepcopy(base)
    new["set_O"]["objects"]["big_outside"]["false_stop_frames"] = 9               # +3 false STOP ...
    new["set_O"]["objects"]["small_center"]["stop_frames"] = 40                   # ... for +21 STOP frames
    allow = ["set_O.objects.big_outside.*"]
    assert failing(base, new, allow) == []
    rows = rows_by_metric(base, new, allow)
    assert rows["set_O.objects.big_outside.false_stop_frames"]["allowed"]
    g = gate.gate_summary(gate.compare(base, new, allow), base, "b.json", allow)
    assert g["passed"] and g["worse_allowed"] == ["set_O.objects.big_outside.false_stop_frames"]
    assert "set_O.objects.small_center.stop_frames" in g["better"]
    assert failing(base, new, ["set_O.objects.small_*"]) == ["set_O.objects.big_outside.false_stop_frames"]


def test_different_frame_counts_fail_as_different_data():
    base = result()
    new = copy.deepcopy(base)
    new["recordings"]["roundT_doubleT"]["frames"] = 241
    row = rows_by_metric(base, new)["recordings.roundT_doubleT.frames"]
    assert row["verdict"] == "differs" and row["fails"]


def test_latency_never_gates():
    base = result()
    new = copy.deepcopy(base)
    new["latency_ms"]["doubleT_obstacle"] = {"mean_ms": 400.0, "p95_ms": 900.0, "max_ms": 2000.0}
    rows = rows_by_metric(base, new)
    assert rows["latency_ms.doubleT_obstacle.p95"]["verdict"] == "worse"
    assert failing(base, new) == []


RIDE_GATED = ["ride.frames", "ride.alarm_events", "ride.stop_episodes"]
SET_F_GATED = [f"set_F_straight.person.{m}" for m in ("detected", "first_detection_median_m", "false_detections")]
WITHOUT_RIDE = ["ride.*", "set_F_straight.*"]


def test_ride_rows_gate_when_both_runs_have_it():
    base = with_ride(result())
    assert failing(base, with_ride(result(), events=48)) == ["ride.alarm_events"]
    assert failing(base, with_ride(result(), episodes=40)) == ["ride.stop_episodes"]
    assert failing(base, with_ride(result(), alarm_frames=300)) == []


def test_a_gated_metric_missing_in_this_run_fails():
    """The baseline has the ride and set F straight, this run has no <cache>/new_data: their gated
    rows fail as missing (the gate cannot tell they are not worse), the information rows do not."""
    base = with_set_f(with_ride(result()))
    new = result()                                         # this run has no ride cache
    assert failing(base, new) == RIDE_GATED + SET_F_GATED
    rows = rows_by_metric(base, new)
    row = rows["ride.alarm_events"]
    assert row["verdict"] == gate.MISSING == "missing in this run"
    assert row["gated"] and row["fails"] and not row["allowed"]
    assert (row["baseline"], row["current"]) == (47, None)
    info = rows["ride.alarm_frames"]                        # not gated: information, never a failure
    assert info["verdict"] == "not in this run" and not info["gated"] and not info["fails"]
    assert rows["set_F_straight.person.sustained_median_m"]["verdict"] == "not in this run"
    g = gate.gate_summary(gate.compare(base, new), base, "b.json", [])
    assert not g["passed"]
    assert g["worse_gated"] == [] and g["missing_gated"] == RIDE_GATED + SET_F_GATED
    assert g["info_changed"] == []
    # the missing data sets are named, with why and the --allow that accepts running without them
    assert gate.missing_lines(gate.compare(base, new), new) == [
        "MISSING in this run: ride (set E): 3 gated row(s) of the baseline not checked "
        "(no cache in /data/cache/new_data)",
        "MISSING in this run: set F straight: 3 gated row(s) of the baseline not checked "
        "(no cache in /data/cache/new_data)",
        "   these rows fail the gate; to accept running without them on purpose: "
        "--allow 'ride.*' --allow 'set_F_straight.*'"]
    assert gate.unavailable(base, new) == []               # said by the MISSING lines, not a note


def test_a_missing_gated_metric_allowed_passes():
    base = with_set_f(with_ride(result()))
    new = result()
    assert failing(base, new, WITHOUT_RIDE) == []
    rows = gate.compare(base, new, WITHOUT_RIDE)
    assert all(r["allowed"] for r in rows if r["verdict"] == gate.MISSING)
    g = gate.gate_summary(rows, base, "b.json", WITHOUT_RIDE)
    assert g["passed"] and g["missing_allowed"] == RIDE_GATED + SET_F_GATED
    assert g["missing_gated"] == [] and g["worse_allowed"] == []
    assert gate.missing_lines(rows, new) == [
        "missing in this run, accepted by --allow: ride (set E): 3 gated row(s) of the baseline not "
        "checked (no cache in /data/cache/new_data)",
        "missing in this run, accepted by --allow: set F straight: 3 gated row(s) of the baseline not "
        "checked (no cache in /data/cache/new_data)"]
    # --allow 'ride.*' alone accepts the ride only: set F straight still fails
    assert failing(base, new, ["ride.*"]) == SET_F_GATED
    # a worse metric of a set that did run still fails with the ride allowed
    worse = copy.deepcopy(new)
    worse["recordings"]["roundT_doubleT"]["alarm_events"] += 1
    assert failing(base, worse, WITHOUT_RIDE) == ["recordings.roundT_doubleT.alarm_events"]


def test_a_metric_only_in_this_run_is_information():
    base = result()                                        # a baseline without the ride
    new = with_set_f(with_ride(result()))
    assert failing(base, new) == []
    rows = rows_by_metric(base, new)
    for key in RIDE_GATED + SET_F_GATED:
        assert rows[key]["verdict"] == "not in baseline" and not rows[key]["gated"] and not rows[key]["fails"]
    assert gate.gate_summary(gate.compare(base, new), base, "b.json", [])["passed"]
    assert gate.missing_lines(gate.compare(base, new), new) == []
    assert gate.unavailable(base, new) == ["ride (set E): this run only; not compared",
                                           "set F straight: this run only; not compared"]


def test_a_recording_or_object_missing_from_an_earlier_result_fails():
    base = result()
    new = copy.deepcopy(base)
    del new["recordings"]["roundT_doubleT"]
    del new["set_O"]["objects"]["small_center"]
    assert failing(base, new) == [f"recordings.roundT_doubleT.{m}" for m in ("frames", "alarm_events", "stop_episodes")] \
        + ["set_O.objects.small_center.stop_frames", "set_O.objects.small_center.first_stop_m"]
    lines = gate.missing_lines(gate.compare(base, new), new)
    assert lines[0] == "MISSING in this run: recording roundT_doubleT: 3 gated row(s) of the baseline not checked"
    assert lines[1] == "MISSING in this run: set O: 2 gated row(s) of the baseline not checked"
    assert lines[2].endswith("--allow 'recordings.roundT_doubleT.*' --allow 'set_O.*'")
    assert failing(base, new, ["recordings.roundT_doubleT.*", "set_O.objects.small_center.*"]) == []


def test_both_runs_without_the_ride_is_a_note_not_a_failure():
    base, new = result(), result()
    assert failing(base, new) == []
    assert gate.unavailable(base, new) == [
        "ride (set E): not available in either run (no cache in /data/cache/new_data)",
        "set F straight: not available in either run (no cache in /data/cache/new_data)"]


def test_set_f_straight_detected_first_confirmation_and_false_detections():
    base = with_set_f(result())
    assert failing(base, with_set_f(result(), detected=5)) == ["set_F_straight.person.detected"]
    assert failing(base, with_set_f(result(), median=140.0)) == ["set_F_straight.person.first_detection_median_m"]
    assert failing(base, with_set_f(result(), median=None)) == ["set_F_straight.person.first_detection_median_m"]
    assert failing(base, with_set_f(result(), false=10)) == ["set_F_straight.person.false_detections"]
    assert failing(base, with_set_f(result(), median=150.0, false=8)) == []


def test_notes_on_runs_that_are_not_like_for_like():
    base = with_ride(result())
    new = with_ride(result())
    new["run"]["nominal_stamps"] = True
    new["ride"]["chunks"] = 4
    notes = gate.unavailable(base, new)
    assert any(n.startswith("stamps differ") for n in notes)
    assert any(n.startswith("ride pieces differ (8 -> 4)") for n in notes)


def test_a_failed_set_f_run_on_a_cached_ride_exits_2(tmp_path):
    broken = result()
    broken["set_F_straight"] = {"available": False, "error": True, "reason": "far_range_eval.py failed: x"}
    p = tmp_path / "broken.json"
    p.write_text(json.dumps(broken))
    b = tmp_path / "base.json"
    b.write_text(json.dumps(result()))
    assert gate.main(["--from-json", str(p), "--baseline", str(b)]) == 2


def test_verdict_none_handling():
    assert gate.verdict(None, None, gate.HIGHER) == "same"
    assert gate.verdict(None, 5.0, gate.HIGHER) == "better"
    assert gate.verdict(5.0, None, gate.HIGHER) == "worse"
    assert gate.verdict(None, 3, gate.LOWER) == "better"
    assert gate.verdict(3, None, gate.LOWER) == "worse"
    assert gate.verdict(1, 2, gate.EQUAL) == "differs"


def test_cli_compare_only_exit_codes(tmp_path, capsys):
    base = result()
    b = tmp_path / "base.json"
    b.write_text(json.dumps(base))
    same = tmp_path / "same.json"
    same.write_text(json.dumps(base))
    assert gate.main(["--from-json", str(same), "--baseline", str(b)]) == 0
    assert "GATE PASS" in capsys.readouterr().out
    worse = copy.deepcopy(base)
    worse["recordings"]["squareT_platform_squareT_switch"]["alarm_events"] = 16
    w = tmp_path / "worse.json"
    w.write_text(json.dumps(worse))
    out = tmp_path / "gate.json"
    assert gate.main(["--from-json", str(w), "--baseline", str(b), "--out", str(out)]) == 1
    text = capsys.readouterr().out
    assert "GATE FAIL" in text and "<< FAIL" in text
    written = json.loads(out.read_text())
    assert written["gate"]["passed"] is False
    assert written["gate"]["worse_gated"] == ["recordings.squareT_platform_squareT_switch.alarm_events"]
    assert gate.main(["--from-json", str(w), "--baseline", str(b), "--allow",
                      "recordings.squareT_platform_squareT_switch.alarm_events"]) == 0


def test_cli_a_run_without_the_ride_against_a_baseline_with_it(tmp_path, capsys):
    """Exit 1 and the missing data set named; exit 0 with --allow 'ride.*' --allow 'set_F_straight.*'."""
    b = tmp_path / "base.json"
    b.write_text(json.dumps(with_set_f(with_ride(result()))))
    cur = tmp_path / "current.json"
    cur.write_text(json.dumps(result()))
    out = tmp_path / "gate.json"
    assert gate.main(["--from-json", str(cur), "--baseline", str(b), "--out", str(out)]) == 1
    text = capsys.readouterr().out
    assert "MISSING in this run: ride (set E): 3 gated row(s) of the baseline not checked" in text
    assert "MISSING in this run: set F straight:" in text
    assert "--allow 'ride.*' --allow 'set_F_straight.*'" in text
    assert "GATE FAIL: 6 gated metric(s) missing in this run (ride (set E), set F straight)" in text
    assert "missing in this run  << FAIL" in text
    written = json.loads(out.read_text())["gate"]
    assert written["passed"] is False and written["missing_gated"] == RIDE_GATED + SET_F_GATED
    assert written["worse_gated"] == []
    args = ["--from-json", str(cur), "--baseline", str(b)]
    assert gate.main(args + ["--allow", "ride.*", "--allow", "set_F_straight.*"]) == 0
    text = capsys.readouterr().out
    assert "missing in this run, accepted by --allow: ride (set E)" in text
    assert "GATE PASS" in text and "6 missing but allowed" in text
    assert gate.main(args + ["--allow", "ride.*"]) == 1          # set F straight still missing
    assert "GATE FAIL: 3 gated metric(s) missing in this run (set F straight)" in capsys.readouterr().out
