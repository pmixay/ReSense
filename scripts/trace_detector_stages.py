"""Read-only, single-threaded diagnostics around the unchanged detector.

Target points are explicit frame indices supplied by the caller. This observes production
functions, including their actual return lines; it does not replay an approximation of the
filters. Timing/latency from an instrumented run is not a performance measurement.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
from functools import lru_cache
import inspect
import sys
import textwrap

import numpy as np

from resense import clustering
from resense.detector import Detector
from resense.gauge import point_in_polygon


@lru_cache(maxsize=None)
def _return_conditions(function):
    source, start = inspect.getsourcelines(function)
    tree = ast.parse(textwrap.dedent("".join(source)))
    conditions = {}

    def visit(node, branch=()):
        if isinstance(node, ast.Return):
            conditions[start + node.lineno - 1] = {
                "condition": branch[-1] if branch else "unconditional",
                "expression": ast.unparse(node.value) if node.value is not None else "None",
            }
        for field, value in ast.iter_fields(node):
            children = value if isinstance(value, list) else [value]
            for child in children:
                if isinstance(child, ast.AST):
                    nested = branch
                    if isinstance(node, ast.If) and field in ("body", "orelse"):
                        cond = ast.unparse(node.test)
                        nested += (cond if field == "body" else "not (" + cond + ")",)
                    visit(child, nested)

    visit(tree)
    return conditions


def _range(values):
    return [float(values.min()), float(values.max())] if len(values) else None


def cluster_record(cluster, targets):
    return {
        "target_points": int(np.isin(cluster.points_idx, targets).sum()),
        "points": int(cluster.n_raw), "voxels": int(cluster.n),
        "gauge_voxels": int(cluster.n_gauge), "zone": cluster.zone,
        "reason": cluster.reason, "kind": cluster.kind, "thin": bool(cluster.thin),
        "demoted": bool(cluster.demoted), "score": float(cluster.score),
        "distance": float(cluster.distance), "lateral": float(cluster.lateral),
        "height": [float(cluster.height_min), float(cluster.height_max)],
        "size": (cluster.bbox_max - cluster.bbox_min).astype(float).tolist(),
    }


class TraceDetector(Detector):
    """Call ``process_target(frame, indices)``; normal output remains the original result."""

    def process_target(self, frame, indices, ego_speed=None):
        self.target_groups = {k: np.asarray(v, dtype=np.int64) for k, v in indices.items()} if isinstance(indices, dict) else {
            "target": np.asarray(indices, dtype=np.int64)}
        self.target_indices = np.unique(np.concatenate(list(self.target_groups.values()))) if self.target_groups else np.empty(0, np.int64)
        self.trace = {"target_points": len(self.target_indices), "stages": {}, "blobs": []}
        result = super().process(frame, ego_speed)
        self.trace["track"] = result.track.to_dict()
        self.trace["mount"] = result.mount
        self.trace["hanging_stage_called"] = bool(self.trace.get("hanging_stage_called", False))
        self.trace["clusters"] = [cluster_record(c, self.target_indices) for c in result.candidates
                                  if np.isin(c.points_idx, self.target_indices).any()]
        for row, c in zip(self.trace["clusters"], [c for c in result.candidates
                         if np.isin(c.points_idx, self.target_indices).any()]):
            row["groups"] = self._group_counts(c.points_idx)
        self.trace["tracks"] = []
        for track in self.tracker.tracks:
            if track.last is None or track.misses or not np.isin(track.last.points_idx, self.target_indices).any():
                continue
            self.trace["tracks"].append({
                "id": track.id, "hits": track.hits, "misses": track.misses,
                "age": track.age, "span_s": float(track.span_s),
                "reported": bool(track.reported), "zone": track.zone,
                "vote_zone": track.vote_zone, "confidence": float(track.confidence),
                "hit_hist": list(track.hit_hist), "zone_hist": list(track.zone_hist),
                "column_hist": list(track.column_hist), "near_hist": list(track.near_hist),
                "near_escalated": bool(track.near_escalated), "column_held": bool(track.column_held),
                "last_reason": track.last.reason, "last_kind": track.last.kind,
                "target_points": int(np.isin(track.last.points_idx, self.target_indices).sum()),
                "groups": self._group_counts(track.last.points_idx),
            })
        return result

    def _candidate_record(self, cand):
        if cand is None:
            return None
        m = np.isin(cand.idx, self.target_indices)
        return {"points": int(m.sum()), "strict_points": int((m & cand.in_gauge).sum()),
                "low_points": int((m & cand.low).sum()), "lateral": _range(cand.dy[m]),
                "height": _range(cand.h[m]), "groups": self._group_counts(cand.idx),
                "strict_groups": self._group_counts(cand.idx[cand.in_gauge])}

    def _group_counts(self, indices):
        return {name: int(np.isin(indices, ids).sum()) for name, ids in self.target_groups.items()}

    def _corridor(self, xyz, intensity):
        out = super()._corridor(xyz, intensity)
        cand, dy, h, mask, ranges = out
        ids = self.target_indices
        self.trace["geometry"] = {
            "x": _range(xyz[ids, 0]), "y": _range(xyz[ids, 1]), "z": _range(xyz[ids, 2]),
            "lateral": _range(dy[ids]), "height": _range(h[ids]),
            "valid": float(ranges[0]), "axis_valid": float(ranges[1]),
            "height_valid": float(ranges[2]), "rail_slabs": int(self.track.rail_slabs),
        }
        self.trace["stages"]["corridor"] = self._candidate_record(cand)
        self.trace["geometry"]["groups"] = {
            name: {"points": len(ids), "x": _range(xyz[ids, 0]), "y": _range(xyz[ids, 1]),
                   "z": _range(xyz[ids, 2]), "lateral": _range(dy[ids]), "height": _range(h[ids])}
            for name, ids in self.target_groups.items()}
        for name, ids in self.target_groups.items():
            raw_strict = point_in_polygon(dy[ids], h[ids], np.asarray(self.cfg.gauge.profile))
            self.trace["geometry"]["groups"][name]["nominal_gauge_points_before_filters"] = int(raw_strict.sum())
        return out

    def _low_stage(self, *args):
        out = super()._low_stage(*args)
        for name, cand in zip(("after_low", "straddle", "near"), out):
            self.trace["stages"][name] = self._candidate_record(cand)
        return out

    def _accumulate(self, *args):
        out = super()._accumulate(*args)
        self.trace["stages"]["merged"] = self._candidate_record(out[0])
        return out

    @contextmanager
    def _observe_blobs(self):
        originals = {name: getattr(clustering, name) for name in ("_corridor_cluster", "_low_cluster")}
        observed = [*originals.values(), clustering._is_infrastructure, clustering._advisory_reason]
        returns = {fn.__code__: (fn.__name__, _return_conditions(fn)) for fn in observed}

        def wrap(function):
            signature = inspect.signature(function)

            def run(*args, **kwargs):
                params = signature.bind(*args, **kwargs).arguments
                blob, frame_idx = params["b"], params["frame_idx"]
                overlap = np.isin(frame_idx[blob.idx], self.target_indices)
                if not overlap.any():
                    return function(*args, **kwargs)
                record = {
                    "function": function.__name__, "target_points": int(overlap.sum()),
                    "raw_points": len(blob.idx), "voxels": blob.n_vox,
                    "size": blob.size.astype(float).tolist(),
                    "distance": float(blob.pts[:, 0].min()),
                    "lateral": _range(params["dy"][blob.idx]),
                    "height": _range(params["h"][blob.idx]), "returns": [],
                    "groups": self._group_counts(frame_idx[blob.idx]),
                }
                if "in_gauge" in params:
                    strict = params["in_gauge"][blob.idx]
                    record["target_strict_points"] = int((overlap & strict).sum())
                    record["strict_voxels"] = int(np.unique(params["inv"][blob.idx][strict]).size)

                def profile(frame, event, value):
                    if event != "return" or frame.f_code not in returns:
                        return
                    name, sites = returns[frame.f_code]
                    site = sites.get(frame.f_lineno, {})
                    answer = value if isinstance(value, (str, bool, int, float, type(None))) else type(value).__name__
                    record["returns"].append({"function": name, "line": frame.f_lineno,
                                              "value": answer, **site})

                previous = sys.getprofile()
                if previous is not None:
                    raise RuntimeError("stage tracing requires an unused Python profile hook")
                sys.setprofile(profile)
                try:
                    result = function(*args, **kwargs)
                finally:
                    sys.setprofile(previous)
                record["output"] = None if result is None else cluster_record(result, self.target_indices)
                self.trace["blobs"].append(record)
                return result

            return run

        for name, fn in originals.items():
            setattr(clustering, name, wrap(fn))
        try:
            yield
        finally:
            for name, fn in originals.items():
                setattr(clustering, name, fn)

    def _cluster(self, *args):
        with self._observe_blobs():
            return super()._cluster(*args)

    def _hanging(self, *args):
        self.trace["hanging_stage_called"] = True
        return super()._hanging(*args)
