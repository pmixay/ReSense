"""Ego-speed estimation from the LiDAR stream alone (no odometry, no IMU).

Why not ICP: a straight tunnel is translation-invariant along its axis, so ICP on the lining
is degenerate in exactly the direction we need (docs/RESEARCH.md section 2). What *is*
observable is the texture of the tunnel along the track: brackets, cable hangers, lamps,
signs, cabinets, niches and column edges stick out of the walls at irregular positions and,
seen from a moving train, slide towards the sensor by ``v * dt`` per frame.

Cue 1, *profile*: per side, a 1-D histogram of returns along X in a height band above the
walkway (vertical surfaces only: horizontal ones - bed, walkway tops, platforms - are
sampled in ring stripes that are static in the sensor frame and would vote for lag 0).
The histogram is normalised by a running mean (density falls with range). Even a smooth
lining leaves a faint pattern that is fixed in the sensor frame (where the ring / column
grid lands on the curved wall), and in a featureless tunnel a moving and a stopped train
produce the same data; so a temporal background (EMA over frames) of the profile is
subtracted first: what does not move is discarded, and a featureless stretch honestly yields
"unknown" rather than a confident 0 m/s. The normalised cross-correlation between the
previous and the current residual profile is searched over ``0 .. speed_max * dt``; the peak
is refined to sub-bin accuracy by a parabola. Confidence is the peak correlation times its
prominence over the best peak further than three bins away, halved when the estimate jumps
by more than ``speed_max_step`` from the previous one. Nothing is reported during the first
``speed_warmup_frames`` frames, while the background settles.

Cue 2, *tracks*: persistent clusters (>= 3 hits) approach at the ego speed when they are
static infrastructure; the median along-track velocity of at least two of them cross-checks
cue 1 (disagreement halves the confidence) and replaces it when the profile has no texture
(three or more consistent tracks).

The result carries ``speed = None`` when neither cue reaches ``speed_min_confidence``; the
detector then does not accumulate at all rather than smear. A speed given by the caller
(odometry, a parameter) always wins over the estimate.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

from resense.config import AccumulationConfig
from resense.track import TrackModel

X_RANGE = (4.0, 25.0)      # m along the track used for the texture profile
BIN = 0.1                  # m, profile bin (one bin = 1 m/s at 10 Hz)
H_BAND = (1.3, 3.0)        # m above the rail head: walls above the walkway, below the roof
DY_BAND = (1.6, 3.5)       # m, |dy| band of the side structures (outside the advisory corridor)
SMOOTH_M = 2.0             # m, running-mean window of the density normalisation
PEAK_SEP = 3               # bins, minimum separation of the competing peak
BG_ALPHA = 0.7             # EMA weight of the static-pattern background of the profile
MIN_ENERGY = 0.02          # rms of the residual profile below which there is no texture to correlate


@dataclass
class EgoSpeedEstimate:
    speed: Optional[float]           # m/s along the track, None = unknown
    confidence: float                # 0..1
    method: str                      # 'profile' | 'tracks' | 'none'
    corr: float = 0.0                # peak normalised correlation of the profile cue
    speed_profile: Optional[float] = None
    speed_tracks: Optional[float] = None


def texture_profiles(xyz: np.ndarray, track: TrackModel) -> Tuple[np.ndarray, np.ndarray]:
    """Left / right side histograms of returns along X (``BIN`` metres, ``X_RANGE``)."""
    x0, x1 = X_RANGE
    nb = int(round((x1 - x0) / BIN))
    X = xyz[:, 0]
    sel = (X > x0) & (X < x1)
    P = xyz[sel]
    if P.shape[0] == 0:
        return np.zeros(nb), np.zeros(nb)
    Xs = P[:, 0].astype(np.float64)
    dy = P[:, 1] - track.center_y(Xs)
    h = P[:, 2] - track.rail_z(Xs)
    ady = np.abs(dy)
    side = (h > H_BAND[0]) & (h < H_BAND[1]) & (ady > DY_BAND[0]) & (ady < DY_BAND[1])
    b = np.clip(((Xs - x0) / BIN).astype(int), 0, nb - 1)
    left = np.bincount(b[side & (dy > 0)], minlength=nb).astype(np.float64)
    right = np.bincount(b[side & (dy < 0)], minlength=nb).astype(np.float64)
    return left, right


def normalise_profile(counts: np.ndarray) -> np.ndarray:
    """Relative texture: counts over their running mean, minus one, zero where there is no
    data, clipped so that one huge spike does not dominate the correlation."""
    k = max(1, int(round(SMOOTH_M / BIN)))
    kern = np.ones(2 * k + 1) / (2 * k + 1)
    mean = np.convolve(counts, kern, mode="same")
    rel = np.where(mean >= 0.5, counts / np.maximum(mean, 1e-9) - 1.0, 0.0)
    rel = np.clip(rel, -1.0, 4.0)
    ok = mean >= 0.5
    if ok.sum() >= 2:
        rel[ok] -= rel[ok].mean()
    return rel


def correlate_lags(prev: np.ndarray, cur: np.ndarray, max_lag: int) -> np.ndarray:
    """Normalised cross-correlation c[l] = <prev[i + l], cur[i]> for l = 0..max_lag.

    A structure at X in the previous frame is at X - v*dt now, so the current profile matches
    the previous one shifted towards the vehicle: cur[i] ~ prev[i + lag]."""
    n = prev.size
    out = np.full(max_lag + 1, -1.0)
    for lag in range(max_lag + 1):
        if n - lag < 20:
            break
        a, b = prev[lag:], cur[: n - lag]
        den = np.sqrt((a * a).sum() * (b * b).sum())
        out[lag] = float((a * b).sum() / den) if den > 1e-9 else 0.0
    return out


def peak_lag(c: np.ndarray) -> Tuple[float, float, float]:
    """(lag, corr, prominence) of the best correlation peak, sub-bin by parabolic fit."""
    i = int(np.argmax(c))
    cmax = float(c[i])
    lag = float(i)
    if 0 < i < c.size - 1 and c[i - 1] > -1.0 and c[i + 1] > -1.0:
        d = c[i - 1] - 2 * c[i] + c[i + 1]
        if d < -1e-9:
            lag = i + 0.5 * (c[i - 1] - c[i + 1]) / d
    others = np.array([c[j] for j in range(c.size) if abs(j - i) >= PEAK_SEP and c[j] > -1.0])
    second = float(others.max()) if others.size else 0.0
    prom = (cmax - max(second, 0.0)) / cmax if cmax > 1e-6 else 0.0
    return lag, cmax, float(np.clip(prom, 0.0, 1.0))


class EgoSpeedEstimator:
    def __init__(self, cfg: AccumulationConfig):
        self.cfg = cfg
        self._prev: Optional[Tuple[np.ndarray, np.ndarray]] = None   # previous residual profiles
        self._bg: Optional[Tuple[np.ndarray, np.ndarray]] = None     # static-pattern background
        self._n = 0                                                   # frames seen
        self.last_speed: Optional[float] = None   # last accepted (smoothed) speed, m/s

    def reset(self) -> None:
        self._prev = None
        self._bg = None
        self._n = 0
        self.last_speed = None

    # -- cue 1 ---------------------------------------------------------------
    def profile_cue(self, xyz: np.ndarray, track: TrackModel, dt: float):
        """(speed, confidence, corr) from the texture profile, or None while warming up."""
        left, right = texture_profiles(xyz, track)
        raw = (normalise_profile(left), normalise_profile(right))
        if self._bg is None:
            self._bg = raw
        else:
            self._bg = tuple(BG_ALPHA * b + (1.0 - BG_ALPHA) * r for b, r in zip(self._bg, raw))
        cur = tuple(r - b for r, b in zip(raw, self._bg))
        prev, self._prev = self._prev, cur
        self._n += 1
        if prev is None or self._n <= self.cfg.speed_warmup_frames:
            return None
        max_lag = int(np.ceil(self.cfg.speed_max * dt / BIN))
        w = np.array([left.sum(), right.sum()])
        energy = np.array([np.sqrt(np.mean(p * p)) for p in cur])
        w = np.where(energy >= MIN_ENERGY, w, 0.0)
        if w.sum() < 50:
            return 0.0, 0.0, 0.0
        c = np.zeros(max_lag + 1)
        for k in range(2):
            if w[k] <= 0:
                continue
            ck = correlate_lags(prev[k], cur[k], max_lag)
            c += (w[k] / w.sum()) * np.where(ck > -1.0, ck, 0.0)
        lag, cmax, prom = peak_lag(c)
        speed = lag * BIN / max(dt, 1e-3)
        conf = float(np.clip(cmax, 0.0, 1.0) * np.clip(prom / 0.3, 0.0, 1.0))
        return speed, conf, cmax

    # -- cue 2 ---------------------------------------------------------------
    @staticmethod
    def tracks_cue(tracks: Sequence, dt: float):
        """(speed, n) from the along-track velocity of persistent tracks, or None."""
        v = [-float(t.velocity[0]) / max(dt, 1e-3) for t in tracks
             if t.hits >= 3 and t.misses == 0 and t.last is not None]
        if len(v) < 2:
            return None
        v = np.array(v)
        med = float(np.median(v))
        if np.median(np.abs(v - med)) > 1.5:
            return None
        return med, int(v.size)

    # -- fusion --------------------------------------------------------------
    def estimate(self, xyz: np.ndarray, track: TrackModel, dt: float,
                 tracks: Sequence = ()) -> EgoSpeedEstimate:
        cfg = self.cfg
        prof = self.profile_cue(xyz, track, dt)
        trk = self.tracks_cue(tracks, dt)
        speed, conf, method, corr = None, 0.0, "none", 0.0
        sp = st = None
        if prof is not None:
            sp, conf_p, corr = prof
        if trk is not None:
            st, n_trk = trk
        if prof is not None and conf_p >= cfg.speed_min_confidence:
            speed, conf, method = sp, conf_p, "profile"
            if st is not None and abs(st - sp) > max(1.5, 0.15 * abs(sp)):
                conf *= 0.5
        elif trk is not None and n_trk >= 3:
            speed, conf, method = st, 0.6, "tracks"
        elif prof is not None:
            conf = conf_p
        if speed is not None and self.last_speed is not None and abs(speed - self.last_speed) > cfg.speed_max_step:
            conf *= 0.5
        if speed is not None and conf >= cfg.speed_min_confidence:
            if self.last_speed is not None and abs(speed - self.last_speed) <= cfg.speed_max_step:
                speed = 0.6 * speed + 0.4 * self.last_speed
            speed = float(np.clip(speed, 0.0, cfg.speed_max))
            self.last_speed = speed
        else:
            speed, method = None, "none"
        return EgoSpeedEstimate(speed=speed, confidence=float(conf), method=method, corr=float(corr),
                                speed_profile=sp, speed_tracks=st)
