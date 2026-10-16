"""Exact Linux checkouts, source authentication and focused subprocesses."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

OUT = Path("/review") / (sys.argv[1] if len(sys.argv) > 1 else "run-001")
SOURCES = dict(selected="c9aea87cb5322092070158cd8987115ee44833c9",
               sealed="707ea9cda051369326fb9407c42488c1033dad76")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def run(argv, root, env, name):
    t = time.time()
    r = subprocess.run(argv, cwd=root, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (OUT / (name + ".txt")).write_text(r.stdout)
    commands.append(dict(argv=argv, cwd=str(root), returncode=r.returncode, elapsed_s=time.time() - t,
                         log=name + ".txt"))
    (OUT / "commands.json").write_text(json.dumps(commands, indent=2) + "\n")
    assert r.returncode == 0, (name, r.stdout[-3000:])


def inventory(root, head):
    manifest = json.loads((root / "docs/evidence/detector_freeze_2026-09-29_shell_off.json").read_text())
    paths = set(manifest["files"])
    paths.update(["ros2_ws/src/resense_ros/resense_ros/detector_node.py",
                  "ros2_ws/src/resense_ros/launch/detector.launch.py"])
    if head == SOURCES["selected"]:
        paths.update(["ros2_ws/src/resense_ros/resense_ros/decision_policy.py", "scripts/decision_policy_import.py"])
    files = {}
    for p in sorted(paths):
        b = (root / p).read_bytes()
        assert b"\r\n" not in b, p
        assert b == subprocess.check_output(["git", "show", head + ":" + p], cwd=root), p
        files[p] = sha(b)
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=root).strip()
    assert (root / "configs/default.yaml").read_bytes() == (root / "ros2_ws/src/resense_ros/config/detector.yaml").read_bytes()
    native = {p.name: sha(p.read_bytes()) for p in (root / "resense").glob("*.so")}
    return dict(head=head, files=files, native=native, clean=True)


commands, identities = [], {}
for name, head in SOURCES.items():
    root = Path("/work") / name
    env = {**os.environ, "PYTHONPATH": str(root), "RESENSE_REPO": str(root)}
    if not root.exists():
        run(["git", "-c", "safe.directory=/source.git", "clone", "--shared", "--no-checkout", "-q",
             "/source.git", str(root)], Path("/work"), env, name + "-clone")
        run(["git", "-c", "core.autocrlf=false", "checkout", "--detach", "-q", head], root, env, name + "-checkout")
        run(["bash", "scripts/build_native.sh"], root, env, name + "-build")
    assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip() == head
    identities[name] = dict(before=inventory(root, head))
    if OUT.name != "run-001" and name == "selected":
        run(["python3", "/review/probes.py", name, str(OUT / "runtime.json"), "--runtime-only"], root, env, "runtime")
        previous = json.loads(Path("/review/run-001/selected-probes.json").read_text())
        assert all(k in previous for k in ("tracker", "gt_components", "h2", "axis_health", "reachability"))
        previous.update(json.loads((OUT / "runtime.json").read_text()))
        previous["continued_from"] = "run-001/selected-probes.json"
        (OUT / (name + "-probes.json")).write_text(json.dumps(previous, indent=2) + "\n")
    else:
        run(["python3", "/review/probes.py", name, str(OUT / (name + "-probes.json"))], root, env, name + "-probes")
    if name == "selected":
        run(["python3", "-m", "pytest", "-q", "-rs", "tests/test_node.py", "tests/test_decision_policy.py",
             "tests/test_rescore_decisions.py", "tests/test_health_histogram.py", "tests/test_native.py",
             "tests/test_structure_cut.py", "tests/test_column_shipping.py", "tests/test_wall_drift.py",
             "tests/test_explained_run.py", "--junitxml=" + str(OUT / "pytest.xml")], root, env, "focused-units")
    identities[name]["after"] = inventory(root, head)
    assert identities[name]["before"] == identities[name]["after"]
    (OUT / "identity.json").write_text(json.dumps(identities, indent=2) + "\n")

a, b = [json.loads((OUT / (n + "-probes.json")).read_text()) for n in SOURCES]
assert a["tracker"] == b["tracker"], "unspared tracker behavior differs"
assert a["gt_components"] == b["gt_components"], "ordinary labelled controls differ"
assert a["runtime"]["preserved_defaults"] == 39
(OUT / "paired.json").write_text(json.dumps(dict(
    unspared_tracker_identical=True, tracker_sequences=len(a["tracker"]),
    tracker_frames=sum(len(r["frames"]) for r in a["tracker"]),
    gt_components_identical=True, gt_components=a["gt_components"], completed=True), indent=2) + "\n")
print("Independent selected H4 focused checks complete", flush=True)
