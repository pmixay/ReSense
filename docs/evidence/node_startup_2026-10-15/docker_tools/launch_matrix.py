#!/usr/bin/env python3
"""Detach long S1 runs from terminal deadlines, or clean only an interrupted run.

Host stdlib only. Logs/launch receipts are exclusive new sibling files; no old raw
receipt is overwritten. A detached driver still owns normal finally cleanup.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from scripts import startup_acceptance as s1  # noqa: E402


def cleanup(root):
    manifest = s1.read_json(root / "manifest.json")
    run_id = manifest["run_id"]
    raw = s1.command(["docker", "ps", "-aq", "--filter", f"label=resense.startup.run={run_id}"]).stdout
    receipt = {"run_id": run_id, "t": time.time(), "reason": "host terminal deadline",
               "containers": [], "clean": True}
    for cid in raw.split():
        info = s1.strict_json(s1.command(["docker", "inspect", cid]).stdout)[0]
        if info["Config"]["Labels"].get("resense.startup.run") != run_id:
            raise RuntimeError("Refusing to clean a container owned by another run")
        if info["State"]["Running"]:
            s1.command(["docker", "stop", "--time", "12", cid], timeout=20)
        final = s1.strict_json(s1.command(["docker", "inspect", cid]).stdout)[0]
        name = final["Name"].lstrip("/")
        logs = s1.command(["docker", "logs", cid], check=False)
        with (root / (name + ".manual.log")).open("x", encoding="utf-8") as f:
            f.write(logs.stdout + logs.stderr)
        receipt["containers"].append({"id": cid, "name": name, "state": final["State"]})
        s1.command(["docker", "rm", cid])
    receipt["remaining_ids"] = s1.command([
        "docker", "ps", "-aq", "--filter", f"label=resense.startup.run={run_id}"]).stdout.split()
    receipt["clean"] = not receipt["remaining_ids"]
    s1.write_json(root / "manual_cleanup.json", receipt)
    print(json.dumps(receipt, indent=2, allow_nan=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cleanup", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("args", nargs=argparse.REMAINDER)
    a = ap.parse_args()
    if a.cleanup:
        cleanup(a.cleanup.resolve())
        return
    if not a.out or not a.out.parent.is_dir() or a.out.exists():
        ap.error("--out must be a new directory under an existing parent")
    root = a.out.resolve()
    args = a.args[1:] if a.args[:1] == ["--"] else a.args
    cmd = [sys.executable, str(REPO / "scripts/startup_acceptance.py"), "--out", str(root), *args]
    paths = {k: Path(str(root) + suffix) for k, suffix in (
        ("stdout", ".stdout.log"), ("stderr", ".stderr.log"), ("launch", ".launch.json"))}
    if any(p.exists() for p in paths.values()):
        ap.error("Launch/log sibling already exists; choose another output directory")
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    with paths["stdout"].open("x", encoding="utf-8") as out, paths["stderr"].open("x", encoding="utf-8") as err:
        child = subprocess.Popen(cmd, cwd=REPO, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 creationflags=flags, start_new_session=sys.platform != "win32")
    receipt = {"pid": child.pid, "t": time.time(), "argv": cmd,
               "out": str(root), "stdout": str(paths["stdout"]), "stderr": str(paths["stderr"]),
               "driver_sha256": s1.sha256_file(REPO / "scripts/startup_acceptance.py")}
    s1.write_json(paths["launch"], receipt)
    print(json.dumps(receipt, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
