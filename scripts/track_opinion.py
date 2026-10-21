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
# 21.10: .npy and verified .npy.zst caches (scripts/cache_extended_ride.py) alike
from cache_io import cache_file_stem, cache_files, load_cache_array  # noqa: E402

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
    name, files, piece, cfg_path, sets, cache = job[:6]
    # 21.10: negative augmentation as the X3 variants (5 Hz: every 2nd frame; random point dropout), so the
    # same structures give more false-STOP tracks; label rows of a labelled recording keep their frame ids
    every, phase, drop, seed = job[6] if len(job) > 6 else (1, 0, 0.0, 0)
    from resense.frame import frame_from_compact
    from resense.io import load_cache_stamps
    from resense.metrics import gt_objects, load_gt, match
    cfg, det = _detector(cfg_path, sets)
    stamps = load_cache_stamps(os.path.join(cache, name))
    gt = load_gt(os.path.join(ROOT, LABELS[name])) if name in LABELS else None
    prev, rows = {}, []
    for i, f in enumerate(files):
        if (i - phase) % every:
            continue
        stem = cache_file_stem(f)
        idx = int(stem.rsplit("_", 1)[1])
        arr = load_cache_array(f)
        if drop > 0:
            keep = np.random.default_rng(np.random.SeedSequence([seed, i])).random(arr.shape[0]) >= drop
            arr = arr[keep]
        fr = frame_from_compact(arr, cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
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
    (files, stamps, speeds, kind, d0, lateral, refl, seed, cfg_path, sets, place, piece, cross) = job[:13]
    move = job[13] if len(job) > 13 else 0.0     # 21.10: the object's own speed towards the train (m/s; < 0 = away)
    # 21.10: per-sequence size factors (L, W, H) and the rail placement (an object lying across a rail)
    scale = job[14] if len(job) > 14 else (1.0, 1.0, 1.0)
    on_rail = job[15] if len(job) > 15 else False
    from dataclasses import replace
    from far_range_eval import legacy_placement, placement_match
    from resense.frame import frame_from_compact
    from resense.synthetic import inject_obstacles
    cfg, det = _detector(cfg_path, sets)
    d, prev_t, prev, rows = d0, None, {}, []
    if cross:                           # a person crossing the track at |cross| m/s, from outside the corridor
        lateral = -2.0 if cross > 0 else 2.0
    for k, (f, spd) in enumerate(zip(files, speeds)):
        stem = cache_file_stem(f)
        t = stamps.get(stem)
        if prev_t is not None and t is not None:
            dt = t - prev_t
            d -= (spd + move) * (dt if 0 < dt < 10 else 0.1)
            lateral = float(np.clip(lateral + cross * (dt if 0 < dt < 10 else 0.1), -2.2, 2.2))
        prev_t = t
        if d < 8.0 or d > 260.0:
            break
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=t or 0.0, frame_id=stem)
        spec, tm = legacy_placement(fr.xyz, cfg.track, det.track, kind, d, lateral, refl, place)
        if scale != (1.0, 1.0, 1.0):
            spec = replace(spec, size=tuple(float(v * f) for v, f in zip(spec.size, scale)))
        if on_rail and kind == "railobj" and spec.base_z is not None:
            # the catalogue's railobj: across a rail, its top ~0.13 m above the rail head (doubleT_obstacle)
            spec = replace(spec, base_z=float(spec.base_z) + 0.13 - spec.size[2])
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
        allf = cache_files(nd)
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
                             a.config, a.set, place, f"syn:{fn}:{kind}{a.piece_tag}:p{piece_of[start]}",
                             float(rng.choice([-1.0, 1.0]) * a.cross) if a.cross else 0.0,
                             float(rng.uniform(*(float(v) for v in a.move.split(":")))) if ":" in a.move
                             else float(a.move),
                             tuple(float(v) for v in rng.uniform(1 - a.size_jitter, 1 + a.size_jitter, 3))
                             if a.size_jitter else (1.0, 1.0, 1.0),
                             bool(a.on_rail)))
                if a.on_rail:                   # across a rail: |lateral| 0.6-0.9 m on either side
                    j = list(jobs[-1])
                    j[5] = float(rng.choice([-1.0, 1.0]) * rng.uniform(0.6, 0.9))
                    jobs[-1] = tuple(j)
        fn_ = collect_injected
    else:
        for name in a.bag.split(","):
            files = cache_files(os.path.join(a.cache, name))
            n = a.chunks if name == "new_data" else 1
            for k, part in enumerate(np.array_split(np.array(files), n)):
                jobs.append((name, list(part), (f"{name}:{k}" if n > 1 else name) + a.piece_suffix, a.config, a.set, a.cache,
                             (a.every, a.phase, a.drop, a.seed)))
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
    return piece.split("|", 1)[0]          # 21.10: an augmented copy ("<piece>|<variant>") goes with its piece


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


