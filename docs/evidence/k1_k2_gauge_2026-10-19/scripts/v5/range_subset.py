#!/usr/bin/env python3
"""The range-probe rows of PROTOCOL §3/§7 that this container's data allows (A = roundT_squareT, D = squareT_platform;
B / C decoded caches are not here): A_person (K2-4), S_person_100 / S_person_150 (K1-1 / K1-2), S_person_60,
K15 (K1-5). Same harness as tools/prebuild_range.py (range_test.py of the evidence folder, per-tag symlinked caches,
the object-free baseline first), ICP from tools/icp_odometry.py into /data/work_k2/rdata/x1/icp.
range_subset.py <tree> <tag> <outdir> [-j N]"""
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
tree, tag, outdir = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
nj = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[4] == "-j" else 1
TOOLS = tree / "docs/evidence/k1_k2_gauge_2026-10-19/tools"
DATA = Path("/data/work_k2/rdata")
A, D = "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"
JOBS = [("A_person", A, "--obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340"),
        ("S_person_60", D, "--obj 0.5,0.5,1.75 --start 360 --d0 60 --end 620"),
        ("S_person_100", D, "--obj 0.5,0.5,1.75 --start 360 --d0 100 --end 620"),
        ("S_person_150", D, "--obj 0.5,0.5,1.75 --start 360 --d0 150 --end 620"),
        ("K15", D, "--obj 0.5,0.5,1.75 --start 450 --d0 100 --end 620 --appear 100")]
out, cache = outdir / tag, outdir / f"cache_{tag}"
out.mkdir(parents=True, exist_ok=False)
cache.mkdir(parents=True, exist_ok=True)
for b in (A, D):
    if not (cache / b).exists():
        (cache / b).symlink_to(DATA / "decoded" / b)
env = dict(os.environ, RESENSE_REPO=str(tree), PYTHONPATH=f"{tree}{os.pathsep}{tree}/ros2_ws/src/resense_ros",
           OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_CORETYPE="Haswell")
for b in (A, D):
    code = (f"import sys; sys.path.insert(0, {str(TOOLS)!r}); import range_test as t; "
            f"t.baseline({str(cache / b)!r}, {str(cache / b) + '_baseline.json'!r})")
    subprocess.run([sys.executable, "-c", code], cwd=tree, env=env, check=True)

def run(job):
    name, bag, args = job
    prefix = out / name
    t0 = time.monotonic()
    with open(f"{prefix}.log", "x") as log:
        r = subprocess.run([sys.executable, str(TOOLS / "range_test.py"), str(cache / bag),
                            str(DATA / "x1/icp" / f"icp_{bag}.json"), str(prefix), *args.split()],
                           cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT)
    res = {"job": name, "recording": bag, "args": args, "exit": r.returncode, "wall_s": round(time.monotonic() - t0, 1)}
    if r.returncode == 0:
        res["summary"] = json.loads(Path(f"{prefix}.json").read_text())["summary"]
    print(name, res["exit"], res.get("summary"), flush=True)
    return res

with ThreadPoolExecutor(nj) as pool:
    results = list(pool.map(run, JOBS))
commit = subprocess.check_output(["git", "-C", str(tree), "rev-parse", "HEAD"], text=True).strip()
dirty = subprocess.check_output(["git", "-C", str(tree), "diff", "--", "configs"], text=True)
json.dump({"tag": tag, "commit": commit, "config_diff": dirty, "jobs": results}, open(outdir / f"summary_{tag}.json", "x"), indent=1)
