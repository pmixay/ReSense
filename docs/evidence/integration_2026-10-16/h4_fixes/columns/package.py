"""Retain author measurements and rejected source without promoting a runtime default."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parent
S = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-h4-columns-author-20261016")
REFERENCE = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016\run-001\replay-sealed-all")


def sha(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write(name, data):
    path = P / name
    assert not path.exists(), path
    path.write_text(json.dumps(data, indent=2) + "\n")


def retain(source, name):
    target = P / name
    assert not target.exists(), target
    shutil.copyfile(source, target)


def read_rows(path):
    with path.open() as f:
        return {r["frame_id"]: r for r in map(json.loads, f)}


candidate = S / "attempt-08-dark"
retain(candidate / "source.patch", "rejected_attempt_08.patch")
retain(candidate / "results/identity.json", "rejected_attempt_08_identity.json")
for name in ["parent-witness-02", "attempt-07-tests", "attempt-08-tests", "parent-final-witness"]:
    retain(S / name / "worker.txt", name + ".txt")
    xml = ET.parse(S / name / "results/pytest.xml")
    groups = defaultdict(lambda: dict(passed=0, failed=0, skipped=0, errors=0))
    failures = []
    for c in xml.iter("testcase"):
        group = groups[c.attrib["classname"]]
        failure = c.find("failure")
        key = "failed" if failure is not None else "skipped" if c.find("skipped") is not None else \
            "errors" if c.find("error") is not None else "passed"
        group[key] += 1
        if failure is not None:
            failures.append(dict(test=c.attrib, message=failure.attrib, text=failure.text))
    write(name + "-summary.json", dict(groups=dict(groups), failures=failures))

normal = {}
for name in ["roundT_doubleT", "squareT_platform_squareT_switch", "ride_1", "ride_3"]:
    ref = read_rows(REFERENCE / (name + ".jsonl"))
    got = read_rows(S / "attempt-08-normal/results" / (name + ".jsonl"))
    assert ref.keys() == got.keys()
    diffs, lost, added, output_diffs = [], [], [], []
    for k in ref:
        assert ref[k]["input"] == got[k]["input"] and ref[k]["mask"] == got[k]["mask"]
        assert ref[k]["stamp"] == got[k]["stamp"] and ref[k]["cache_sha256"] == got[k]["cache_sha256"]
        rr, gg = ref[k]["serialized"], got[k]["serialized"]
        if rr != gg:
            diffs.append(k)
        rc = {tuple(d["center"]) for d in rr["detections"]}
        gc = {tuple(d["center"]) for d in gg["detections"]}
        lost.extend([dict(frame=k, center=c) for c in sorted(rc - gc)])
        added.extend([dict(frame=k, center=c) for c in sorted(gc - rc)])
        if rr["detections"] != gg["detections"] or rr["warnings"] != gg["warnings"]:
            output_diffs.append(k)
    normal[name] = dict(frames=len(ref), sealed_stop=sum(r["serialized"]["obstacle"] for r in ref.values()),
                        candidate_stop=sum(r["serialized"]["obstacle"] for r in got.values()),
                        non_timing_differences=diffs, descriptor_differences=output_diffs,
                        lost_exact_detection_centers=lost, new_exact_detection_centers=added)
write("normal_comparison.json", normal)

probes = {}
for name in ["pole_c", "C_person"]:
    parent = json.loads((S / "parent-critical/results" / (name + ".json")).read_text())
    comparisons = {}
    for attempt in ["attempt-06-probes", "attempt-07-probes", "attempt-08-probes"]:
        data = json.loads((S / attempt / "results" / (name + ".json")).read_text())
        assert len(parent["rows"]) == len(data["rows"])
        lost, added = [], []
        for r, c in zip(parent["rows"], data["rows"], strict=True):
            for key in ["k", "X", "n_obj", "Y", "Zb", "axis_valid"]:
                assert r.get(key) == c.get(key), (name, key, r["k"])
            if r["hit"] and not c["hit"]:
                lost.append(dict(parent=r, candidate=c))
            if c["hit"] and not r["hit"]:
                added.append(dict(parent=r, candidate=c))
        comparisons[attempt] = dict(summary=data["summary"], lost_matched_stop_frames=lost,
                                    new_matched_stop_frames=added)
    probes[name] = dict(parent=parent["summary"], comparisons=comparisons)
write("probe_comparison.json", probes)

inventory, states = [], {}
for run in sorted(S.iterdir()):
    if not run.is_dir():
        continue
    for path in sorted(run.rglob("*")):
        if path.is_file():
            inventory.append(dict(path=str(path.relative_to(S)), bytes=path.stat().st_size, sha256=sha(path)))
    launch = run / "launch.json"
    if launch.exists():
        argv = json.loads(launch.read_text())["argv"]
        name = argv[argv.index("--name") + 1]
        raw = subprocess.check_output(["docker", "inspect", name, "--format", "{{json .State}}"], text=True)
        states[run.name] = json.loads(raw)
write("EXTERNAL_ARTIFACTS.json", dict(root=str(S), files=inventory))
write("runtime.json", states)
print(json.dumps(dict(normal=normal, probes={k: dict(parent=v["parent"], candidate=v["comparisons"]
      ["attempt-08-probes"]["summary"]) for k, v in probes.items()}), indent=2))
