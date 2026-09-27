#!/usr/bin/env python3
"""Track-level learned second opinion (27.09, P2 ride): dataset, grouped validation, export.

``collect`` runs the detector over cached recordings (fresh detector per piece, as the regression
gate) with the tracker's observation record on and writes one row per matched track per frame:
the features of ``resense/opinion.py`` plus whether the track is a STOP by the rules, whether this
frame is a STOP onset, its cluster's distance / lateral and a label:

* obstacle-free recordings (the ride in the gate's 8 pieces, the five empty bags): every row 0;
* labelled recordings (``cloud_with_fake_obj`` = set O, ``doubleT_obstacle``): 1 when the cluster
  matches an in-envelope object of the frame (``resense.metrics.match``), -1 outside objects, 0 else;
* ``--inject KIND,...``: objects ray-cast into consecutive ride frames (``scripts/far_range_eval.py``
  legacy placement, the ride's speeds): 1 when the cluster matches the placement, rows of other
  tracks are dropped (the ride rows are the negatives).

``train`` fits a small gradient-boosted tree ensemble on onset-relevant rows (STOP candidates) of
the training groups only and reports grouped held-out results: leave-one-ride-piece-out for the
negatives, synthetic sequences split by ride piece, and set O / doubleT_obstacle never trained on.
``--export`` writes the JSON model read by ``resense.opinion.TrackOpinion``.

    python scripts/track_opinion.py collect --bag new_data --out /data/work/p2ride_tmp/ride.npz
    python scripts/track_opinion.py collect --inject person,box0.5 --files 30,120 --out syn.npz
    python scripts/track_opinion.py train --neg ride.npz empty.npz --pos syn.npz --test setO.npz dto.npz \\
        --export resense/models/track_opinion.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

LABELS = {"cloud_with_fake_obj": "labels/cloud_with_fake_obj.json", "doubleT_obstacle": "labels/doubleT_obstacle.json"}
SIX = ("doubleT_obstacle", "doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
       "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
META = ["piece", "frame", "track", "stop", "onset", "dist", "lat", "label"]


def _detector(cfg_path, sets):
    import eval_real
    from resense.detector import Detector
    cfg = eval_real.load_cfg(cfg_path, sets)
    det = Detector(cfg)
    det.tracker.record = True
    return cfg, det


def _rows(det, piece, frame, prev_stop, label_fn):
    from resense.opinion import track_features
    out = []
    for t in det.tracker.tracks:
        stop = bool(t.reported and t.rule_zone == "gauge")
        was = prev_stop.get(t.id, False)
        prev_stop[t.id] = bool(t.reported and t.zone == "gauge")
        if t.misses or not t.obs or t.last is None:
            continue
        lab = label_fn(t.last)
        if lab is None:
            continue
        f = track_features(t.obs, t.hits, t.hit_fraction)
        out.append((f, [piece, frame, t.id, float(stop), float(stop and not was), t.last.distance,
                        t.last.lateral, lab]))
    return out


def collect_recording(job):
    name, files, piece, cfg_path, sets, cache = job
    from resense.frame import frame_from_compact
    from resense.io import load_cache_stamps
    from resense.metrics import gt_objects, load_gt, match
    cfg, det = _detector(cfg_path, sets)
    stamps = load_cache_stamps(os.path.join(cache, name))
    gt = load_gt(os.path.join(ROOT, LABELS[name])) if name in LABELS else None
    prev, rows = {}, []
    for i, f in enumerate(files):
        stem = os.path.splitext(os.path.basename(f))[0]
        idx = int(stem.rsplit("_", 1)[1])
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        det.process(fr)
        frame = idx if name in SIX else i
        if gt is None:
            def lab(cl):
                return 0
        else:
            objs = gt_objects(gt.get(f"{frame:05d}", []))

            def lab(cl):
                for g in objs:
                    if match(cl.distance, cl.lateral, g):
                        return 1 if g.in_gauge else -1
                return 0
        rows += _rows(det, piece, frame, prev, lab)
    return rows


def collect_injected(job):
    (files, stamps, speeds, kind, d0, lateral, refl, seed, cfg_path, sets, place, piece, cross) = job
    from far_range_eval import legacy_placement, placement_match
    from resense.frame import frame_from_compact
    from resense.synthetic import inject_obstacles
    cfg, det = _detector(cfg_path, sets)
    d, prev_t, prev, rows = d0, None, {}, []
    if cross:                           # a person crossing the track at |cross| m/s, from outside the corridor
        lateral = -2.0 if cross > 0 else 2.0
    for k, (f, spd) in enumerate(zip(files, speeds)):
        stem = os.path.splitext(os.path.basename(f))[0]
        t = stamps.get(stem)
        if prev_t is not None and t is not None:
            dt = t - prev_t
            d -= spd * (dt if 0 < dt < 10 else 0.1)
            lateral = float(np.clip(lateral + cross * (dt if 0 < dt < 10 else 0.1), -2.2, 2.2))
        prev_t = t
        if d < 8.0:
            break
        fr = frame_from_compact(np.load(f), cfg.sensor, stamp=t or 0.0, frame_id=stem)
        spec, tm = legacy_placement(fr.xyz, cfg.track, det.track, kind, d, lateral, refl, place)
        rng = np.random.default_rng(np.random.SeedSequence([seed, k, 1]))
        inj = inject_obstacles(fr, tm, [spec], rng=rng, dropout_start=60.0, dropout_full=200.0)
        det.process(inj.frame)

        def lab(cl, spec=spec, tm=tm):
            return 1 if placement_match(cl, spec.distance, spec, tm, det.track, "legacy") else None
        rows += _rows(det, piece, k, prev, lab)
    return rows


def cmd_collect(a):
    from concurrent.futures import ProcessPoolExecutor
    from resense.io import _natural_key, load_cache_stamps
    jobs = []
    if a.inject:
        from resense.synthetic import OBJECT_CATALOGUE
        nd = os.path.join(a.cache, "new_data")
        stamps = load_cache_stamps(nd)
        allf = sorted(glob.glob(os.path.join(nd, "*.npy")), key=_natural_key)
        pieces = np.array_split(np.arange(len(allf)), 8)
        piece_of = np.zeros(len(allf), dtype=int)
        for k, p in enumerate(pieces):
            piece_of[p] = k
        intake = json.load(open(os.path.join(ROOT, "docs/extended_dataset_intake.json")))
        spd = {f["n"]: (f.get("speed_tracks") or 0.0) for f in intake["files"]}
        rng = np.random.default_rng(a.seed)
        lo, hi = (float(v) for v in a.lateral.split(":"))
        from far_range_eval import consecutive_files
        for fn in [int(v) for v in a.files.split(",") if v]:
            start = next(i for i, f in enumerate(allf) if os.path.basename(f).startswith(f"new_data_{fn}_"))
            files = consecutive_files(allf, start, a.frames)
            speeds = [spd.get(int(os.path.basename(f).split("_")[2]), 0.0) for f in files]
            for kind in a.inject.split(","):
                place = "rail" if kind in ("lowbox", "railobj") else "bed"
                d0 = float(rng.uniform(*(float(v) for v in a.start.split(":")))) if ":" in a.start else float(a.start)
                jobs.append((files, stamps, speeds, kind, d0, float(rng.uniform(lo, hi)),
                             float(rng.uniform(*OBJECT_CATALOGUE[kind].reflectivity)), int(rng.integers(1 << 30)),
                             a.config, a.set, place, f"syn:{fn}:{kind}:p{piece_of[start]}",
                             float(rng.choice([-1.0, 1.0]) * a.cross) if a.cross else 0.0))
        fn_ = collect_injected
    else:
        for name in a.bag.split(","):
            files = sorted(glob.glob(os.path.join(a.cache, name, "*.npy")), key=_natural_key)
            n = a.chunks if name == "new_data" else 1
            for k, part in enumerate(np.array_split(np.array(files), n)):
                jobs.append((name, list(part), f"{name}:{k}" if n > 1 else name, a.config, a.set, a.cache))
        fn_ = collect_recording
    rows = []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        for r in ex.map(fn_, jobs):
            rows += r
    X = np.array([r[0] for r in rows], dtype=np.float32).reshape(-1, len(_features()))
    meta = [r[1] for r in rows]
    np.savez_compressed(a.out, X=X, piece=np.array([m[0] for m in meta]),
                        M=np.array([m[1:] for m in meta], dtype=np.float64), features=np.array(_features()))
    print(f"{len(rows)} rows ({int(sum(m[-1] == 1 for m in meta))} positive) -> {a.out}")


def _features():
    from resense.opinion import FEATURES
    return FEATURES


# ------------------------------------------------------------------------------------------------
def load(paths):
    Xs, Ps, Ms = [], [], []
    for p in paths:
        z = np.load(p, allow_pickle=False)
        Xs.append(z["X"])
        Ps.append(z["piece"].astype(str))
        Ms.append(z["M"])
    return np.concatenate(Xs), np.concatenate(Ps), np.concatenate(Ms)


def ride_group(piece: str) -> str:
    """The held-out group of a row: the ride piece (a synthetic sequence goes with the ride piece it
    was injected into), else the recording."""
    if piece.startswith("syn:"):
        return "new_data:" + piece.rsplit(":p", 1)[1]
    return piece


def export_gbm(clf, features) -> dict:
    trees = []
    for est in clf.estimators_[:, 0]:
        t = est.tree_
        trees.append({"feature": t.feature.tolist(), "threshold": [float(v) for v in t.threshold],
                      "left": t.children_left.tolist(), "right": t.children_right.tolist(),
                      "value": [float(v) for v in t.value[:, 0, 0]]})
    init = clf.init_.class_prior_[1] if hasattr(clf.init_, "class_prior_") else None
    p = float(init) if init is not None else float(clf._raw_predict_init(np.zeros((1, len(features))))[0, 0])
    f0 = float(np.log(p / (1 - p))) if init is not None else p
    return {"features": list(features), "init": f0, "learning_rate": float(clf.learning_rate), "trees": trees}


def fit(X, y, a):
    from sklearn.ensemble import GradientBoostingClassifier
    w = np.where(y == 1, 0.5 / y.mean(), 0.5 / (1 - y.mean()))          # class-balanced
    clf = GradientBoostingClassifier(n_estimators=a.trees, max_depth=a.depth, learning_rate=a.lr,
                                     subsample=0.8, min_samples_leaf=a.min_leaf, random_state=0)
    return clf.fit(X, y, sample_weight=w)


def simulate(P, M, p, thr, extra, near, sticky=False):
    """The doubt rule (``Tracker._doubt``) replayed on collected rows (the rules' STOP flags of the
    run without it; a withheld track also loses the keep rules, so this is an upper bound of what
    stays). Returns (events, events kept, STOP rows, STOP rows kept, delayed positive rows)."""
    ev, kept, fr, fk, delayed = set(), set(), 0, 0, []
    state = {}
    for i in np.lexsort((M[:, 0], M[:, 1], P)):              # piece, track, frame
        key = (P[i], int(M[i, 1]))
        stop, d = M[i, 2] > 0, M[i, 4]
        w, doubt, sp = state.get(key, (False, 0, False))
        if not stop:
            w, doubt = False, 0
        elif sp and not w and not M[i, 3] > 0:           # a STOP already (an onset of the run is one here too)
            pass
        elif d <= near or (p[i] >= thr and not (sticky and w)):
            w = False
        else:
            doubt += 1
            w = doubt <= extra
        state[key] = (w, doubt, stop and not w)
        if stop:
            ev.add(key)
            fr += 1
        if stop and not w:
            kept.add(key)
            fk += 1
        if stop and w and M[i, 6] == 1:
            delayed.append((str(P[i]), int(M[i, 0]), round(float(d), 1), round(float(p[i]), 3)))
    return len(ev), len(kept), fr, fk, delayed


def cmd_train(a):
    from sklearn.metrics import roc_auc_score
    from resense.opinion import FEATURES, TrackOpinion
    drop = [f for f in a.drop.split(",") if f]
    cols = [i for i, f in enumerate(FEATURES) if f not in drop]
    feats = [FEATURES[i] for i in cols]
    Xn, Pn, Mn = load(a.neg)
    Xp, Pp, Mp = load(a.pos)
    # training rows: the rows the opinion is asked about - STOP candidates by the rules beyond the near range
    tn = (Mn[:, 2] > 0) & ((Mn[:, 4] > a.near) | a.neg_all_range)
    tp = (Mp[:, 2] > 0) & (Mp[:, 4] > a.near) & (Mp[:, 6] == 1)
    X = np.concatenate([Xn[tn], Xp[tp]])[:, cols]
    y = np.r_[np.zeros(int(tn.sum())), np.ones(int(tp.sum()))].astype(int)
    G = np.array([ride_group(p) for p in np.r_[Pn[tn], Pp[tp]]])
    rep = {"features": feats, "near": a.near, "train_rows": {"negative": int((y == 0).sum()), "positive": int(y.sum()),
                                                             "positive_sequences": len(set(Pp[tp]))},
           "groups": sorted(set(G))}
    # grouped CV: each ride piece (with the objects injected into it) / empty recording held out
    oof = np.full(len(y), np.nan)
    for g in sorted(set(G)):
        te = G == g
        oof[te] = fit(X[~te], y[~te], a).predict_proba(X[te])[:, 1]
    rep["heldout_auc"] = round(float(roc_auc_score(y, oof)), 4)
    clf = fit(X, y, a)
    spec = export_gbm(clf, feats)
    op = TrackOpinion(spec)
    Xf = np.zeros((min(300, len(y)), len(FEATURES)))
    Xf[:, cols] = X[:len(Xf)]
    rep["export_max_abs_diff"] = float(max(abs(op.prob(Xf[i]) - clf.predict_proba(X[i:i + 1])[0, 1])
                                           for i in range(len(Xf))))
    pn = np.ones(len(Xn))
    pn[tn] = oof[:int(tn.sum())]
    pp = np.ones(len(Xp))
    pp[tp] = oof[int(tn.sum()):]
    Xt, Pt, Mt = load(a.test) if a.test else (np.zeros((0, len(FEATURES))), np.zeros(0, str), np.zeros((0, 8)))
    pt = np.array([op.prob(x) for x in Xt])
    ride = np.array([p.startswith("new_data") for p in Pn])
    rep["simulation"] = []
    for extra in [int(v) for v in a.extra.split(",")]:
        # the threshold: the highest at which at most --max-delayed synthetic sequences (held out) would
        # be delayed by the rule; then the quantiles of the positive rows for comparison
        best = None
        for thr in np.unique(oof[y == 1]):
            if len({d[0] for d in simulate(Pp, Mp, pp, thr, extra, a.near, a.sticky)[4]}) > a.max_delayed:
                break
            best = float(np.floor(thr * 1e4) / 1e4)        # rounded down: the config value
        thrs = [("max_delayed", best)] + [(q, float(np.quantile(oof[y == 1], q))) for q in
                                          [float(v) for v in a.quantiles.split(",") if v]]
        # a safety margin below the highest threshold that delays no held-out synthetic sequence: the
        # lowest held-out positive onset score is then at least 1 / factor times the threshold
        if best is not None:
            thrs += [(f"max_delayed_x{f:g}", float(np.floor(best * f * 1e4) / 1e4))
                     for f in [float(v) for v in a.margin.split(",") if v]]
        for q, thr in thrs:
            r = simulate(Pn[ride], Mn[ride], pn[ride], thr, extra, a.near, a.sticky)
            e = simulate(Pn[~ride], Mn[~ride], pn[~ride], thr, extra, a.near, a.sticky)
            s = simulate(Pp, Mp, pp, thr, extra, a.near, a.sticky)
            t = simulate(Pt, Mt, pt, thr, extra, a.near, a.sticky)
            rep["simulation"].append({
                "extra": extra, "sticky": a.sticky, "positive_quantile": q, "threshold": round(thr, 4),
                "ride_events": [r[0], r[1]], "ride_stop_rows": [r[2], r[3]], "empty_events": [e[0], e[1]],
                "synthetic_delayed_rows": len(s[4]), "synthetic_delayed_sequences": len({d[0] for d in s[4]}),
                "test_delayed": t[4]})
    rep["importance"] = {f: round(float(v), 3) for f, v in sorted(zip(feats, clf.feature_importances_),
                                                                   key=lambda t: -t[1])}
    print(json.dumps(rep, indent=1))
    if a.export:
        with open(a.export, "w", encoding="utf-8") as fh:
            json.dump(spec, fh, separators=(",", ":"))
        print(f"model -> {a.export} ({os.path.getsize(a.export)} bytes)")
    if a.report:
        with open(a.report, "w", encoding="utf-8") as fh:
            json.dump(rep, fh, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--cache", default="/data/cache")
    c.add_argument("--bag", default="new_data")
    c.add_argument("--chunks", type=int, default=8)
    c.add_argument("--inject", default="")
    c.add_argument("--files", default="30,120,150,190,200,210")
    c.add_argument("--start", default="200", help="object distance at the first frame (m), or lo:hi (uniform per sequence)")
    c.add_argument("--frames", type=int, default=110)
    c.add_argument("--lateral", default="-0.8:0.8")
    c.add_argument("--seed", type=int, default=1)
    c.add_argument("--cross", type=float, default=0.0, help="m/s: the objects cross the track laterally (a walking person)")
    c.add_argument("--config", default=os.path.join(ROOT, "configs/default.yaml"))
    c.add_argument("--set", action="append", default=[])
    c.add_argument("--jobs", type=int, default=1)
    c.add_argument("--out", required=True)
    t = sub.add_parser("train")
    t.add_argument("--neg", nargs="+", required=True, help="obstacle-free collections (ride pieces, empty bags)")
    t.add_argument("--pos", nargs="+", required=True, help="synthetic injection collections")
    t.add_argument("--test", nargs="*", default=[], help="held-out labelled collections (set O, doubleT_obstacle)")
    t.add_argument("--extra", default="1,2,3")
    t.add_argument("--quantiles", default="0.005,0.01,0.02")
    t.add_argument("--sticky", action="store_true", help="simulate tracking.doubt_sticky")
    t.add_argument("--max-delayed", type=int, default=0, help="synthetic sequences the chosen threshold may delay")
    t.add_argument("--margin", default="0.5,0.33", help="also report the max-delayed threshold times these factors")
    t.add_argument("--neg-all-range", action="store_true", help="negatives: STOP rows at every range (not only beyond --near)")
    t.add_argument("--near", type=float, default=30.0)
    t.add_argument("--drop", default="")
    t.add_argument("--trees", type=int, default=60)
    t.add_argument("--depth", type=int, default=3)
    t.add_argument("--lr", type=float, default=0.1)
    t.add_argument("--min-leaf", type=int, default=20)
    t.add_argument("--export", default="")
    t.add_argument("--report", default="")
    a = ap.parse_args()
    (cmd_collect if a.cmd == "collect" else cmd_train)(a)


if __name__ == "__main__":
    main()
