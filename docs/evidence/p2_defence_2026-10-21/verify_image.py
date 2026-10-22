"""Verify capture/runtime source bytes against the selected checkout and seal."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
seal = json.loads((ROOT / "docs/evidence/detector_freeze_2026-10-20_1.2.0_f1a.json").read_text())
paths = set(seal["files"])
paths.update(subprocess.check_output(["git", "ls-files", "ros2_ws/src", "docker/entrypoint.sh", "scripts/reset_replay.py"], cwd=ROOT, text=True).splitlines())
expected = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in sorted(paths)}
program = """
import hashlib,json,sys
from pathlib import Path
import resense,resense._native as n
paths=json.load(sys.stdin)
out={}
for p in paths:
 target=Path('/entrypoint.sh') if p=='docker/entrypoint.sh' else Path('/opt/resense')/p
 out[p]=hashlib.sha256(target.read_bytes()).hexdigest()
print(json.dumps({'files':out,'version':resense.__version__,'native':n.status(),'import':resense.__file__}))
"""
results = {}
for image in ("resense:p2-1.2.0-31154690", "resense:p2-capture-31154690"):
    run = subprocess.run(["docker", "run", "--rm", "-i", "-w", "/", image, "python3", "-c", program],
                         input=json.dumps(expected), text=True, capture_output=True, check=True)
    data = json.loads(run.stdout)
    assert data["version"] == "1.2.0"
    assert data["native"].startswith("native")
    differences = [p for p in expected if expected[p] != data["files"][p]]
    assert not differences, differences
    data["image_id"] = subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Id}}"], text=True).strip()
    results[image] = data
(HERE / "image_receipt.json").write_text(json.dumps({"source": "31154690", "seal_digest": seal["source_sha256"],
    "matched_files": len(expected), "images": results}, indent=2) + "\n")
print(f"PASS: {len(expected)} source files identical in both images; version 1.2.0, native available")
