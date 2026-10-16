#!/usr/bin/env python3
"""Host launcher. Unique labelled Docker resources; pinned tools image, 2 jobs, threads=1."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import uuid

IMAGE = "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19"
DEFAULT_GIT = r"C:\Users\alikh\OneDrive\Desktop\projects\ReSense\.git"
DEFAULT_CACHE = r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-p3-data\cache"


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--baseline-control", action="store_true")
    ap.add_argument("--source-git", default=DEFAULT_GIT)
    ap.add_argument("--cache", default=DEFAULT_CACHE)
    a = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    assert Path(a.source_git).is_dir() and Path(a.cache).is_dir() and root.is_dir()
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = ("baseline" if a.baseline_control else "candidate") + "-" + a.commit[:12] + "-" + stamp + "-" + uuid.uuid4().hex[:8]
    name = "rs-gate-" + run_id.lower()
    volume = name + "-checkout"
    label = "resense.integration.owner=gate-frame-infra-20261016"
    subprocess.run(["docker", "volume", "create", "--label", label, volume], check=True)
    cmd = ["docker", "run", "--detach", "--name", name, "--label", label, "--network", "none",
           "--cpus", "2", "--memory", "4608m", "--memory-swap", "6656m",
           "--mount", f"type=bind,source={a.source_git},target=/source.git,readonly",
           "--mount", f"type=bind,source={a.cache},target=/data/cache,readonly",
           "--mount", f"type=bind,source={root},target=/evidence",
           "--mount", f"type=bind,source={root / 'helpers'},target=/helpers,readonly",
           "--mount", f"type=volume,source={volume},target=/evalworkspace",
           "--workdir", "/evalworkspace", "--entrypoint", "python3", IMAGE,
           "/helpers/run_linux_gate.py", "--commit", a.commit, "--run-id", run_id]
    if a.baseline_control:
        cmd.append("--baseline-control")
    cid = subprocess.check_output(cmd, text=True).strip()
    record = dict(run_id=run_id, container=name, container_id=cid, volume=volume, image=IMAGE,
                  argv=cmd, source_git=a.source_git, cache=a.cache)
    (root / (run_id + ".launch.json")).write_text(json.dumps(record, indent=2) + "\n")
    for suffix, args in ((".inspect.json", ["inspect", name]), (".docker-version.txt", ["version"]),
                         (".docker-info.json", ["info", "--format", "{{json .}}"]),
                         (".image.json", ["image", "inspect", IMAGE])):
        p = subprocess.run(["docker", *args], capture_output=True)
        (root / (run_id + suffix)).write_bytes(p.stdout + p.stderr)
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
