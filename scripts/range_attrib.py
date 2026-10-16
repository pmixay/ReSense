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
from types import SimpleNamespace

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


BLOB_LOCALS = ("thin", "keep_thin", "size", "min_pts", "weak_height", "dist", "ordinary", "cross_ring", "weak",
               "h_max", "lat_rules", "spare", "lateral", "spare_wall", "lat_along", "factor")
# the lines of Tracker.update that withhold or hold a STOP (matched on their source text, both versions)
CFG_KEYS = ("max_extent", "oversize_split_max_length", "min_height", "gauge_min_points", "thin_min_length",
            "thin_max_width", "thin_max_height", "hardware_max_top", "hardware_max_width", "hardware_max_height",
            "wall_min_height", "wall_min_lateral", "wall_segment_min_length", "wall_segment_max_width",
            "linear_min_aspect", "linear_max_height", "linear_min_lateral")
LOW_KEYS = ("min_length", "max_length", "max_width", "min_height", "min_points", "min_width", "min_top")
GATES = ("q = False", "q = self._fresh_stop_ok(t)", "fresh_blocked = True", "fresh_blocked = explained_blocked = True",
         "t.reported = False", "t.reported = True")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plain(v):
    """A JSON-able copy of a recorded local (numpy scalars / small arrays); None for anything else."""
    if isinstance(v, (bool, int, float, str)) or v is None:
        return v
    if hasattr(v, "tolist"):
        return v.tolist()
    return None


def guard_text(lines, i):
    """The ``if`` / ``elif`` condition (continuation lines joined) that guards source line ``i``."""
    ind = len(lines[i]) - len(lines[i].lstrip())
    for n in range(i - 1, -1, -1):
        s = lines[n].strip()
        if s and len(lines[n]) - len(lines[n].lstrip()) < ind and (s.startswith("if ") or s.startswith("elif ")):
            parts, m = [s], n + 1
            while not parts[-1].endswith(":") and m < i:
                parts.append(lines[m].strip())
                m += 1
            return " ".join(parts)
    return ""


class TrackerTrace:
    """Records, inside the tracker's own update, which gate lines ran for each track, the exact inputs
    and result of ``_qualifies``, the results of ``_carried_along`` / ``_fresh_stop_ok``, and which
    ``return`` of the ``zone`` / ``rule_zone`` / ``vote_zone`` properties fired (``sys.settrace``
    only on these code objects; nothing is written to the tracker)."""

    def __init__(self, T):
        import inspect
        Tr, Tk = T.Tracker, T.Track
        self.names = {Tr.update.__code__: "update", Tr._qualifies.__code__: "qualifies",
                      Tk.zone.fget.__code__: "zone", Tk.rule_zone.fget.__code__: "rule_zone",
                      Tk.vote_zone.fget.__code__: "vote_zone"}
        for n, key in (("_carried_along", "carried"), ("_fresh_stop_ok", "fresh_ok")):
            if hasattr(Tr, n):
                self.names[getattr(Tr, n).__code__] = key
        self.guards = {}
        for fn in (Tr.update, Tr._qualifies, Tk.zone.fget, Tk.rule_zone.fget, Tk.vote_zone.fget):
            lines, start = inspect.getsourcelines(fn)
            for i, text in enumerate(lines):
                s = text.strip()
                if s in GATES if fn is Tr.update else s.startswith("return"):
                    self.guards[(fn.__code__, start + i)] = (s, guard_text(lines, i))
        self.record = {}

    def start(self):
        self.record = {}
        sys.settrace(self._global)

    def stop(self):
        sys.settrace(None)

    def _rec(self, t):
        return self.record.setdefault(id(t), {"gates": [], "zone_eval": {}})

    def _global(self, frame, event, arg):
        return self._local if frame.f_code in self.names else None

    def _local(self, frame, event, arg):
        name = self.names[frame.f_code]
        loc = frame.f_locals
        key = (frame.f_code, frame.f_lineno)
        if event == "line" and name == "update" and key in self.guards and loc.get("t") is not None:
            text, guard = self.guards[key]
            self._rec(loc["t"])["gates"].append({"line": frame.f_lineno, "text": text, "guard": guard})
        elif event == "return":
            if name == "qualifies" and frame.f_back is not None and frame.f_back.f_code.co_name == "update":
                t, c = loc["t"], loc["self"].cfg
                low = t.last is not None and t.last.kind == "low"
                q = {"value": bool(arg), "line": frame.f_lineno, "guard": self.guards.get(key, ("", ""))[1],
                     "hits": t.hits, "need_hits": c.low_confirm_hits if low else c.confirm_hits,
                     "confidence": float(t.confidence), "conf_threshold": c.conf_threshold, "misses": t.misses,
                     "span_s": float(t.span_s), "need_span": loc.get("need_span"), "hit_fraction": float(t.hit_fraction),
                     "min_hit_fraction": c.min_hit_fraction}
                self._rec(t)["qualifies"] = q
            elif name in ("zone", "rule_zone", "vote_zone"):
                t = loc["self"]
                text, guard = self.guards.get(key, ("", ""))
                self._rec(t)["zone_eval"][name] = {
                    "value": arg, "line": frame.f_lineno, "return": text, "guard": guard,
                    "withheld": bool(t.withheld), "fresh_blocked": bool(t.fresh_blocked),
                    "column_held": bool(t.column_held), "approach_block": bool(t.approach_block),
                    "zone_hist": len(t.zone_hist), "near_escalated": bool(t.near_escalated)}
            elif name in ("carried", "fresh_ok") and loc.get("t") is not None:
                self._rec(loc["t"])[name] = bool(arg)
        return self._local


