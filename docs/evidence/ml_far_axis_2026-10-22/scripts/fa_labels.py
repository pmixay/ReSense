#!/usr/bin/env python3
"""Self-supervised far-axis labels: the true track centreline ahead of frame t, from the near-field rail-pair
midpoints (5-34 m) of the later frames t+1 ... t+k brought into frame t by odometry.

    fa_labels.py <extract.npz> [<extract.npz> ...] <out.npz> [--truth truth.json] [--pose-noise yaw_sd,yaw_bias]

The extraction files (fa_extract.py) must be one contiguous sequence in order. Odometry: the frame-to-frame ICP
motions, composed; a motion is *repaired* (replaced by the median of its neighbours) where it is missing, its
fitness is below 0.9, or its forward step or yaw step leaves the running median of +-5 frames by more than
max(0.15 m, 10 %) / 2 mrad; where the running median step is below 5 cm (a standing train) the
motion is the identity; a label whose chain contains more than ``max_repaired`` repaired motions is dropped.
With ``--truth`` (ray-cast scenes) the poses come from the scene's exact sensor poses instead (optionally with
added per-frame yaw noise / bias, to measure how odometry error turns into label error).

Per frame t and query distance X (resense.far_axis.QUERY_X): every later midpoint whose transformed X lies within
+-2.5 m; the label is a robust weighted line through them evaluated at X (the median with < 3 samples); n, the spread (1.4826 MAD), the chain length and the repaired
count are kept. A label is valid with n >= 3, spread <= 0.12 m and at most ``max_repaired`` repaired motions.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, ROOT)
from resense.far_axis import QUERY_X  # noqa: E402

RAIL_Z = -1.45            # approximate rail-head height in the vehicle frame (only enters through pitch / roll)


def _yaw(T):
    return float(np.arctan2(T[1, 0], T[0, 0]))


def repair(T: np.ndarray, fit: np.ndarray, win: int = 5):
    """(T repaired, repaired flags). T[k] maps frame k into frame k-1 (T[0] unused)."""
    n = len(T)
    T = T.copy()
    dx = np.array([t[0, 3] if np.isfinite(t).all() else np.nan for t in T])
    yw = np.array([_yaw(t) if np.isfinite(t).all() else np.nan for t in T])
    bad = ~np.isfinite(dx) | (fit < 0.9)
    bad[0] = False
    for _ in range(2):
        dxm = np.array([np.nanmedian(np.where(bad, np.nan, dx)[max(1, k - win):k + win + 1])
                        if np.isfinite(np.where(bad, np.nan, dx)[max(1, k - win):k + win + 1]).any() else np.nan
                        for k in range(n)])
        ywm = np.array([np.nanmedian(np.where(bad, np.nan, yw)[max(1, k - win):k + win + 1])
                        if np.isfinite(np.where(bad, np.nan, yw)[max(1, k - win):k + win + 1]).any() else np.nan
                        for k in range(n)])
        new = (np.abs(dx - dxm) > np.maximum(0.15, 0.1 * np.abs(dxm))) | (np.abs(yw - ywm) > 0.002)
        new[0] = False
        bad = bad | (new & np.isfinite(dxm))
    # a standing train does not move: where the running median step (+-5 frames) is below 5 cm the motion is the
    # identity (ICP noise would otherwise accumulate heading over a station stop of hundreds of frames)
    good_dx = np.where(bad, np.nan, dx)
    run = np.array([np.nanmedian(good_dx[max(1, k - win):k + win + 1])
                    if np.isfinite(good_dx[max(1, k - win):k + win + 1]).any() else np.nan for k in range(n)])
    still = np.isfinite(run) & (np.abs(run) < 0.05)
    still[0] = False
    for k in np.flatnonzero(still):
        T[k] = np.eye(4)
    bad = bad & ~still
    for k in np.flatnonzero(bad):
        lo, hi = max(1, k - win), min(n, k + win + 1)
        good = [j for j in range(lo, hi) if not bad[j]]
        if not good:
            T[k] = np.eye(4)
            T[k][0, 3] = np.nan
            continue
        ty = float(np.median([yw[j] for j in good]))
        R = np.eye(4)
        R[0, 0], R[0, 1], R[1, 0], R[1, 1] = np.cos(ty), -np.sin(ty), np.sin(ty), np.cos(ty)
        R[:3, 3] = np.median([T[j][:3, 3] for j in good], axis=0)
        T[k] = R
    return T, bad


def poses_from_T(T):
    """World pose of every frame (frame 0 = identity); NaN after an unrepairable motion starts a new segment."""
    P, seg, out, segs = np.eye(4), 0, [], []
    for k, t in enumerate(T):
        if k and np.isfinite(t).all():
            P = P @ t
        elif k:
            seg += 1
            P = np.eye(4)
        out.append(P.copy())
        segs.append(seg)
    return np.array(out), np.array(segs)


def _pose2(X0, Y0, h):
    P = np.eye(4)
    P[0, 0], P[0, 1], P[1, 0], P[1, 1] = np.cos(h), -np.sin(h), np.sin(h), np.cos(h)
    P[:2, 3] = [X0, Y0]
    return P


def poses_from_truth(truth, yaw_sd=0.0, yaw_bias=0.0, seed=0):
    """The scene's exact sensor poses, or with ``yaw_sd`` / ``yaw_bias`` the exact frame-to-frame motions with a
    yaw error added to each (noise + bias per frame), composed as odometry is."""
    rng = np.random.default_rng(seed)
    W = [_pose2(*f["pose"]) for f in truth["frames"]]
    P = [np.eye(4)]
    for k in range(1, len(W)):
        T = np.linalg.inv(W[k - 1]) @ W[k]
        e = rng.normal(0.0, yaw_sd) + yaw_bias if (yaw_sd or yaw_bias) else 0.0
        P.append(P[-1] @ T @ _pose2(0.0, 0.0, e))
    return np.array(P), np.zeros(len(W), dtype=int)


def build_labels(P, segs, rails, repaired, xq=QUERY_X, half=2.5, max_repaired=2, max_ahead=None):
    """(n, len(xq)) label, count, spread, chain, repaired-in-chain."""
    n = len(P)
    nq = len(xq)
    lab = np.full((n, nq), np.nan)
    cnt = np.zeros((n, nq), dtype=np.int32)
    spr = np.full((n, nq), np.nan)
    chain = np.zeros((n, nq), dtype=np.int32)
    rep = np.zeros((n, nq), dtype=np.int32)
    xmax = float(np.max(xq)) + half
    # rails of every frame as homogeneous points in its own frame
    R = [r[np.isfinite(r[:, 0])] for r in rails]
    for t in range(n):
        Pinv = np.linalg.inv(P[t])
        xs, ys, ws, js = [], [], [], []
        for j in range(t + 1, n):
            if segs[j] != segs[t]:
                break
            M = Pinv @ P[j]
            if M[0, 3] > xmax:
                break
            r = R[j]
            if not len(r):
                continue
            p = M[:3, :3] @ np.stack([r[:, 0], r[:, 1], np.full(len(r), RAIL_Z)]) + M[:3, 3:4]
            xs.append(p[0]); ys.append(p[1]); ws.append(r[:, 2]); js.append(np.full(len(r), j))
        if not xs:
            continue
        xs, ys, ws, js = map(np.concatenate, (xs, ys, ws, js))
        crep = np.cumsum(repaired[t + 1:]) if t + 1 < n else np.zeros(0)
        for i, x in enumerate(xq):
            m = np.abs(xs - x) <= half
            if m.sum() == 0:
                continue
            x_, y, w = xs[m] - x, ys[m], ws[m]
            if m.sum() >= 3 and np.ptp(x_) > 1.0:
                # local line through the samples (the track's slope across the window), one robust reweighting
                A = np.stack([np.ones_like(x_), x_], 1)
                sol = np.linalg.lstsq(A * w[:, None], y * w, rcond=None)[0]
                r = y - A @ sol
                s_ = 1.4826 * np.median(np.abs(r)) + 0.01
                w2 = w / (1.0 + (r / (2.5 * s_)) ** 2)
                sol = np.linalg.lstsq(A * w2[:, None], y * w2, rcond=None)[0]
                med, res = float(sol[0]), y - A @ sol
            else:
                o = np.argsort(y)
                cw = np.cumsum(w[o])
                med = float(y[o][np.searchsorted(cw, 0.5 * cw[-1])])
                res = y - med
            lab[t, i] = med
            cnt[t, i] = int(m.sum())
            spr[t, i] = float(1.4826 * np.median(np.abs(res)))
            jmax = int(js[m].max())
            chain[t, i] = jmax - t
            rep[t, i] = int(crep[jmax - t - 1]) if jmax - t - 1 < crep.size else 0
    valid = (cnt >= 3) & (spr <= 0.12) & (rep <= max_repaired)
    return lab, cnt, spr, chain, rep, valid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--truth", default="")
    ap.add_argument("--pose-noise", default="", help="yaw_sd,yaw_bias (rad per frame), with --truth")
    ap.add_argument("--max-repaired", type=int, default=2)
    ap.add_argument("--gap-break", type=float, default=0.0,
                    help="post-hoc fix (found 22.10 after the registered measurement): a stamp gap longer than this (s) "
                         "ends the odometry segment (the motion across a recording dropout is unknown); 0 = off, the "
                         "registered behaviour")
    a = ap.parse_args()
    *ins, out = a.files
    D = [np.load(f, allow_pickle=False) for f in ins]
    # consecutive pieces overlap by one frame (its ICP to the previous frame comes from the earlier piece; the later
    # piece's next motion is relative to the same physical frame): keep the first occurrence
    keep = []
    seen = set()
    for d in D:
        k = np.array([str(n) not in seen for n in d["names"]])
        seen.update(str(n) for n in d["names"])
        keep.append(k)
    names = np.concatenate([d["names"][k] for d, k in zip(D, keep)])
    rails_l = [r for d, k in zip(D, keep) for r in d["rails"][k]]
    if a.truth:
        truth = json.load(open(a.truth))
        sd, bias = (float(v) for v in a.pose_noise.split(",")) if a.pose_noise else (0.0, 0.0)
        P, segs = poses_from_truth(truth, sd, bias)
        repaired = np.zeros(len(P), dtype=bool)
    else:
        T = np.concatenate([d["T"][k] for d, k in zip(D, keep)])
        fit = np.concatenate([d["fitness"][k] for d, k in zip(D, keep)])
        T, repaired = repair(T, fit)
        if a.gap_break > 0:
            st = np.concatenate([d["stamps"][k] for d, k in zip(D, keep)])
            gap = np.r_[False, np.diff(st) > a.gap_break]
            T[gap] = np.nan                     # poses_from_T starts a new segment there
            print("segment breaks at stamp gaps:", int(gap.sum()))
        P, segs = poses_from_T(T)
    lab, cnt, spr, chain, rep, valid = build_labels(P, segs, rails_l, repaired, max_repaired=a.max_repaired)
    np.savez_compressed(out, names=names, label=lab, count=cnt, spread=spr, chain=chain, repaired_in_chain=rep,
                        valid=valid, repaired=repaired, poses=P, segs=segs, query_x=QUERY_X)
    print(out, len(names), "frames; valid labels per query X:",
          dict(zip(QUERY_X.astype(int).tolist(), valid.sum(0).tolist())), "; repaired motions", int(repaired.sum()))


if __name__ == "__main__":
    main()
