"""Independent read-only recount of completed development evidence; no detector execution."""
from array import array
from collections import Counter
import copy
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
TEMP = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode")
RUNS = TEMP / "resense-integration-20261016-runs"
BASE = RUNS / "baseline-707ea9cda051-20261016T060147Z-68fb3429"
CAND = RUNS / "candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1"
WITHDRAWAL = TEMP / "resense-h4-column-withdrawal-20261016"
HEAD = "c9aea87cb5322092070158cd8987115ee44833c9"
SEAL = "707ea9cda051369326fb9407c42488c1033dad76"
FILES = {}


def record(path):
    b = path.read_bytes()
    FILES[str(path)] = dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
    return b


def load(path):
    return json.loads(record(path))


def rows(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in f:
            h.update(b)
            yield json.loads(b)
    FILES[str(path)] = dict(bytes=path.stat().st_size, sha256=h.hexdigest())


def normalized(r):
    r = copy.deepcopy(r)
    r.pop("timing_ms", None)
    h = r.get("health", {})
    for k in ("latency_p95_ms", "latency_basis", "latency_sample_age_frames"):
        h.pop(k, None)
    before = h.get("messages", [])
    h["messages"] = [s for s in before if not re.fullmatch(r"latency p95 \d+ ms over the \d+ ms budget", s)]
    if before != h["messages"] and h.get("level") == "warn" and h.get("decision_level") == "ok":
        assert not h["messages"]
        h["level"] = "ok"
    return r


def range_pair(a, b, drift):
    a, b = normalized(a), normalized(b)
    for section, key in (("health", "monitored_range"), ("health", "clear_distance"), (None, "clear_distance")):
        left, right = (a[section], b[section]) if section else (a, b)
        assert right[key] == round(max(0., min(left[key], drift)), 1), (key, left[key], right[key], drift)
        right[key] = left[key]
    for section in ("track", "health"):
        b[section].pop("wall_drift", None)
    assert a == b


def authenticate(identity):
    assert identity["head"] in (HEAD, SEAL)
    for p, digest in identity["files"].items():
        blob = subprocess.check_output(["git", "show", identity["head"] + ":" + p], cwd=REPO)
        assert hashlib.sha256(blob).hexdigest() == digest, p


def withdrawal():
    selected = WITHDRAWAL / "probes-c9aea87-20261016a"
    sealed = WITHDRAWAL / "probes-sealed-707ea9c-20261016a"
    dark = WITHDRAWAL / "dark-c9aea87-20261016a"
    for folder, head in ((selected, HEAD), (sealed, SEAL), (dark, HEAD)):
        assert load(folder / "completion.json")["ok"]
        ident = load(folder / "results/identity.json")
        assert ident["head"] == head and ident["clean_git"]
        authenticate(ident)
        assert all(v == "b5a5c2dc08be8fa1ab00e27dee7662d31413a99f819a760d2d2d4b16b93e8534" for v in ident["native"].values())
        if head == HEAD:
            assert ident["config"]["cluster"]["column_free_max_top"] == 0.
    probe_results = {}
    for name, count in (("pole_c", 82), ("C_person", 55)):
        a = load(sealed / ("results/" + name + ".json"))
        b = load(selected / ("results/" + name + ".json"))
        assert len(a["rows"]) == len(b["rows"])
        placement = ("k", "X", "n_obj", "lat", "Y", "Zb", "axis_valid")
        for x, y in zip(a["rows"], b["rows"]):
            assert {k:x.get(k) for k in placement} == {k:y.get(k) for k in placement}
        hit = lambda data: [r["k"] for r in data["rows"] if r["hit"] and r["n_obj"] > 0]
        old, new = hit(a), hit(b)
        assert len(new) == count and not set(old) - set(new)
        if name == "pole_c":
            assert old == new and b["summary"]["visible_frames"] == 177
        else:
            assert new == list(range(98, 153)) and old == list(range(104, 153))
            assert b["summary"]["first_stop_X"] == 82.77
        probe_results[name] = dict(rows=len(b["rows"]), placement_identical=True,
            sealed_hits=old, selected_hits=new, added=sorted(set(new)-set(old)), lost=[], summary=b["summary"])
    dark_result = {}
    for piece, count in ((1, 14), (3, 2)):
        a = rows(BASE / f"frames/new_data_{piece}.jsonl")
        b = rows(dark / f"results/ride_{piece}.jsonl")
        stop, n, candidates, center_pairs = [], 0, 0, 0
        for old, new in itertools.zip_longest(a, b):
            assert old is not None and new is not None
            assert old["key"]["frame_id"] == new["frame_id"]
            assert not new["observer"] and not new["spares"]
            assert not any(any(t.get("spare_hist", [])) for t in new["tracks"])
            assert len(old["raw"]["candidates"]) == len(new["candidates"])
            for x, y in zip(old["raw"]["candidates"], new["candidates"]):
                y = copy.deepcopy(y)
                assert not y.pop("spared") and not y.pop("cut")
                points = y.pop("points_idx")
                x = copy.deepcopy(x)
                idx = x.pop("points_idx")
                assert points["shape"] == [len(idx)] and points["dtype"] == "int64"
                assert points["sha256"] == hashlib.sha256(array("q", idx).tobytes()).hexdigest()
                assert x == y
                candidates += 1
            old, cur = old["serialized"], new["serialized"]
            assert old["obstacle"] == cur["obstacle"]
            for key in ("detections", "warnings"):
                # Exact full descriptor equality is stronger than matching rounded centers.
                assert old[key] == cur[key]
                center_pairs += len(cur[key])
            drift = cur.get("track", {}).get("wall_drift", 1e9)
            range_pair(old, cur, drift)
            if cur["obstacle"]: stop.append(new["frame_id"])
            n += 1
        assert n == 1409 and len(stop) == count
        dark_result[str(piece)] = dict(frames=n, stop_frames=stop, candidates=candidates,
            exact_detection_warning_descriptors=center_pairs, extra=[], lost=[], observer_calls=0,
            nonrange_result_and_all_common_candidate_fields_identical=True)
    guard = load(dark / "results/shipping_guard.json")
    assert all(guard[k] == 0 for k in ("free_top_calls", "spared_candidates", "provisional_tracks", "spare_history_tracks", "observer_calls"))
    original = subprocess.check_output(["git", "show", "4c6ea25:tests/test_h4_column_evidence.py"], cwd=REPO)
    archived = record(HERE.parent / "h4_fixes/columns/withdrawn_acceptance.py.txt")
    assert original == archived
    return dict(probes=probe_results, dark=dark_result, guard=guard,
                failed_acceptance_preserved_sha256=hashlib.sha256(original).hexdigest())


def h3():
    done = load(CAND / "completion.json")
    assert done["commit"] == HEAD and done["gate_exit"] == 0 and done["passed"] and done["clean_source"]
    for root, head in ((BASE, SEAL), (CAND, HEAD)):
        before, after = load(root / "source_before.json"), load(root / "source_after.json")
        assert all(before[k] == after[k] for k in ("files", "head", "git_status", "source_sha256"))
        assert before["head"] == head and before["inventory_matches_commit"]
        assert not before["git_status"] and not before["crlf_files"] and not before["files_differing_from_commit"]
        authenticate(before)
        authenticate(after)
        g = load(root / "gate.json")
        assert g["code"]["commit"] == head and not g["code"]["uncommitted_detector_changes"]
        assert not g["gate"]["allow"] and not g["config"]["set"]
        assert not load(root / "gate_work/config.yaml.json")["resense"]["health"]["latency_affects_decision"]
    assert load(BASE / "cache_identity.json") == load(CAND / "cache_identity.json")
    pa, pb = load(BASE / "provenance.json"), load(CAND / "provenance.json")
    for key in ("python", "packages", "platform", "native_sha256", "baseline_sha256"):
        assert pa[key] == pb[key]
    ra = {r["metric"]:r for r in load(BASE / "gate_comparison_rows.json")}
    rb = {r["metric"]:r for r in load(CAND / "gate_comparison_rows.json")}
    assert ra.keys() == rb.keys() and len(rb) == 224
    nonlat = [k for k in rb if not k.startswith("latency_ms.")]
    assert len(nonlat) == 208
    assert all(ra[k]["current"] == rb[k]["current"] == rb[k]["baseline"] for k in nonlat)
    assert sum(r["gated"] for r in rb.values()) == 146 and not any(r["fails"] or r["allowed"] for r in rb.values())
    a = {p.name:p for p in (BASE / "frames").glob("*.jsonl")}
    b = {p.name:p for p in (CAND / "frames").glob("*.jsonl")}
    assert a.keys() == b.keys()
    counts, per = Counter(), {}
    for name in sorted(a):
        n = 0
        for left, right in itertools.zip_longest(rows(a[name]), rows(b[name])):
            assert left is not None and right is not None and left["key"] == right["key"]
            raw = right["raw"]
            drift = raw["track"]["wall_drift"]
            counts["finite_drift_frames"] += drift < 1e9
            counts["monitored_reductions"] += raw["health"]["monitored_range"] < left["raw"]["health"]["monitored_range"]
            counts["clear_reductions"] += raw["clear_distance"] < left["raw"]["clear_distance"]
            for representation in ("raw", "serialized"):
                x, y = copy.deepcopy(left[representation]), copy.deepcopy(right[representation])
                if representation == "raw":
                    for c in y["candidates"]:
                        assert not c.pop("spared") and not c.pop("cut")
                        counts["candidates"] += 1
                range_pair(x, y, drift)
                counts["cap_equations"] += 3
            counts["frames"] += 1; n += 1
        per[name] = n
    assert counts["frames"] == 18329 and counts["candidates"] == 25706
    sf_a, sf_b = [load(r / "gate_work/setF_straight.json")["sequences"] for r in (BASE, CAND)]
    sf_rows, sf_changed = 0, 0
    for a, b in zip(sf_a, sf_b):
        assert len(a["rows"]) == len(b["rows"])
        for x, y in zip(a["rows"], b["rows"]):
            y = copy.deepcopy(y)
            sf_changed += x["mon"] != y["mon"]
            assert y["mon"] <= x["mon"]
            y["mon"] = x["mon"]
            assert x == y
            sf_rows += 1
    assert sf_rows == 3060
    return dict(completion=done, counts=dict(counts), frame_sequences=per, metric_rows=224,
        identical_nonlatency_rows=208, gated_rows=146, raw_and_serialized_other_fields_identical=True,
        setF_rows=sf_rows, setF_only_mon_changed=sf_changed, source_and_runtime_authenticated=True)


stage = sys.argv[1]
result = withdrawal() if stage == "withdrawal" else h3()
result["external_files"] = FILES
dest = HERE / (stage + "_audit.json")
assert not dest.exists(), "retain prior audit results"
dest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"stage": stage, "passed": True, "authenticated_external_files": len(FILES), "out": str(dest)}))
