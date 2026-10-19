#!/usr/bin/env python3
"""J1 pre-build: the judge's range jobs (run_range_matrix.sh + run_range_extra.sh, 13.10) on a checkout.

    prebuild_range.py --repo <checkout> --tag <name> --data <root with decoded/ and x1/icp/> --out <dir> [-j 3]

The job list below is transcribed from the two shell scripts (the scripts hard-code the judge's machine
paths, so they cannot run here unchanged); `--list` prints it for comparison. Each job runs the unchanged
`scripts/range_test.py` of this folder with RESENSE_REPO / PYTHONPATH pinned to the checkout and
OPENBLAS_CORETYPE=Haswell (P4 protocol amendment 1). range_test caches the object-free track model next
to the cache path, so each tag reads the caches through its own symlink folder. Writes <out>/<tag>/<job>.json
and summary_<tag>.json (every job's summary, exit code, wall time, output SHA-256). Existing outputs are
never overwritten.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE                 # K1/K2 19.10: this folder (range_test.py with the curvature-step placement)
A, B, C, D = ("roundT_squareT_pressureGate_squareT", "roundT_doubleT", "roundT_pressureGate_roundT",
              "squareT_platform_squareT_switch")
OBJ = {"person": "0.5,0.5,1.75", "cube1": "1.0,1.0,1.0", "cube05": "0.5,0.5,0.5", "cube03": "0.3,0.3,0.3"}


def jobs():
    j = []
    for o in ("person", "cube1", "cube05", "cube03"):        # run_range_matrix.sh lines 9-14
        j += [(f"A_{o}", A, f"--obj {OBJ[o]} --start 150 --d0 230 --end 340"),
              (f"B_{o}", B, f"--obj {OBJ[o]} --start 50 --d0 230"),
              (f"C_{o}", C, f"--obj {OBJ[o]} --start 0 --d0 230"),
              (f"D_{o}", D, f"--obj {OBJ[o]} --start 100 --d0 230 --end 420")]
    a = "--start 150 --d0 230 --end 340"                       # lines 15-20
    j += [("A_person_latp05", A, f"--obj 0.5,0.5,1.75 {a} --lat 0.5"),
          ("A_person_latm05", A, f"--obj 0.5,0.5,1.75 {a} --lat -0.5"),
          ("A_person_drop", A, f"--obj 0.5,0.5,1.75 {a} --dropout"),
          ("A_cube05_drop", A, f"--obj 0.5,0.5,0.5 {a} --dropout"),
          ("A_cube1_drop", A, f"--obj 1.0,1.0,1.0 {a} --dropout"),
          ("A_lowbox_rail", A, f"--obj 0.3,0.3,0.15 {a}")]
    for d in (60, 100, 150):                                   # lines 22-25
        j += [(f"S_person_{d}", D, f"--obj 0.5,0.5,1.75 --start 360 --d0 {d} --end 620"),
              (f"S_cube05_{d}", D, f"--obj 0.5,0.5,0.5 --start 360 --d0 {d} --end 620")]
    j += [("E1_cross150", A, "--obj 0.5,0.5,1.75 --start 150 --d0 150 --end 340 --lat -4 --vy 1.0"),   # extra
          ("E2_cross80", A, "--obj 0.5,0.5,1.75 --start 220 --d0 80 --end 340 --lat -3 --vy 1.0"),
          ("E3_recede8", A, "--obj 0.6,0.6,1.0 --start 230 --d0 100 --end 340 --vx 8"),
          ("E3_recede5", A, "--obj 0.6,0.6,1.0 --start 230 --d0 100 --end 340 --vx 5"),
          ("E4_appear60", A, "--obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --appear 60"),
          ("E4_appear100", A, "--obj 0.5,0.5,1.75 --start 150 --d0 230 --end 340 --appear 100"),
          ("E5_pole_side", A, "--obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340 --lat 0.7"),
          ("E5_pole_c", A, "--obj 0.3,0.3,2.8 --start 150 --d0 230 --end 340"),
          ("E6_cable_low_c", A, "--obj 0.05,0.05,2.6 --start 150 --d0 230 --end 340 --base 0.2")]
    return j


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path)
    ap.add_argument("--tag")
    ap.add_argument("--data", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("-j", "--jobs", type=int, default=3)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        for name, bag, args in jobs():
            print(f"{name:16s} {bag:38s} {args}")
        return 0
    repo = a.repo.resolve()
    out = a.out / a.tag
    cache = a.out / f"cache_{a.tag}"
    out.mkdir(parents=True, exist_ok=False)
    cache.mkdir(parents=True, exist_ok=True)
    for b in (A, B, C, D):
        if not (cache / b).exists():
            (cache / b).symlink_to(a.data / "decoded" / b)
    env = dict(os.environ, RESENSE_REPO=str(repo), PYTHONPATH=f"{repo}{os.pathsep}{repo}/ros2_ws/src/resense_ros",
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_CORETYPE="Haswell")
    # the object-free track model of each recording, once, before parallel jobs (no race on the cache file)
    for b in (A, B, C, D):
        code = (f"import sys; sys.path.insert(0, {str(SCRIPTS)!r}); import range_test as t; "
                f"t.baseline({str(cache / b)!r}, {str(cache / b) + '_baseline.json'!r})")
        subprocess.run([sys.executable, "-c", code], cwd=repo, env=env, check=True)

    def run(job):
        name, bag, args = job
        prefix = out / name
        t0 = time.monotonic()
        with open(f"{prefix}.log", "x") as log:
            r = subprocess.run([sys.executable, str(SCRIPTS / "range_test.py"), str(cache / bag),
                                str(a.data / "x1/icp" / f"icp_{bag}.json"), str(prefix), *args.split()],
                               cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
        res = {"job": name, "recording": bag, "args": args, "exit": r.returncode,
               "wall_s": round(time.monotonic() - t0, 1)}
        if r.returncode == 0:
            res.update(summary=json.loads(Path(f"{prefix}.json").read_text())["summary"],
                       output_sha256=sha(f"{prefix}.json"))
        print(name, res["exit"], res.get("summary", {}).get("first_stop_X"), flush=True)
        return res

    t0 = time.monotonic()
    with ThreadPoolExecutor(a.jobs) as pool:
        results = list(pool.map(run, jobs()))
    commit = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    report = {"tag": a.tag, "commit": commit, "runtime": "linux-cloud-4vcpu (OPENBLAS_CORETYPE=Haswell)",
              "range_test_sha256": sha(SCRIPTS / "range_test.py"), "harness_sha256": sha(__file__),
              "icp": {b: sha(a.data / "x1/icp" / f"icp_{b}.json") for b in (A, B, C, D)},
              "wall_s": round(time.monotonic() - t0, 1), "jobs": results}
    with open(a.out / f"summary_{a.tag}.json", "x") as f:
        json.dump(report, f, indent=1)
    failed = [r["job"] for r in results if r["exit"]]
    print("failed:", failed)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
