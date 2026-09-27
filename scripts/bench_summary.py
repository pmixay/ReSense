#!/usr/bin/env python3
"""Summarise a bench folder written by ``scripts/bench_8core.sh`` (summary.txt, summary.json).

    python3 scripts/bench_summary.py docs/evidence/bench_2026-09-25            # print the summary
    python3 scripts/bench_summary.py docs/evidence/bench_2026-09-25 --write    # + summary.txt / summary.json

Reads ``facts.txt`` (key=value: machine, commit), ``runs.tsv`` (one row per run: name, kind, kernels
asked for, exit code, wall seconds, bag paths) and per run:

* Docker runs (``dry``: ``scripts/dry_run.sh``, one container with node + player; ``ct``:
  ``scripts/console_test.sh``, the node in its own container): ``<run>/status.jsonl[.gz]`` (the node's
  /resense/status), ``node_log.txt`` (which kernels the node ran), ``docker_stats.tsv`` (every ~2 s:
  epoch, container, CPU %, memory), ``run.txt`` (the PASS / FAIL lines of ``check_dry_run.py``);
* offline runs (``offline_node``: ``scripts/bench_node_path.py``, ``offline_stages``: ``resense
  bench``): ``offline/<run>.txt`` with the tool's output, ``kernels: ...`` and ``peak RSS ... MB``.

Latency is the node's decode + detect per frame (``node.latency_ms``), the detector stage is
``timing_ms.total``; fps is the median of the node's 2 s windows after the first 5 s of recording;
dropped frames are the node's estimate from input stamp gaps (``check_dry_run.py``'s rule: in
total and after the first 5 s); CPU is ``docker stats`` in % of one core (median of the samples
above 10 %, i.e. while frames arrive, and the peak), memory the container's peak. Needs python3 only.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_dry_run import load, percentile  # noqa: E402

SETTLE_S = 5.0
BUSY_CPU = 10.0          # % of one core: a sample above it counts as "frames arriving"
NODE_CONTAINER = {"dry": "resense_bench_dry", "ct": "resense_ct_node"}
MEM_UNITS = {"b": 1 / 2**20, "kib": 1 / 1024, "kb": 1e3 / 2**20, "mib": 1.0, "mb": 1e6 / 2**20,
             "gib": 1024.0, "gb": 1e9 / 2**20}


def read_facts(root):
    facts = {}
    path = os.path.join(root, "facts.txt")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            k, sep, v = line.rstrip("\n").partition("=")
            if sep:
                facts[k.strip()] = v.strip()
    return facts


def read_runs(root):
    path = os.path.join(root, "runs.tsv")
    if not os.path.exists(path):
        raise SystemExit(f"bench_summary: {path} not found (not a scripts/bench_8core.sh folder)")
    lines = [ln.rstrip("\n").split("\t") for ln in open(path, encoding="utf-8") if ln.strip()]
    head, rows = lines[0], lines[1:]
    return [dict(zip(head, r + [""] * (len(head) - len(r)))) for r in rows]


def cloud_count(bag):
    """PointCloud2 messages in a rosbag2 metadata.yaml (no yaml module needed)."""
    path = os.path.join(bag, "metadata.yaml")
    if not bag or not os.path.exists(path):
        return None
    n, want = 0, False
    for line in open(path, encoding="utf-8"):
        if re.search(r"\btype:\s*sensor_msgs/msg/PointCloud2\b", line):
            want = True
        m = re.match(r"\s*message_count:\s*(\d+)", line)
        if m and want:
            n += int(m.group(1))
            want = False
    return n or None


def mem_mib(text):
    m = re.match(r"\s*([\d.]+)\s*([A-Za-z]+)", text.split("/")[0])
    if not m:
        return None
    return float(m.group(1)) * MEM_UNITS.get(m.group(2).lower(), float("nan"))


def docker_stats(path, container):
    """(samples, CPU % median while busy, CPU % peak, memory MiB peak) of one container."""
    if not os.path.exists(path):
        return None
    by_name = {}
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 4:
            continue
        try:
            cpu = float(parts[2].strip().rstrip("%"))
        except ValueError:
            continue
        by_name.setdefault(parts[1].strip(), []).append((cpu, mem_mib(parts[3])))
    if not by_name:
        return None
    name = container if container in by_name else max(by_name, key=lambda k: len(by_name[k]))
    cpu = [c for c, _ in by_name[name]]
    mem = [m for _, m in by_name[name] if m is not None and math.isfinite(m)]
    busy = [c for c in cpu if c > BUSY_CPU]
    return {"container": name, "samples": len(cpu), "busy_samples": len(busy),
            "cpu_busy_median_pct": round(statistics.median(busy), 1) if busy else None,
            "cpu_peak_pct": round(max(cpu), 1), "mem_peak_mib": round(max(mem), 1) if mem else None}


def first_match(path, pattern):
    if not os.path.exists(path):
        return None
    rx = re.compile(pattern)
    for line in open(path, encoding="utf-8", errors="replace"):
        m = rx.search(line)
        if m:
            return m.group(1).strip()
    return None


def checks(path):
    if not os.path.exists(path):
        return []
    return [ln.strip() for ln in open(path, encoding="utf-8", errors="replace")
            if ln.startswith(("PASS:", "FAIL:"))]


def stats_of(values):
    if not values:
        return None
    return {"mean": round(sum(values) / len(values), 1), "p95": round(percentile(values, 95), 1),
            "max": round(max(values), 1)}


def docker_run(root, run):
    d = os.path.join(root, run["name"])
    out = {"name": run["name"], "kind": run["kind"], "kernels_asked": run["kernels"],
           "exit": run["exit"], "wall_s": run["wall_s"], "bags": run["bags"]}
    status = next((os.path.join(d, f) for f in ("status.jsonl.gz", "status.jsonl")
                   if os.path.exists(os.path.join(d, f))), None)
    out["kernels"] = first_match(os.path.join(d, "node_log.txt"), r"per-frame kernels: (.+?)\s*$")
    bags = [b for b in run["bags"].split(",") if b]
    counts = [cloud_count(b) for b in bags]
    out["frames_in_bags"] = sum(counts) if counts and all(c for c in counts) else None
    out["docker_stats"] = docker_stats(os.path.join(d, "docker_stats.tsv"), NODE_CONTAINER.get(run["kind"]))
    out["checks"] = checks(os.path.join(d, "run.txt"))
    if status is None:
        out["frames"] = 0
        return out
    frames, _ = load(status)
    out["frames"] = len(frames)
    lat = [f.get("node", {}).get("latency_ms") for f in frames]
    lat = [v for v in lat if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0]
    det = [f.get("timing_ms", {}).get("total") for f in frames]
    det = [v for v in det if isinstance(v, (int, float))]
    out["latency_ms"] = stats_of(lat)
    out["detector_ms"] = stats_of(det)
    t0 = next((f["stamp"] for f in frames if isinstance(f.get("stamp"), (int, float))), None)
    settled = [f for f in frames if t0 is not None and isinstance(f.get("stamp"), (int, float))
               and f["stamp"] - t0 >= SETTLE_S]
    fps = [f.get("node", {}).get("fps") for f in settled]
    fps = [v for v in fps if isinstance(v, (int, float)) and v > 0]
    out["fps_median"] = round(statistics.median(fps), 2) if fps else None
    last = frames[-1].get("node", {}) if frames else {}
    dropped = last.get("dropped_frames") if isinstance(last.get("dropped_frames"), int) else None
    base = settled[0].get("node", {}).get("dropped_frames") if settled else None
    out["dropped"] = dropped
    out["dropped_after_settle"] = dropped - base if isinstance(dropped, int) and isinstance(base, int) else None
    return out


def cached_frames(src, limit):
    """Frames an offline run saw when its tool does not print them (``resense bench``)."""
    if not src or not os.path.isdir(src):
        return None
    n = len(glob.glob(os.path.join(src, "*.npy")))
    return min(n, int(limit)) if str(limit).isdigit() else n


def offline_run(root, run, limit=None):
    path = os.path.join(root, "offline", run["name"] + ".txt")
    out = {"name": run["name"], "kind": run["kind"], "kernels_asked": run["kernels"],
           "exit": run["exit"], "wall_s": run["wall_s"], "bags": run["bags"]}
    if not os.path.exists(path):
        return out
    text = open(path, encoding="utf-8", errors="replace").read()
    m = re.search(r"^kernels: (.+)$", text, re.M) or re.search(r"^\s+kernels: (.+)$", text, re.M)
    out["kernels"] = m.group(1).strip() if m else None
    m = re.search(r"peak RSS (\d+) MB", text)
    out["peak_rss_mb"] = int(m.group(1)) if m else None
    m = re.search(r"(\d+) frames, (\d+) slots per message", text)
    out["frames"] = int(m.group(1)) if m else cached_frames(run["bags"], limit)
    m = re.search(r"decode \+ detect:\s+mean ([\d.]+) ms, p95 ([\d.]+) ms, max ([\d.]+) ms", text)
    if m:
        out["total_ms"] = {"mean": float(m.group(1)), "p95": float(m.group(2)), "max": float(m.group(3))}
    m = re.search(r"decode \+ crop \+ rotate: mean ([\d.]+) ms, p95 ([\d.]+) ms", text)
    if m:
        out["decode_ms"] = {"mean": float(m.group(1)), "p95": float(m.group(2))}
    stages = {k: {"mean": float(a), "p95": float(b), "max": float(c)} for k, a, b, c in
              re.findall(r"^(\w+)\s+mean\s+([\d.]+) ms\s+p95\s+([\d.]+) ms\s+max\s+([\d.]+) ms", text, re.M)}
    if stages:
        out["stages_ms"] = stages
        if "total" in stages:
            out["total_ms"] = stages["total"]
    return out


def fmt(v, nd=0, dash="-"):
    if v is None:
        return dash
    return f"{v:.{nd}f}" if isinstance(v, float) else str(v)


def summarise(root):
    facts = read_facts(root)
    runs = read_runs(root)
    res = {"folder": os.path.abspath(root), "facts": facts, "build": [], "docker": [], "offline": []}
    for r in runs:
        if r["kind"] == "build":
            res["build"].append(dict(r))
        elif r["kind"] in ("dry", "ct"):
            res["docker"].append(docker_run(root, r))
        elif r["kind"].startswith("offline"):
            res["offline"].append(offline_run(root, r, facts.get("bench_limit")))
    return res


def kernels_short(s):
    if not s:
        return "?"
    return "native" if s.startswith("native") else "numpy"


def text_report(res):
    f = res["facts"]
    L = []
    L.append(f"ReSense bench, {f.get('date', '?')} on {f.get('host', '?')}; commit {f.get('commit', '?')}"
             f"{' (dirty)' if f.get('dirty') == '1' else ''}")
    L.append(f"CPU {f.get('cpu_model', '?')}: {f.get('nproc', '?')} logical CPUs, {f.get('cores', '?')} cores "
             f"x {f.get('threads_per_core', '?')} threads, {f.get('sockets', '?')} socket(s); RAM {f.get('ram_gib', '?')} GiB; "
             f"governor {f.get('governor', '?')}; docker {f.get('docker', '-')}")
    L.append(f"host python {f.get('python', '?')}, numpy {f.get('numpy', '?')}; image kernels: {f.get('image_kernels', '-')}")
    L.append("Stands in for the organizers' i7-9700E (8 cores, no SMT), not available before the upload (organizers, 25.09).")
    for b in res["build"]:
        L.append(f"build ({b['name']}): exit {b['exit']}, {b['wall_s']} s{'; ' + b['note'] if b.get('note') else ''}")
    if res["docker"]:
        L.append("")
        L.append("Docker chain (the node in resense:latest). frames = processed / in the bag(s); fps = median of "
                 "the node's 2 s windows after 5 s; latency = decode + detect per frame, ms mean / p95 / max; det = "
                 "detector stage, ms mean / p95; dropped = total (after the first 5 s); CPU = docker stats, % of one "
                 "core, median while busy / peak; mem = container peak, MiB. dry: node + player + echo in one "
                 "container; ct: the node container alone.")
        hdr = f"{'run':<24} {'kernels':<7} {'frames':>9} {'fps':>5} {'latency':>15} {'det':>11} {'dropped':>9} " \
              f"{'CPU %':>11} {'mem':>6}  check"
        L.append(hdr)
        for d in res["docker"]:
            lat, det, st = d.get("latency_ms"), d.get("detector_ms"), d.get("docker_stats") or {}
            frames = f"{d.get('frames', 0)}/{fmt(d.get('frames_in_bags'))}"
            lat_s = f"{fmt(lat['mean'])}/{fmt(lat['p95'])}/{fmt(lat['max'])}" if lat else "-"
            det_s = f"{fmt(det['mean'])}/{fmt(det['p95'])}" if det else "-"
            drop_s = f"{fmt(d.get('dropped'))} ({fmt(d.get('dropped_after_settle'))})"
            cpu_s = f"{fmt(st.get('cpu_busy_median_pct'))}/{fmt(st.get('cpu_peak_pct'))}" if st else "-"
            ok = "PASS" if d.get("exit") == "0" else f"FAIL (exit {d.get('exit')})"
            L.append(f"{d['name']:<24} {kernels_short(d.get('kernels')):<7} {frames:>9} {fmt(d.get('fps_median'), 1):>5} "
                     f"{lat_s:>15} {det_s:>11} {drop_s:>9} {cpu_s:>11} {fmt(st.get('mem_peak_mib')):>6}  {ok}")
            for c in d.get("checks", []):
                if c.startswith("FAIL:"):
                    L.append(f"{'':<26}{c}")
            if d.get("kernels_asked") not in ("", "-", None) and d.get("kernels") \
                    and kernels_short(d["kernels"]) != d["kernels_asked"]:
                L.append(f"{'':<26}WARNING: asked for {d['kernels_asked']}, the node ran {d['kernels']}")
    if res["offline"]:
        L.append("")
        L.append("Offline, host python, single-threaded BLAS (ms per frame; node path = decode + crop + rotate + "
                 "detect as detector_node.on_cloud, bench_node_path.py; stages = resense bench):")
        L.append(f"{'run':<34} {'kernels':<7} {'frames':>6} {'mean':>6} {'p95':>6} {'max':>6} {'RSS MB':>7}")
        for o in res["offline"]:
            t = o.get("total_ms") or {}
            L.append(f"{o['name']:<34} {kernels_short(o.get('kernels')):<7} {fmt(o.get('frames')):>6} "
                     f"{fmt(t.get('mean'), 1):>6} {fmt(t.get('p95'), 1):>6} {fmt(t.get('max'), 1):>6} "
                     f"{fmt(o.get('peak_rss_mb')):>7}" + ("" if o.get("exit") == "0" else f"  FAIL (exit {o.get('exit')})"))
            if o.get("kernels_asked") and o.get("kernels") and kernels_short(o["kernels"]) != o["kernels_asked"]:
                L.append(f"{'':<36}WARNING: asked for {o['kernels_asked']}, ran {o['kernels']}")
        pairs = {}
        for o in res["offline"]:
            key = o["name"].rsplit("_", 1)[0]
            if o.get("total_ms"):
                pairs.setdefault(key, {})[kernels_short(o.get("kernels"))] = o["total_ms"]["mean"]
        ratios = [f"{k} {v['numpy'] / v['native']:.2f}x" for k, v in pairs.items()
                  if "native" in v and "numpy" in v and v["native"] > 0]
        if ratios:
            L.append("numpy / native mean time: " + ", ".join(ratios))
    failed = [d["name"] for d in res["docker"] + res["offline"] + res["build"] if d.get("exit") != "0"]
    L.append("")
    L.append("all runs passed" if not failed else "failed or not passed: " + ", ".join(failed))
    return "\n".join(L) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("folder")
    ap.add_argument("--write", action="store_true", help="also write <folder>/summary.txt and summary.json")
    a = ap.parse_args(argv)
    res = summarise(a.folder)
    text = text_report(res)
    sys.stdout.write(text)
    if a.write:
        with open(os.path.join(a.folder, "summary.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
        with open(os.path.join(a.folder, "summary.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=1)
            fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