QUAL_CLAUSES = ("confirm_hits", "confidence", "misses", "confirm_time", "hit_fraction")


def qualifies_failure(q):
    """The first false clause of ``_qualifies`` (its own expression order) from the recorded inputs."""
    if "low_min_seen_distance" in q["guard"] and not q["value"]:
        return "low_min_seen"
    need_span = q["need_span"] if q["need_span"] is not None else 0.0
    flags = [q["hits"] >= q["need_hits"], q["confidence"] >= q["conf_threshold"], q["misses"] == 0,
             q["span_s"] >= need_span - 1e-9,
             q["min_hit_fraction"] <= 0 or q["hit_fraction"] >= q["min_hit_fraction"] - 1e-9]
    if all(flags) != q["value"]:
        return "qualifies_mismatch"
    return next((n for n, f in zip(QUAL_CLAUSES, flags) if not f), None)


def traced_track_cause(t):
    """The cause from the branches recorded inside Tracker.update / Track.zone (not reconstructed)."""
    br = t.get("branch") or {}
    gates = br.get("gates", [])

    def gate(word):
        return next((g for g in gates if word in g["guard"]), None)
    if t["reported"]:
        if t["zone"] == "gauge":
            return "stop_off_object"
        z = br.get("zone_eval", {}).get("zone")
        if z is None:
            return "unclassified:no_zone_trace"
        if z["value"] == "warning" and "withheld" in z["guard"]:
            if z["withheld"]:
                return "track:doubt"
            if gate("explained_run"):
                return "track:ego_veto" if br.get("carried") else "track:explained_run"
            if gate("fresh_stop_evidence"):
                return "track:fresh_stop_evidence"
            if gate("was_blocked"):
                return "track:fresh_block_held"
            return "unclassified:fresh_blocked_without_gate"
        r = br.get("zone_eval", {}).get("rule_zone")
        if r is None:
            return "unclassified:no_rule_zone_trace"
        if "column_held" in r["guard"] and r["value"] == "warning":
            if not r["zone_hist"]:
                return "track:no_zone_votes"
            return "track:column_hold" if r["column_held"] else "track:approach_block"
        v = br.get("zone_eval", {}).get("vote_zone")
        if v is not None and v["value"] == "warning":
            return "track:zone_vote"
        return "unclassified:reported_warning"
    q = br.get("qualifies")
    if q is None:
        return "unclassified:no_qualifies_trace"
    if not q["value"]:
        f = qualifies_failure(q)
        return f"track:{f}" if f in QUAL_CLAUSES + ("low_min_seen",) else f"unclassified:{f}"
    for word, name in (("low_ok", "low_onset_gate"), ("rail_within", "rail_within"), ("start_clean", "start_clean")):
        if gate(word):
            return f"track:{name}"
    if gate("fresh_stop_evidence") and br.get("fresh_ok") is False:
        return "track:fresh_stop_evidence"
    if gate("explained_run"):
        return "track:ego_veto" if br.get("carried") else "track:explained_run"
    if gate("low_height_weak"):
        return "track:low_weak_expired"
    return "unclassified:traced_unreported"


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
                keep = {k: plain(loc[k]) for k in BLOB_LOCALS if k in loc}
                if "b" in loc and hasattr(loc["b"], "n_vox"):
                    keep["n_vox"] = int(loc["b"].n_vox)
                if "part" in loc:
                    keep["part_is_none"] = loc["part"] is None
                # the config object this call used (the low-object stages pass their own cluster / low configs)
                if "cfg" in loc:
                    keep["cfg"] = {k: plain(getattr(loc["cfg"], k)) for k in CFG_KEYS if hasattr(loc["cfg"], k)}
                if "low_cfg" in loc:
                    keep["low_cfg"] = {k: plain(getattr(loc["low_cfg"], k, 0.0)) for k in LOW_KEYS}
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
               "y0": r2(pts[:, 1].min()), "y1": r2(pts[:, 1].max()),
               "n_vox": int(b.n_vox), "size": [r2(v) for v in b.size]}
        if out is None:
            rec["fail"], rec["cond"] = self.label(events, fn)
            # the locals at the firing return(s), for the independent re-evaluation in ``check``
            rec["evidence"] = {e[0]: e[4] for e in events if e[0] in (fn, "_is_infrastructure") and
                               (e[0] == fn or e[3])}
        else:
            self.alive.append(out)
            rec["out"] = id(out)
        self.blobs.append(rec)

    def frame(self, orig_run_frame, tracer=None):
        def run_frame(rep, xyz_s, inten, ring, m, idx):
            self.blobs, self.alive = [], []
            if tracer is not None:
                tracer.start()
            try:
                res = orig_run_frame(rep, xyz_s, inten, ring, m, idx)
            finally:
                if tracer is not None:
                    tracer.stop()
            snap = self.snapshot(rep, res)
            if tracer is not None:
                for t in snap["tracks"]:
                    t["branch"] = tracer.record.get(t["_obj"], {})
            for t in snap["tracks"]:
                t.pop("_obj", None)
            self.frames.setdefault(id(rep), {})[idx] = snap
            return res
        return run_frame

    def snapshot(self, rep, res):
        det = rep.detector
        tr = det.tracker
        thin = list(getattr(det, "_thin", []) or [])
        clusters = {}
        for c in list(res.candidates) + thin:
            clusters[id(c)] = {"d": r2(c.distance), "x0": r2(c.bbox_min[0]), "x1": r2(c.bbox_max[0]),
                               "y": r2(c.centroid[1]), "y0": r2(c.bbox_min[1]), "y1": r2(c.bbox_max[1]),
                               "zone": c.zone, "reason": c.reason or "",
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
                     history_max=r2(max(t.history)) if t.history else None,
                     column_hist=[bool(z) for z in getattr(t, "column_hist", [])],
                     column_hold=int(getattr(t, "column_hold", 0)), _obj=id(t))
            tracks.append(s)
        dets = [{"d": r2(d.distance), "y": r2(d.center[1]), "zone": d.zone, "reason": d.reason or "", "id": d.id}
                for d in list(res.detections) + list(res.warnings)]
        blobs = [dict(b) for b in self.blobs]
        return {"blobs": blobs, "clusters": clusters, "tracks": tracks, "dets": dets}