def fit(X, y, a, sw=None):
    from sklearn.ensemble import GradientBoostingClassifier
    w = np.where(y == 1, 0.5 / y.mean(), 0.5 / (1 - y.mean()))          # class-balanced
    if sw is not None:                                                  # 21.10: x per-row weights (mean 1 per class)
        for c in (0, 1):
            m = y == c
            w[m] *= sw[m] / sw[m].mean()
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
    keep = [f for f in a.features.split(",") if f] or FEATURES
    unknown = [f for f in keep if f not in FEATURES]
    if unknown:
        raise SystemExit(f"unknown features {unknown}")
    cols = [i for i, f in enumerate(FEATURES) if f in keep and f not in drop]
    feats = [FEATURES[i] for i in cols]
    Xn, Pn, Mn = load(a.neg)
    Xp, Pp, Mp = load(a.pos)
    # --exclude: groups left out of everything (a fold of the cross-fitted ride measurement: the ride
    # pieces it is measured on, and the synthetic sequences injected into them, are never seen)
    excl = {g for g in a.exclude.split(",") if g}
    if excl:
        kn = np.array([ride_group(p) not in excl for p in Pn], dtype=bool)
        kp = np.array([ride_group(p) not in excl for p in Pp], dtype=bool)
        Xn, Pn, Mn, Xp, Pp, Mp = Xn[kn], Pn[kn], Mn[kn], Xp[kp], Pp[kp], Mp[kp]
    # training rows: the rows the opinion is asked about - STOP candidates by the rules beyond the near range
    tn = (Mn[:, 2] > 0) & ((Mn[:, 4] > a.near) | a.neg_all_range)
    tp = (Mp[:, 2] > 0) & (Mp[:, 4] > a.near) & (Mp[:, 6] == 1)
    X = np.concatenate([Xn[tn], Xp[tp]])[:, cols]
    y = np.r_[np.zeros(int(tn.sum())), np.ones(int(tp.sum()))].astype(int)
    names_train = np.r_[Pn[tn], Pp[tp]]
    G = np.array([ride_group(p) for p in names_train])
    rep = {"features": feats, "near": a.near, "excluded": sorted(excl), "train_rows": {"negative": int((y == 0).sum()), "positive": int(y.sum()),
                                                             "positive_sequences": len(set(Pp[tp]))},
           "groups": sorted(set(G))}
    # grouped CV: each ride piece (with the objects injected into it) / empty recording held out
    # 21.10: --seq-weight gives every positive sequence the same total weight (long sequences of one
    # easy object do not dominate); negatives keep one weight per row
    sw = None
    if a.seq_weight:
        names = np.r_[Pn[tn], Pp[tp]]
        cnt = {k: v for k, v in zip(*np.unique(names[y == 1], return_counts=True))}
        sw = np.array([1.0 / cnt[n] if yy == 1 else 1.0 for n, yy in zip(names, y)])
    oof = np.full(len(y), np.nan)
    for g in sorted(set(G)):
        te = G == g
        oof[te] = fit(X[~te], y[~te], a, None if sw is None else sw[~te]).predict_proba(X[te])[:, 1]
    rep["heldout_auc"] = round(float(roc_auc_score(y, oof)), 4)
    clf = fit(X, y, a, sw)
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
    # 21.10: augmented negatives (piece "<piece>|<variant>") train but are not counted in the replayed rows
    plain = np.array(["|" not in p for p in Pn])
    if not plain.all():
        Xn, Pn, Mn, pn, ride = Xn[plain], Pn[plain], Mn[plain], pn[plain], ride[plain]
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
    # 21.10: the chosen threshold (--pick: a factor below the highest that delays no held-out synthetic
    # sequence, rounded down to the config's 4 decimals) and what it does on held-out groups
    first = [r for r in rep["simulation"] if r["positive_quantile"] == "max_delayed"][0]
    best = first["threshold"]
    if best is not None:
        thr = float(np.floor(best * a.pick * 1e4) / 1e4)
        extra = int(a.extra.split(",")[0])
        r = simulate(Pn[ride], Mn[ride], pn[ride], thr, extra, a.near, a.sticky)
        e = simulate(Pn[~ride], Mn[~ride], pn[~ride], thr, extra, a.near, a.sticky)
        sp = simulate(Pp, Mp, pp, thr, extra, a.near, a.sticky)
        t = simulate(Pt, Mt, pt, thr, extra, a.near, a.sticky)
        rep["heldout"] = {"max_delayed_threshold": best, "pick": a.pick, "threshold": thr, "extra": extra,
                          "ride_events": [r[0], r[1]], "ride_stop_rows": [r[2], r[3]], "empty_events": [e[0], e[1]],
                          "delayed_rows_at_threshold": len(sp[4]),
                          "delayed_sequences_at_threshold": len({d[0] for d in sp[4]}),
                          "min_positive_onset_score": round(float(np.min(oof[y == 1])), 5),
                          "test_delayed_rows": len(t[4]), "test_delayed": t[4][:200]}
    if a.oof_out:
        np.savez_compressed(a.oof_out, oof=oof, y=y, G=G, names=names_train, X=X, features=np.array(feats),
                            pt=pt, Pt=Pt, Mt=Mt)
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
    c.add_argument("--move", default="0", help="m/s, or lo:hi (uniform per sequence): the object's own speed towards the train (< 0 = away)")
    c.add_argument("--piece-suffix", default="", help="21.10: recordings: e.g. '|hz5a' marks an augmented copy")
    c.add_argument("--every", type=int, default=1, help="21.10: recordings: every N-th frame (5 Hz = 2)")
    c.add_argument("--phase", type=int, default=0, help="21.10: with --every, the first frame kept")
    c.add_argument("--drop", type=float, default=0.0, help="21.10: recordings: random point dropout share (seeded by --seed)")
    c.add_argument("--size-jitter", type=float, default=0.0, help="21.10: each size factor uniform in 1 +- this, per sequence")
    c.add_argument("--on-rail", action="store_true", help="21.10: lay the objects across a rail (|lateral| 0.6-0.9 m)")
    c.add_argument("--piece-tag", default="", help="21.10: appended to the sequence name (distinguishes positive sets)")
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
    t.add_argument("--features", default="", help="21.10: the feature columns (comma-separated; default all FEATURES)")
    t.add_argument("--seq-weight", action="store_true", help="21.10: equal total weight per positive sequence")
    t.add_argument("--pick", type=float, default=0.5, help="21.10: chosen threshold = max_delayed threshold x this")
    t.add_argument("--oof-out", default="", help="21.10: out-of-fold scores and the training matrix (.npz)")
    t.add_argument("--exclude", default="", help="groups (new_data:K, a recording) left out of training and simulation")
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
