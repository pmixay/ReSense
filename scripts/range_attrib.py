#!/usr/bin/env python3
"""X1 range attribution: which rule or tracker hold costs each visible non-STOP frame.

Observation-only wrapper of the 13.10 judge tools (BACKLOG X1). The judge script runs unmodified;
this harness replaces three module attributes with wrappers that call the originals with the same
arguments and return their results unchanged:

* ``range_test.run_frame`` / ``probe.run_frame``: after the detector's frame, snapshot the final
  candidates, the thin / weak clusters and every tracker track (read-only attribute reads and the
  pure ``Tracker._qualifies``);
* ``resense.clustering._corridor_cluster`` / ``_low_cluster``: while the original runs,
  ``sys.setprofile`` records which ``return`` statement of ``_corridor_cluster``, ``_low_cluster``,
  ``_split_part`` and ``_is_infrastructure`` fired and the locals needed to name it. The rule is
  named from the source condition of that line, so the same harness reads 707ea9c and 1.1.0.

    range_attrib.py run --repo <checkout> --out <prefix> range <range_test args...>
    range_attrib.py run --repo <checkout> --out <prefix> --labels <labels.json>
        --window name:first:last [...] probe <probe args...>
    range_attrib.py table --out <table.json> <prefix> [...]

``run`` writes the judge tool's own output (``<prefix>.json`` / ``.jsonl``) and
``<prefix>.attrib.json``. Proof of no influence: compare the judge output with a hooks-off run
(``table`` refuses an attribution without ``hooks_off`` equality recorded by ``verify``):

    range_attrib.py verify <prefix> <hooks-off judge output>

Every visible non-STOP row gets exactly one cause (precedence in ``cause``); a row the precedence
cannot name is ``unclassified:*`` and makes ``table`` exit 1.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import linecache
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
JUDGE = ROOT / "docs/evidence/judgement_2026-10-13/scripts"
SCHEMA = "resense-range-attribution-v1"
BINS = [(3, 30), (30, 60), (60, 100), (100, 150), (150, 200), (200, 260)]
INFRA = [("thin_min_length", "infra_linear_thin"), ("hardware_max_top", "infra_hardware"),
         ("wall_min_lateral", "infra_wall_side"), ("wall_segment_min_length", "infra_wall_segment"),
         ("linear_min_aspect", "infra_linear_side")]
TRACK_FIELDS = ("id", "hits", "misses", "age", "confidence", "reported", "column_held", "approach_block",
                "far_evidence", "clean_run", "doubt", "withheld", "fresh_blocked", "near_escalated", "span_s",
                "stop_earned", "was_stop", "kept", "hold")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def r2(v):
    return round(float(v), 2)


# ---------------------------------------------------------------------------------------- hooks
class Recorder:
    def __init__(self, C):
        self.C = C
        self.orig_cc, self.orig_low = C._corridor_cluster, C._low_cluster
        names = ("_corridor_cluster", "_low_cluster", "_split_part", "_gauge_part", "_is_infrastructure")
        self.codes = {getattr(C, n).__code__: n for n in names if hasattr(C, n)}  # _split_part: 1.1.0 only
        self.frames = {}          # id(rep) -> {k: record}
        self.blobs = []           # this frame's blob records
        self.alive = []           # keeps this frame's clusters alive: ids stay unique

    def _condition(self, code, line):
        """Source text of the ``if`` that guards the return on ``line`` (or the return itself)."""
        fn = code.co_filename
        text = linecache.getline(fn, line).strip()
        if not text.startswith("return") or text not in ("return None", "return True"):
            return text
        for n in range(line - 1, code.co_firstlineno, -1):
            t = linecache.getline(fn, n).strip()
            if t.startswith("if ") or t.startswith("elif "):
                # a multi-line condition: join the continuation lines
                parts, m = [t], n + 1
                while not parts[-1].endswith(":") and m < line:
                    parts.append(linecache.getline(fn, m).strip())
                    m += 1
                return " ".join(parts)
        return text

    def _traced(self, orig, args, kwargs):
        events = []

        def prof(frame, event, arg):
            if event == "return" and frame.f_code in self.codes:
                loc = frame.f_locals
                keep = {k: loc[k] for k in ("thin", "keep_thin", "size", "min_pts", "weak_height") if k in loc}
                events.append((self.codes[frame.f_code], frame.f_code, frame.f_lineno, arg, keep))
            return prof

        old = sys.getprofile()
        sys.setprofile(prof)
        try:
            out = orig(*args, **kwargs)
        finally:
            sys.setprofile(old)
        return out, events

    def label(self, events, top):
        """The first failing check of a dropped blob, from the return events of its call."""
        last = next(e for e in reversed(events) if e[0] == top)
        _, code, line, _, loc = last
        cond = self._condition(code, line)
        if top == "_low_cluster":
            size = loc.get("size")
            if "min_width" in cond:
                return "low_narrow", cond
            if "weak_height" in cond:
                return "low_below_railhead", cond
            if size is not None and "max_length" in cond:
                return "low_shape", cond
            return f"unmapped:{top}:{line}", cond
        if "part is None" in cond:
            return "oversize_split_refused", cond
        if "cfg.max_extent or" in cond:
            return ("thin" if loc.get("thin") and not loc.get("keep_thin") else "oversize"), cond
        if "ordinary or cross_ring" in cond:
            return "min_points", cond
        if "_is_infrastructure(" in cond:
            inf = [e for e in events if e[0] == "_is_infrastructure" and e[3]]
            if inf:
                icond = self._condition(inf[-1][1], inf[-1][2])
                for key, name in INFRA:
                    if key in icond:
                        return name, icond
            return "unmapped:infrastructure", cond
        return f"unmapped:{top}:{line}", cond

    def corridor(self, b, dy, *rest, **kw):
        out, events = self._traced(self.orig_cc, (b, dy) + rest, kw)
        self._blob("_corridor_cluster", b, out, events)
        return out

    def low(self, b, dy, *rest, **kw):
        out, events = self._traced(self.orig_low, (b, dy) + rest, kw)
        self._blob("_low_cluster", b, out, events)
        return out

    def _blob(self, fn, b, out, events):
        pts = b.pts
        rec = {"fn": fn, "x0": r2(pts[:, 0].min()), "x1": r2(pts[:, 0].max()), "y": r2(pts[:, 1].mean()),
               "n_vox": int(b.n_vox), "size": [r2(v) for v in b.size]}
        if out is None:
            rec["fail"], rec["cond"] = self.label(events, fn)
        else:
            self.alive.append(out)
            rec["out"] = id(out)
        self.blobs.append(rec)

    def frame(self, orig_run_frame):
        def run_frame(rep, xyz_s, inten, ring, m, idx):
            self.blobs, self.alive = [], []
            res = orig_run_frame(rep, xyz_s, inten, ring, m, idx)
            self.frames.setdefault(id(rep), {})[idx] = self.snapshot(rep, res)
            return res
        return run_frame

    def snapshot(self, rep, res):
        det = rep.detector
        tr = det.tracker
        thin = list(getattr(det, "_thin", []) or [])
        clusters = {}
        for c in list(res.candidates) + thin:
            clusters[id(c)] = {"d": r2(c.distance), "x0": r2(c.bbox_min[0]), "x1": r2(c.bbox_max[0]),
                               "y": r2(c.centroid[1]), "zone": c.zone, "reason": c.reason or "",
                               "thin": bool(getattr(c, "thin", False)), "weak": bool(getattr(c, "weak", False)),
                               "kind": c.kind, "n": int(c.n), "n_gauge": int(c.n_gauge),
                               "final": any(c is k for k in res.candidates)}
        tracks = []
        for t in tr.tracks:
            # exact floats: the causes re-read the tracker's own thresholds (a 0.4999 s span is not 0.5)
            s = {f: (bool(v) if isinstance(v, (bool,)) else float(v) if isinstance(v, float) else v)
                 for f in TRACK_FIELDS if (v := getattr(t, f, None)) is not None}
            s.update(last=id(t.last) if t.last is not None else None, zone=t.zone, rule_zone=t.rule_zone,
                     vote_zone=t.vote_zone, hit_fraction=float(t.hit_fraction), timed=bool(getattr(tr, "_timed", True)), zone_hist=[bool(z) for z in t.zone_hist],
                     explained=any(getattr(t, "explained_hist", [])),
                     provisional=any(getattr(t, "provisional_explained_hist", [])),
                     qualifies=bool(tr._qualifies(t)),
                     last_kind=t.last.kind if t.last is not None else "",
                     last_low_weak=bool(getattr(t.last, "low_height_weak", False)) if t.last is not None else False,
                     history_max=r2(max(t.history)) if t.history else None)
            tracks.append(s)
        dets = [{"d": r2(d.distance), "y": r2(d.center[1]), "zone": d.zone, "reason": d.reason or "", "id": d.id}
                for d in list(res.detections) + list(res.warnings)]
        blobs = [dict(b) for b in self.blobs]
        return {"blobs": blobs, "clusters": clusters, "tracks": tracks, "dets": dets}


# ------------------------------------------------------------------------------------ causes
def overlaps_x(x0, x1, X, L, tol):
    return x1 >= X - tol and x0 <= X + L + tol


def track_cause(t, cfg):
    """One tracker cause for a matched track that is not a STOP (precedence of Track.zone)."""
    if t["reported"] and t["zone"] == "gauge":
        return "stop_off_object"
    if not t["reported"]:
        if not t["qualifies"]:
            low = t["last_kind"] == "low"
            need = cfg.low_confirm_hits if low else cfg.confirm_hits
            if (cfg.low_min_seen_distance > 0 and low and t["history_max"] is not None
                    and t["history_max"] < cfg.low_min_seen_distance):
                return "track:low_min_seen"
            if t["hits"] < need:
                return "track:confirm_hits"
            if t["confidence"] < cfg.conf_threshold:
                return "track:confidence"
            if cfg.min_hit_fraction > 0 and t["hit_fraction"] < cfg.min_hit_fraction - 1e-9:
                return "track:hit_fraction"
            if cfg.confirm_time_s > 0 and t.get("timed", True) and t["span_s"] < cfg.confirm_time_s - 1e-9:
                return "track:confirm_time"
            return "unclassified:not_qualified"
        if t["last_kind"] == "low":
            return "track:low_onset_gate"
        if cfg.start_clean:
            return "track:start_clean"
        return "unclassified:qualified_unreported"
    # reported, zone warning
    if t.get("withheld"):
        return "track:doubt"
    if t.get("fresh_blocked"):
        if t["explained"] or t["provisional"]:
            return "track:explained_run"
        return "track:fresh_block"
    if t.get("column_held"):
        return "track:column_hold"
    if t.get("approach_block"):
        return "track:approach_block"
    if not t["zone_hist"]:
        return "track:no_zone_votes"
    if t["vote_zone"] != "gauge":
        return "track:zone_vote"
    return "unclassified:reported_warning"


def cause(snap, X, Y, L, W, cfg):
    """Precedence: a clean gauge cluster on the object -> its track; a demoted / advisory cluster ->
    its reason; thin / weak -> tracker-only evidence; a dropped blob -> its first failing check;
    else no corridor blob on the object."""
    tol = max(2.0, 0.03 * X) + L / 2
    lat = 1.0 + W / 2
    on = [(cid, c) for cid, c in snap["clusters"].items()
          if overlaps_x(c["x0"], c["x1"], X, L, tol) and abs(c["y"] - Y) <= lat]
    tracks = {t["last"]: t for t in snap["tracks"] if t["misses"] == 0 and t["last"] is not None}
    clean = [(cid, c) for cid, c in on if c["final"] and c["zone"] == "gauge" and not c["reason"]
             and not c["thin"] and not c["weak"]]
    if clean:
        causes = [track_cause(tracks[int(cid)], cfg) if int(cid) in tracks else "track:no_track"
                  for cid, _ in clean]
        order = ["stop_off_object", "track:", "unclassified"]
        return sorted(causes, key=lambda s: next(i for i, p in enumerate(order) if s.startswith(p)))[0]
    final = [(cid, c) for cid, c in on if c["final"]]
    if final:
        cid, c = min(final, key=lambda kc: abs(kc[1]["d"] - X))
        return f"demoted:{c['reason']}" if c["reason"] else "outside_strict_gauge"
    side = [(cid, c) for cid, c in on if not c["final"]]
    if side:
        cid, c = min(side, key=lambda kc: abs(kc[1]["d"] - X))
        t = tracks.get(int(cid))
        if t is not None and t["reported"] and t["zone"] != "gauge":
            return track_cause(t, cfg)
        return "weak_far_only" if c["weak"] else "thin_scanline_only"
    blobs = [b for b in snap["blobs"] if overlaps_x(b["x0"], b["x1"], X, L, tol) and abs(b["y"] - Y) <= lat]
    if any("out" in b for b in blobs):
        return "post_cluster_drop"
    if blobs:
        b = max(blobs, key=lambda b: b["n_vox"])
        return f"drop:{b['fail']}"
    return "no_blob"


# --------------------------------------------------------------------------------------- run
def git(repo, *a):
    return subprocess.check_output(["git", "-C", str(repo), *a], text=True).strip()


def run(a):
    repo = a.repo.resolve()
    if os.environ.setdefault("RESENSE_REPO", str(repo)) != str(repo):
        sys.exit("RESENSE_REPO names another checkout than --repo")   # judge_runner reads its config there
    sys.path[:0] = [str(repo), str(repo / "ros2_ws/src/resense_ros"), str(JUDGE)]
    import resense
    from resense import _native
    import resense.clustering as C
    if Path(resense.__file__).resolve().parent != repo / "resense":
        sys.exit(f"wrong resense import {resense.__file__}")
    tool = importlib.import_module("range_test" if a.tool == "range" else "probe")
    rec = Recorder(C)
    if not a.hooks_off:
        C._corridor_cluster, C._low_cluster = rec.corridor, rec.low
        tool.run_frame = rec.frame(tool.run_frame)
    sys.argv = [str(JUDGE / f"{'range_test' if a.tool == 'range' else 'probe'}.py"), *a.args]
    tool.main()
    if a.hooks_off:
        return 0
    from resense.config import DetectorConfig  # noqa: F401  (identity only)
    frames = list(rec.frames.values())[-1]     # the object run (range_test runs a baseline first)
    out = Path(a.out)
    rows = []
    cfg = None
    if a.tool == "range":
        res = json.loads(Path(a.args[2] + ".json").read_text())
        from judge_runner import NodeReplica
        cfg = NodeReplica().detector.cfg.tracking
        L, W = (float(v) for v in res["summary"]["obj"][:2])
        for r in res["rows"]:
            if r["X"] is None or r["X"] <= 3.0 or r["n_obj"] <= 0:
                continue
            row = {"k": r["k"], "X": r["X"], "decision": r["decision"], "hit": r["hit"], "n_obj": r["n_obj"]}
            if not r["hit"]:
                row["cause"] = cause(frames[r["k"]], r["X"], r["Y"], L, W, cfg)
            rows.append(row)
    else:
        from judge_runner import NodeReplica
        cfg = NodeReplica().detector.cfg.tracking
        labels = json.loads(Path(a.labels).read_text())
        out_rows = [json.loads(x) for x in Path(a.args[1] + ".jsonl").read_text().splitlines()]
        by_i = {r["i"]: r for r in out_rows}
        for w in a.window:
            name, k0, k1 = w.split(":")
            for k in range(int(k0), int(k1) + 1):
                o = next((o for o in labels.get(f"{k:05d}", []) if o.get("label", o.get("name")) == name
                          and o.get("plausible", True) and o.get("n_points", 1) > 0), None)
                if o is None or k not in by_i:
                    continue
                X, (L, W) = float(o["distance"]), (o.get("size") or [0.5, 0.5])[:2]
                Y = sum(p[1] for p in o["bbox"]) / 2
                tol = max(2, 0.03 * X) + L / 2
                hit = any(abs(d["d"] - X) <= tol and abs(d["c"][1] - Y) <= 1 + W / 2 for d in by_i[k]["dets"])
                row = {"k": k, "object": name, "X": r2(X), "decision": by_i[k]["decision"], "hit": hit,
                       "in_gauge": bool(o["in_gauge"]), "n_obj": int(o.get("n_points", 0))}
                if not hit:
                    row["cause"] = cause(frames[k], X, Y, float(L), float(W), cfg)
                rows.append(row)
    report = {"schema": SCHEMA, "tool": a.tool, "args": a.args, "repo": str(repo),
              "commit": git(repo, "rev-parse", "HEAD"), "version": resense.__version__,
              "native": _native.status(), "harness_sha256": sha256(__file__),
              "judge_sha256": sha256(JUDGE / ("range_test.py" if a.tool == "range" else "probe.py")),
              "rows": rows, "frames": {str(k): v for k, v in frames.items()} if a.keep_frames else None}
    with open(str(out) + ".attrib.json", "x") as f:
        json.dump(report, f)
    n = sum("cause" in r for r in rows)
    print(f"{out}: {len(rows)} visible rows, {n} non-STOP, "
          f"{sum(r.get('cause', '').startswith('unclassified') for r in rows)} unclassified")
    return 0


TIMING = ("decode_ms", "detect_ms", "total_ms")   # wall-clock telemetry of probe / judge records


def verify(a):
    """Hooks-on judge output must equal the hooks-off output: every row and field, except the
    wall-clock timing keys of probe records (the hooks cost time, never results)."""
    on = Path(a.on_output).read_text()
    off = Path(a.off_output).read_text()
    if a.on_output.endswith(".json"):
        same = json.loads(on) == json.loads(off)
    else:
        def strip(text):
            return [{k: v for k, v in json.loads(x).items() if k not in TIMING} for x in text.splitlines()]
        same = strip(on) == strip(off)
    p = Path(a.prefix + ".attrib.json")
    rep = json.loads(p.read_text())
    rep["hooks_off"] = {"equal": same, "on": a.on_output, "off": a.off_output,
                        "on_sha256": sha256(a.on_output), "off_sha256": sha256(a.off_output)}
    p.write_text(json.dumps(rep))
    print(a.prefix, "hooks-off equal" if same else "HOOKS CHANGED THE OUTPUT")
    return 0 if same else 1


def table(a):
    out = {"schema": SCHEMA + "-table", "bins": [f"{lo}-{hi}" for lo, hi in BINS], "cases": {}, "errors": []}
    for prefix in a.prefixes:
        rep = json.loads(Path(prefix + ".attrib.json").read_text())
        if not rep.get("hooks_off", {}).get("equal"):
            out["errors"].append(f"{prefix}: no hooks-off equality proof")
        case = {"commit": rep["commit"], "version": rep["version"], "args": rep["args"],
                "visible": len(rep["rows"]), "stop_hits": sum(r["hit"] for r in rep["rows"]), "causes": {}}
        for r in rep["rows"]:
            if r["hit"]:
                continue
            b = next((f"{lo}-{hi}" for lo, hi in BINS if lo <= r["X"] < hi), "other")
            case["causes"].setdefault(r["cause"], {}).setdefault(b, 0)
            case["causes"][r["cause"]][b] += 1
            if r["cause"].startswith("unclassified") or r["cause"].startswith("unmapped"):
                out["errors"].append(f"{prefix}: frame {r['k']} {r['cause']}")
        case["non_stop"] = case["visible"] - case["stop_hits"]
        out["cases"][Path(prefix).name] = case
    with open(a.out, "x") as f:
        json.dump(out, f, indent=1)
    print(a.out, "errors:", len(out["errors"]))
    return 1 if out["errors"] else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--repo", type=Path, required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--labels")
    r.add_argument("--window", action="append", default=[])
    r.add_argument("--hooks-off", action="store_true", help="plain judge run (the equality reference)")
    r.add_argument("--keep-frames", action="store_true")
    r.add_argument("tool", choices=("range", "probe"))
    r.add_argument("args", nargs=argparse.REMAINDER)
    v = sub.add_parser("verify")
    v.add_argument("prefix")
    v.add_argument("on_output")
    v.add_argument("off_output")
    t = sub.add_parser("table")
    t.add_argument("--out", required=True)
    t.add_argument("prefixes", nargs="+")
    a = ap.parse_args(argv)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    return {"run": run, "verify": verify, "table": table}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