# ------------------------------------------------------------------------------------ causes
def overlaps_x(x0, x1, X, L, tol):
    return x1 >= X - tol and x0 <= X + L + tol


MARGIN = 0.5   # m around the object box: its returns lie inside it (+1 cm noise); one voxel and rounding spare


def on_object(e, X, Y, L, W):
    """Physical overlap of a blob / cluster bbox with the object box: the structure can contain the
    object's returns. (The judge's distance tolerance, max(2 m, 3 %) + L/2, matches a STOP report to the
    object; used for attribution it would credit a neighbouring structure several metres short of it.)"""
    return (e["x1"] >= X - MARGIN and e["x0"] <= X + L + MARGIN
            and e["y1"] >= Y - W / 2 - MARGIN and e["y0"] <= Y + W / 2 + MARGIN)


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


def cause(snap, X, Y, L, W, cfg, track_fn=track_cause):
    """Precedence: a clean gauge cluster on the object -> its track; a demoted / advisory cluster ->
    its reason; thin / weak -> tracker-only evidence; a dropped blob -> its first failing check;
    else no corridor blob on the object."""
    on = [(cid, c) for cid, c in snap["clusters"].items() if on_object(c, X, Y, L, W)]
    tracks = {t["last"]: t for t in snap["tracks"] if t["misses"] == 0 and t["last"] is not None}
    clean = [(cid, c) for cid, c in on if c["final"] and c["zone"] == "gauge" and not c["reason"]
             and not c["thin"] and not c["weak"]]
    if clean:
        causes = [track_fn(tracks[int(cid)], cfg) if int(cid) in tracks else "track:no_track"
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
            return track_fn(t, cfg)
        return "weak_far_only" if c["weak"] else "thin_scanline_only"
    blobs = [b for b in snap["blobs"] if on_object(b, X, Y, L, W)]
    if any("out" in b for b in blobs):
        return "post_cluster_drop"
    if blobs:
        b = max(blobs, key=lambda b: b["n_vox"])
        return f"drop:{b['fail']}"
    return "no_blob"


def attribute(row, snap, X, Y, L, W, cfg):
    """The cause from the recorded tracker branches; the reconstruction from the snapshot is kept
    beside it so that every disagreement is visible."""
    row["cause"] = cause(snap, X, Y, L, W, cfg, track_fn=lambda t, _cfg: traced_track_cause(t))
    row["recon_cause"] = cause(snap, X, Y, L, W, cfg)


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
    import resense.tracking as T
    rec = Recorder(C)
    if not a.hooks_off:
        C._corridor_cluster, C._low_cluster = rec.corridor, rec.low
        tool.run_frame = rec.frame(tool.run_frame, TrackerTrace(T))
    sys.argv = [str(JUDGE / f"{'range_test' if a.tool == 'range' else 'probe'}.py"), *a.args]
    tool.main()
    if a.hooks_off:
        return 0
    from resense.config import DetectorConfig  # noqa: F401  (identity only)
    frames = list(rec.frames.values())[-1]     # the object run (range_test runs a baseline first)
    keep = {int(k) for k in a.keep_frames_at.split(",") if k}
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
            row = {"k": r["k"], "X": r["X"], "Y": r["Y"], "L": L, "W": W, "decision": r["decision"], "hit": r["hit"],
                   "n_obj": r["n_obj"]}
            if not r["hit"]:
                attribute(row, frames[r["k"]], r["X"], r["Y"], L, W, cfg)
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
                row.update(Y=r2(Y), L=float(L), W=float(W))
                if not hit:
                    attribute(row, frames[k], X, Y, float(L), float(W), cfg)
                rows.append(row)
    report = {"schema": SCHEMA, "tool": a.tool, "args": a.args, "repo": str(repo),
              "commit": git(repo, "rev-parse", "HEAD"), "version": resense.__version__,
              "native": _native.status(), "harness_sha256": sha256(__file__),
              "judge_sha256": sha256(JUDGE / ("range_test.py" if a.tool == "range" else "probe.py")),
              "labels": a.labels, "window": a.window, "rows": rows,
              "frames": {str(k): v for k, v in frames.items() if a.keep_frames or k in keep}}
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


# ------------------------------------------------------------------------------- label check
INFRA_RULES = (
    ("infra_linear_thin", lambda s, lat, h, sp, la, c: s[0] > c.thin_min_length and s[1] < c.thin_max_width
     and s[2] < c.thin_max_height),
    ("infra_hardware", lambda s, lat, h, sp, la, c: h < c.hardware_max_top and s[1] < c.hardware_max_width
     and s[2] < c.hardware_max_height),
    ("infra_wall_side", lambda s, lat, h, sp, la, c: s[2] > c.wall_min_height and abs(lat) > c.wall_min_lateral
     and not sp),
    ("infra_wall_segment", lambda s, lat, h, sp, la, c: s[2] > c.wall_min_height and s[0] > c.wall_segment_min_length
     and s[1] < c.wall_segment_max_width),
    ("infra_linear_side", lambda s, lat, h, sp, la, c: s[0] > c.linear_min_aspect * max(float(s[1]), 0.05)
     and s[2] < c.linear_max_height and abs(lat if la is None else la) > c.linear_min_lateral),
)


def _window(row):
    X, L = row["X"], row["L"]
    return max(2.0, 0.03 * X) + L / 2, 1.0 + row["W"] / 2


def recheck(row, snap, cfg):
    """Independently confirm, from the full frame snapshot and the detector config, that the rule named
    by ``row['cause']`` is what kept this frame from a matching STOP. Returns (confirmed, evidence)."""
    cl, tk, low = cfg.cluster, cfg.tracking, cfg.lowobj
    X, Y, L = row["X"], row["Y"], row["L"]
    tol, lat = _window(row)
    # physical overlap with the object box, recomputed from the bboxes (not the harness's selection)
    on_c = {int(cid): c for cid, c in snap["clusters"].items()
            if c["x1"] >= X - MARGIN and c["x0"] <= X + L + MARGIN
            and c["y1"] >= Y - row["W"] / 2 - MARGIN and c["y0"] <= Y + row["W"] / 2 + MARGIN}
    on_b = [b for b in snap["blobs"] if b["x1"] >= X - MARGIN and b["x0"] <= X + L + MARGIN
            and b["y1"] >= Y - row["W"] / 2 - MARGIN and b["y0"] <= Y + row["W"] / 2 + MARGIN]
    final = {k: c for k, c in on_c.items() if c["final"]}
    clean = {k: c for k, c in final.items() if c["zone"] == "gauge" and not c["reason"] and not c["thin"]
             and not c["weak"]}
    tracks = {t["last"]: t for t in snap["tracks"] if t["misses"] == 0 and t["last"] is not None}
    hit = any(abs(d["d"] - X) <= tol and abs(d["y"] - Y) <= lat and d["zone"] == "gauge" for d in snap["dets"])
    ev = {"clusters_on_object": len(on_c), "blobs_on_object": len(on_b), "clean_on_object": len(clean),
          "matching_gauge_detection": hit}
    c = row["cause"]
    if hit:
        return False, dict(ev, why="a matching gauge detection exists")
    if c == "no_blob":
        near = min((min(abs(b["x0"] - X), abs(b["x1"] - X)) for b in snap["blobs"]), default=None)
        return not on_b and not on_c, dict(ev, blobs_in_frame=len(snap["blobs"]), nearest_blob_dx=near)
    if c.startswith("drop:"):
        rule = c[5:]
        cand = [b for b in on_b if b.get("fail") == rule]
        if final or not cand:
            return False, dict(ev, why="a surviving cluster on the object, or no blob with this failure")
        b = max(cand, key=lambda b: b["n_vox"])
        e = b.get("evidence", {})
        cc, ic, lc = e.get("_corridor_cluster", {}), e.get("_is_infrastructure", {}), e.get("_low_cluster", {})
        ev.update(blob={k: b[k] for k in ("x0", "x1", "y", "n_vox", "size")}, locals=e)
        # re-evaluate with the configuration the call itself used (recorded), not the detector default
        used = e.get(b["fn"], {})
        cl = SimpleNamespace(**{**vars(cl), **used.get("cfg", {}), **ic.get("cfg", {})})
        low = SimpleNamespace(**{**{k: getattr(low, k, 0.0) for k in LOW_KEYS}, **lc.get("low_cfg", {})})
        ev["stage_config_differs"] = any(getattr(cfg.cluster, k, None) != v for k, v in used.get("cfg", {}).items())
        if rule == "oversize_split_refused":
            ok = bool(cc.get("part_is_none")) and max(cc["size"]) > cl.max_extent and cl.oversize_split_max_length > 0
        elif rule == "oversize":
            ok = max(cc["size"]) > cl.max_extent
        elif rule == "thin":
            ok = cc["size"][2] < cl.min_height and not cc.get("keep_thin")
        elif rule == "min_points":
            ok = cc["n_vox"] < cc["min_pts"] and not (cc.get("ordinary") or cc.get("cross_ring"))
        elif rule.startswith("infra_"):
            fired = [n for n, f in INFRA_RULES
                     if f(ic["size"], ic["lateral"], ic["h_max"], ic.get("spare_wall"), ic.get("lat_along"), cl)]
            ev["infra_rules_true"] = fired
            ok = bool(fired) and fired[0] == rule
        elif rule.startswith("low_"):
            s = lc["size"]
            shape = (s[0] < getattr(low, "min_length", 0.0) or s[0] > low.max_length or s[1] > low.max_width
                     or s[2] < low.min_height or lc["n_vox"] < low.min_points)
            ok = {"low_shape": shape, "low_narrow": not shape and s[1] < low.min_width,
                  "low_below_railhead": not shape and s[1] >= low.min_width and bool(lc.get("weak_height"))}[rule]
        else:
            ok = False
        return bool(ok), ev
    if c.startswith("demoted:") or c == "outside_strict_gauge":
        if clean:
            return False, dict(ev, why="a clean gauge cluster is on the object")
        reason = c[8:] if c.startswith("demoted:") else ""
        match = [k for k in final.values() if k["reason"] == reason and k["zone"] == "warning"]
        if c == "outside_strict_gauge":
            match = [k for k in match if k["n_gauge"] < cl.gauge_min_points]
        ev["clusters"] = list(final.values())
        return bool(match), ev
    if c in ("thin_scanline_only", "weak_far_only"):
        side = [(k, x) for k, x in on_c.items() if not x["final"] and (x["weak"] if c == "weak_far_only" else x["thin"])]
        ok = not final and bool(side) and not any(k in tracks and tracks[k]["reported"] and tracks[k]["zone"] == "gauge"
                                                  for k, _ in side)
        return ok, dict(ev, side=[x for _, x in side])
    if c == "post_cluster_drop":
        return not on_c and any("out" in b for b in on_b), ev
    # tracker causes: the matched track's state after the update (snapshot, not the branch trace); as in
    # cause(), a clean cluster's track first, else a reported track continued by a thin / weak cluster
    ts = [tracks[k] for k in clean if k in tracks] or [
        tracks[k] for k, x in on_c.items() if not x["final"] and k in tracks and tracks[k]["reported"]]
    if not ts:
        return False, dict(ev, why="no track matched to a clean cluster on the object")
    t = ts[0]
    ev["track"] = {k: t.get(k) for k in ("id", "hits", "confidence", "span_s", "hit_fraction", "reported", "zone",
                                         "withheld", "fresh_blocked", "column_held", "approach_block", "zone_hist",
                                         "column_hist", "column_hold", "clean_run", "explained", "provisional",
                                         "qualifies", "last_kind")}
    ev["branch"] = t.get("branch")
    need = tk.low_confirm_hits if t["last_kind"] == "low" else tk.confirm_hits
    unrep = not t["reported"]
    warn = t["reported"] and t["zone"] == "warning"
    checks = {
        "track:confirm_hits": unrep and t["hits"] < need,
        "track:confidence": unrep and t["hits"] >= need and t["confidence"] < tk.conf_threshold,
        "track:confirm_time": unrep and t["hits"] >= need and t["confidence"] >= tk.conf_threshold
        and t["span_s"] < tk.confirm_time_s - 1e-9,
        "track:hit_fraction": unrep and t["hits"] >= need and t["confidence"] >= tk.conf_threshold
        and t["hit_fraction"] < tk.min_hit_fraction - 1e-9,
        "track:doubt": warn and t.get("withheld"),
        "track:explained_run": (unrep and t["qualifies"] or warn and t.get("fresh_blocked"))
        and (t["explained"] or t["provisional"]) and t.get("clean_run", 0) < tk.explained_run,
        "track:column_hold": warn and not t.get("withheld") and not t.get("fresh_blocked")
        and t["column_hold"] > 0 and sum(t["column_hist"]) >= t["column_hold"],
        "track:approach_block": warn and not t.get("withheld") and not t.get("fresh_blocked")
        and not t.get("column_held") and t.get("approach_block"),
        "track:zone_vote": warn and not any(t.get(k) for k in ("withheld", "fresh_blocked", "column_held",
                                                                 "approach_block")) and bool(t["zone_hist"])
        and sum(t["zone_hist"]) < tk.zone_min_fraction * max(len(t["zone_hist"]), getattr(tk, "zone_min_votes", 0))
        - 1e-9,
        "stop_off_object": t["reported"] and t["zone"] == "gauge",
    }
    if c not in checks:
        return False, dict(ev, why="no independent check for this cause")
    return bool(checks[c]), ev


def check(a):
    """Sample up to ``--samples`` rows per cause (spread over cases), re-run those cases with the
    sampled frames' full snapshots kept, confirm the cause is reproduced, and re-check it with
    :func:`recheck`. Writes the per-cause tally and every wrong label."""
    repo = a.repo.resolve()
    if os.environ.setdefault("RESENSE_REPO", str(repo)) != str(repo):
        sys.exit("RESENSE_REPO names another checkout than --repo")
    sys.path[:0] = [str(repo), str(repo / "ros2_ws/src/resense_ros"), str(JUDGE)]
    from judge_runner import NodeReplica
    cfg = NodeReplica().detector.cfg
    root, out = Path(a.root), Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=False)
    reports = {p.name[:-len(".attrib.json")]: json.loads(p.read_text()) for p in sorted(root.glob("*.attrib.json"))}
    by_cause = {}
    for case, rep in reports.items():
        for r in rep["rows"]:
            if not r["hit"]:
                by_cause.setdefault(r["cause"], []).append((case, r))
    picks = {}
    for c, rows in sorted(by_cause.items()):
        cases = sorted({case for case, _ in rows})
        chosen = []
        for i in range(a.samples):            # round robin over cases, evenly spaced within a case
            case = cases[i % len(cases)]
            mine = [r for cs, r in rows if cs == case]
            r = mine[(i // len(cases)) * len(mine) // max(1, a.samples) % len(mine)]
            if (case, r["k"]) not in chosen:
                chosen.append((case, r["k"]))
        picks[c] = chosen
    need = {}
    for c, ch in picks.items():
        for case, k in ch:
            need.setdefault(case, set()).add(k)
    reruns = {}
    for case, ks in sorted(need.items()):
        rep = reports[case]
        args = list(rep["args"])
        prefix = str(out / case)
        args[2 if rep["tool"] == "range" else 1] = prefix + ".rerun"
        cmd = [sys.executable, __file__, "run", "--repo", str(repo), "--out", prefix,
               "--keep-frames-at", ",".join(map(str, sorted(ks)))]
        if rep["tool"] == "probe":
            cmd += ["--labels", rep["labels"]] + [x for w in rep["window"] for x in ("--window", w)]
        cmd += [rep["tool"], *args]
        with open(prefix + ".log", "x") as log:
            subprocess.run(cmd, check=True, stdout=log, stderr=subprocess.STDOUT, cwd=repo)
        reruns[case] = json.loads(Path(prefix + ".attrib.json").read_text())
    result = {"schema": SCHEMA + "-check", "root": str(root), "commit": git(repo, "rev-parse", "HEAD"),
              "samples_per_cause": a.samples, "causes": {}, "wrong": []}
    for c, ch in sorted(picks.items()):
        tally = {"rows_with_cause": len(by_cause[c]), "checked": 0, "confirmed": 0, "rerun_same_cause": 0,
                 "traced_equals_reconstructed": 0, "samples": []}
        for case, k in ch:
            rr = reruns[case]
            row = next(r for r in rr["rows"] if r["k"] == k)
            orig = next(r for r in reports[case]["rows"] if r["k"] == k)
            ok, ev = recheck(row, rr["frames"][str(k)], cfg) if row.get("cause") == c else (False, {"why": "rerun cause differs"})
            tally["checked"] += 1
            tally["confirmed"] += bool(ok)
            tally["rerun_same_cause"] += row.get("cause") == orig.get("cause")
            tally["traced_equals_reconstructed"] += row.get("cause") == row.get("recon_cause")
            s = {"case": case, "k": k, "X": row["X"], "cause": row.get("cause"), "recon_cause": row.get("recon_cause"),
                 "confirmed": bool(ok), "evidence": ev}
            tally["samples"].append(s)
            if not ok:
                result["wrong"].append(s)
        result["causes"][c] = tally
    with open(out / "check.json", "x") as f:
        json.dump(result, f, indent=1, default=str)
    for c, t in result["causes"].items():
        print(f"{c}: rows {t['rows_with_cause']}, checked {t['checked']}, confirmed {t['confirmed']}, "
              f"rerun same {t['rerun_same_cause']}, traced==recon {t['traced_equals_reconstructed']}")
    print("wrong labels:", len(result["wrong"]))
    return 1 if result["wrong"] else 0


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
    r.add_argument("--keep-frames-at", default="", help="comma list of frame indices whose full snapshot is kept")
    r.add_argument("tool", choices=("range", "probe"))
    r.add_argument("args", nargs=argparse.REMAINDER)
    v = sub.add_parser("verify")
    v.add_argument("prefix")
    v.add_argument("on_output")
    v.add_argument("off_output")
    k = sub.add_parser("check")
    k.add_argument("--repo", type=Path, required=True)
    k.add_argument("--samples", type=int, default=3)
    k.add_argument("root", help="the run_x1.sh output folder of one checkout")
    k.add_argument("out_dir", help="new folder for the re-runs and check.json")
    t = sub.add_parser("table")
    t.add_argument("--out", required=True)
    t.add_argument("prefixes", nargs="+")
    a = ap.parse_args(argv)
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    return {"run": run, "verify": verify, "table": table, "check": check}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
