"""Temporal persistence: a light multi-object tracker in the vehicle frame.

Without odometry a static obstacle moves towards the vehicle by v*dt per frame, so the
association gate is widened by ``ego_speed_max * frame_dt`` along X. Confidence grows
with consecutive hits and decays with misses; only confirmed tracks are reported.

Persistence (v0.5) is measured in *time*, not only in processed frames: a track is
confirmed when it has ``confirm_hits`` hits, it has been observed for at least
``confirm_time_s`` of sensor time (frames x the frame interval the caller passes to
:meth:`Tracker.update`, the first frame included, so 0.3 s = 3 frames at 10 Hz and 3 frames
at any lower rate too; a caller that never passes an interval gets hit counting only), it
was matched in at least ``min_hit_fraction`` of its last ``hit_window`` frames, and it is
matched now. Its zone is 'gauge' when at least ``zone_min_fraction`` of its last
``zone_window`` hits were inside the strict gauge, so a corridor-edge structure that
flickers into the gauge every other frame is advisory (docs/EXPERIMENTS.md section 1b), and
fewer than ``column_hold`` (2 since 25.09) of those hits were demoted as a column: a column far
away shows more than ``column_min_height`` of itself in some frames only (EXPERIMENTS.md 3a).
With ``low_min_seen_distance`` > 0 (tried 26.09, off: EXPERIMENTS.md 1j) a low (bed-level) track
is reported only once it has been matched at or beyond it; 4 m never reports a low object that
stays nearer (a standing train), so it is not shipped.
With ``near_escalate_voxels`` N > 0 (on since 26.09, N 10, EXPERIMENTS.md 1l) a track whose last
``near_escalate_hits`` hits were each a corridor cluster with at least N voxels inside the strict
envelope within ``near_escalate_distance`` is zone 'gauge' whatever demoted it (a signature such
as ``elevated`` or ``floating``, the zone vote); a column never counts and the column hold wins.
With ``stop_keep_signature`` (26.09, P3 range, off: EXPERIMENTS.md 1o) a track reported as an
obstacle in the previous frame counts a hit whose cluster is inside the gauge by its voxels but
demoted only by a shape signature (``Cluster.demoted``) as inside the gauge. With
``stop_keep_thin`` 1 such a track, unmatched otherwise, may be continued by a cluster flatter than
``cluster.min_height`` (``Cluster.thin``: one scan line) inside the gauge; with 2 also a track not
yet reported whose previous hit was an obstacle cluster inside the gauge. None of them starts a
track.
With ``thin_far_min_distance`` > 0 (27.09, P5 range, on at 60 m) far scan lines inside the
gauge (and with ``cluster.weak_min_points`` far clusters under the point-count bar) may start and
continue tracks; while the gauge vote of a track needs such hits, the track becomes an obstacle
(STOP) only while its distances lie on a line in sensor time that approaches (``approach_*``) and
is reported as advisory otherwise, never hidden: a scan line of the bed or the vault is fixed in
the sensor frame or jumps with the pitch, a static object ahead approaches at the train's speed.
A track whose clean hits alone vote gauge, and a STOP in the previous frame, keep the usual rules.

The opt-in ``fresh_stop_evidence`` candidate adds a provenance check only at a new STOP onset.
Its bounded recent matched-hit record must contain the configured number of ordinary/low or
approaching ``far_thin`` gauge hits, and the hit on the onset frame must itself be strict gauge
evidence. A thin continuation hit and an off-gauge hit therefore cannot start a new STOP from an
old zone vote. An already reported gauge STOP is not checked by this candidate, so the existing
miss/occlusion and stop-keep behaviour remains responsible for continuation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from resense.clustering import Cluster
from resense.config import TrackingConfig
from resense.opinion import OBS_KEEP, load_opinion, observation, track_features


# 26.09: demotions a near escalation never overrides (Tracker._near): a column, and a cluster outside
# the range where the corridor's axis or height reference is trusted
_NOT_ESCALATED = ("column", "beyond_axis", "beyond_height_ref")


@dataclass
class Track:
    id: int
    centroid: np.ndarray
    velocity: np.ndarray            # (3,) m/frame, estimated from consecutive matches
    hits: int = 1
    misses: int = 0
    age: int = 1
    confidence: float = 0.0
    last: Optional[Cluster] = None
    history: List[float] = field(default_factory=list)  # distances

    gauge_hits: int = 0             # frames in which the cluster was inside the strict gauge
    zone_hist: List[bool] = field(default_factory=list)   # last zone_window hits: inside strict gauge?
    hit_hist: List[bool] = field(default_factory=list)    # last hit_window frames: matched?
    span_s: float = 0.0             # seconds of sensor time the track has been observed (frames x interval, first frame included)
    zone_min_fraction: float = 0.5  # share of zone_hist that must be inside the gauge
    zone_min_votes: int = 0         # 27.09 (tracking.zone_min_votes): the vote counts at least this many hits (0 = off)
    reported: bool = False          # reported as an obstacle / advisory after the last update
    column_hist: List[bool] = field(default_factory=list)  # last zone_window hits: demoted as a column?
    column_hold: int = 0            # this many column hits in column_hist keep the track advisory (0 = off)
    hold: int = 0                   # 26.09: frames left of a calibration re-seed hold window (Tracker.reseed)
    seen_reported: bool = False     # 26.09: reported in the frame of its last match (health.clear_cap_lost)
    kept: bool = False              # 26.09 (stop_keep_*): the last hit kept a reported obstacle only by the keep rules
    since_clean: float = 0.0        # 26.09 (stop_keep_max_s): s of sensor time since the last clean hit (an obstacle cluster inside the gauge, not a scan line; inf = none yet)
    near_hist: List[bool] = field(default_factory=list)  # 26.09: last near_hits hits: near the envelope (Tracker._near)?
    near_hits: int = 0              # 26.09: this many near hits in a row make the track an obstacle (0 = off)
    obs: List[tuple] = field(default_factory=list)  # 27.09 (tracking.doubt_*): the last matched clusters (opinion.observation)
    doubt: int = 0                  # 27.09: frames a doubtful STOP was withheld over the track's life (tracking.doubt_extra_hits)
    withheld: bool = False          # 27.09: a STOP withheld as advisory by the track opinion (zone 'warning')
    stop_prev: bool = False         # 27.09: reported in zone gauge after the previous update
    thin_hist: List[bool] = field(default_factory=list)  # 27.09 (thin_far_min_distance): last zone_window hits: a far scan line?
    approach: List[tuple] = field(default_factory=list)  # 27.09: (sensor time s, distance m) of the last hits (approach_*)
    far_evidence: bool = False      # 27.09: the track was ever matched by a far scan line / weak far cluster (thin_far_min_distance)
    was_stop: bool = False          # 27.09: reported in zone gauge (a STOP) after the previous update (thin_far_min_distance only)
    approach_block: bool = False    # 27.09: far evidence without an approach holds a reported advisory track advisory (zone)
    evidence_hist: List[str] = field(default_factory=list)  # opt-in fresh_stop_evidence: recent hit provenance
    stop_earned: bool = False       # opt-in onset gate: a gauge STOP was actually earned, not merely reported advisory
    fresh_blocked: bool = False     # opt-in: a reported advisory cannot become a STOP on this hit
    low_clean: Optional[Cluster] = None  # last clean low cluster; weak continuation cannot change this shape reference
    low_since_clean: float = 0.0  # actual elapsed time, including stamp gaps clipped for the existing motion/fit rules
    explained_hist: List[bool] = field(default_factory=list)  # 29.09 (explained_run): last hits demoted with a reason?
    clean_run: int = 0              # 29.09 (explained_run): consecutive clean strict-gauge hits, broken by a miss
    odo: List[tuple] = field(default_factory=list)  # 29.09 (ego_veto_*): (odometry segment, train travel m, distance m) of the last hits

    @property
    def near_escalated(self) -> bool:
        """26.09 (``tracking.near_escalate_voxels``): the last ``near_hits`` hits of the track were
        all near the envelope (``Tracker._near``)."""
        k = self.near_hits
        return k > 0 and len(self.near_hist) >= k and all(self.near_hist[-k:])

    @property
    def column_held(self) -> bool:
        return self.column_hold > 0 and sum(self.column_hist) >= self.column_hold

    @property
    def vote_zone(self) -> str:
        """'gauge' when at least ``zone_min_fraction`` of the last hits were inside the strict gauge."""
        n = max(len(self.zone_hist), self.zone_min_votes)
        return "gauge" if sum(self.zone_hist) >= self.zone_min_fraction * n - 1e-9 else "warning"

    @property
    def zone(self) -> str:
        if self.withheld or self.fresh_blocked:
            return "warning"
        return self.rule_zone

    @property
    def rule_zone(self) -> str:
        """The zone by the persistence rules (``zone`` without the track opinion's withholding)."""
        if not self.zone_hist or self.column_held or self.approach_block:
            return "warning"
        if self.near_escalated:
            return "gauge"
        return self.vote_zone

    @property
    def escalated(self) -> bool:
        """An obstacle only by the near escalation (its vote says advisory)."""
        return (self.near_escalated and bool(self.zone_hist) and not self.column_held
                and self.vote_zone != "gauge")

    @property
    def hit_fraction(self) -> float:
        return (sum(self.hit_hist) / len(self.hit_hist)) if self.hit_hist else 1.0


class Tracker:
    def __init__(self, cfg: TrackingConfig):
        self.cfg = cfg
        self.tracks: List[Track] = []
        self._next_id = 1
        self._timed = False          # a frame interval was supplied at least once
        # 27.09 (tracking.doubt_*): the track opinion and the observation record it reads
        self.opinion = load_opinion(cfg.doubt_model) if cfg.doubt_extra_hits > 0 else None
        self.record = self.opinion is not None
        self._clock = 0.0            # 27.09: s of sensor time since the start (approach_*)
        self._odo_x, self._odo_seg, self._odo_v = 0.0, 0, None   # 29.09 (ego_veto_*): train travel, segment, speed

    def reset(self) -> None:
        self.tracks.clear()
        self._odo_x, self._odo_seg, self._odo_v = 0.0, self._odo_seg + 1, None
        self._next_id = 1
        self._timed = False

    def reseed(self, dR: np.ndarray, hold: int, keep_unreported: bool = True) -> None:
        """A mount-calibration change rotated the cloud by ``dR`` (``p_new = dR @ p_old``; 26.09,
        ``tracking.reseed_hold``): every track's position and velocity are rotated with it; unless
        ``keep_unreported`` (a large tilt change) only the tracks reported in zone gauge (STOPs)
        are kept, the others are dropped as the reset did before (their history, zone votes
        included, was taken in a wrong frame: an object reported as advisory under a 3 deg tilt
        kept its advisory vote 3 frames after the correction at 5 Hz); and a track reported in zone
        gauge is held for a fixed window of ``hold`` frames from the change, the change frame the
        first (from its last match when it was already missing at the change): it stays reported
        in the window matched or not - a match refreshes it but does not end the window (re-review
        26.09: it did, so a loss starting on the frame after the change was not covered) - its
        misses there neither decay its confidence nor enter its hit history, and a missed frame
        reports it at its predicted position. Repeated re-seeds do not extend the hold of a track
        that stays unmatched. The re-seeded geometry (a fresh track model has no floor-shadow
        reference for its warm-up) must not drop a confirmed STOP."""
        dR = np.asarray(dR, dtype=np.float64)
        if not keep_unreported:
            self.tracks = [t for t in self.tracks if t.reported and t.zone == "gauge"]
        for t in self.tracks:
            t.centroid = dR @ t.centroid
            t.velocity = dR @ t.velocity
            if t.reported and t.zone == "gauge":
                t.hold = max(t.hold, int(hold) - t.misses)

    def _near(self, cl: Cluster) -> bool:
        """26.09 (``tracking.near_escalate_voxels`` > 0): a corridor cluster with at least that many
        voxels inside the strict envelope (``Cluster.n_gauge``, edge margin applied) and within
        ``near_escalate_distance``, whatever its zone or demotion reason except a column (a column
        row seen through a wrong axis at a crossover has 50-150 such voxels at 20-40 m on the ride;
        the column hold keeps precedence too) and a cluster demoted because the corridor's axis or
        height reference is not trusted there (``beyond_axis``, ``beyond_height_ref``; safety review
        of 26.09: its strict voxels are not trusted either)."""
        c = self.cfg
        return (c.near_escalate_voxels > 0 and cl.kind == "" and cl.n_gauge >= c.near_escalate_voxels
                and cl.distance <= c.near_escalate_distance and cl.reason not in _NOT_ESCALATED)

    def _gate(self, distance: float) -> float:
        c = self.cfg
        return c.gate_base + c.gate_per_m * max(distance, 0.0)

    def _gated(self, pred: np.ndarray, cen: np.ndarray, x0: np.ndarray, step: float) -> np.ndarray:
        """Distances between predicted track positions ``pred`` (tracks at along-track ``x0``) and
        cluster centroids ``cen``, ``inf`` outside the association gate. A cluster nearer than
        predicted may be up to ``step`` (an object approaching at ``ego_speed_max`` over the frame
        interval) farther: on the whole distance, or with ``gate_along_only`` (27.09) on the
        along-track component only."""
        d = np.linalg.norm(pred[:, None, :] - cen[None, :, :], axis=2)
        dx = cen[None, :, 0] - pred[:, 0][:, None]   # <0: cluster is closer than predicted
        gate = np.array([self._gate(x) for x in x0])[:, None]
        if self.cfg.gate_along_only:
            dxe = np.where(dx < 0, np.minimum(0.0, dx + step), dx)
            de = np.sqrt(dxe ** 2 + np.sum((pred[:, None, 1:] - cen[None, :, 1:]) ** 2, axis=2))
            return np.where(de <= gate, d, np.inf)
        allowed = gate + np.where(dx < 0, step, 0.0)
        return np.where(d <= allowed, d, np.inf)

    def _keep_time_ok(self, t: Track) -> bool:
        """26.09 (``stop_keep_max_s``, safety review of B10): the keep rules act on ``t`` only while
        its last clean hit is at most that many seconds of sensor time ago (``Track.since_clean``,
        already advanced to this frame); 0 = no cap."""
        cap = self.cfg.stop_keep_max_s
        return cap <= 0 or t.since_clean <= cap + 1e-9

    def _keeps(self, t: Track, cl: Cluster) -> bool:
        """26.09 (``stop_keep_signature``): ``cl`` counts as inside the gauge for ``t`` although a
        shape signature demoted it, because ``t`` was reported as an obstacle in the previous frame
        (and ``cl`` has ``stop_keep_min_voxels`` strict voxels, and the track's last clean hit is
        within ``stop_keep_max_s``)."""
        return (self.cfg.stop_keep_signature and cl.demoted and t.reported and t.zone == "gauge"
                and cl.n_gauge >= self.cfg.stop_keep_min_voxels and self._keep_time_ok(t))

    def update(self, clusters: List[Cluster], ego_shift: float = 0.0,
               frame_dt: Optional[float] = None, low_ok: bool = True, rail_within: float = 0.0,
               thin: Optional[List[Cluster]] = None, far_thin: Optional[List[Cluster]] = None,
               low_height: Optional[List[Cluster]] = None,
               low_frame_dt: Optional[float] = None, odo_speed: Optional[float] = None) -> List[Track]:
        """Associate ``clusters`` with the tracks. ``ego_shift`` (m) is the distance the
        vehicle travelled since the previous frame when it is known: a track seen once has no
        velocity yet and is then predicted as a static object approaching by that much.
        ``frame_dt`` (s) is the interval since the previous frame; it accumulates each track's
        observed time for the ``confirm_time_s`` rule (without it persistence counts hits only).
        ``low_ok`` False (``lowobj.min_model_age``, 26.09, off) keeps a low track that was not
        reported in the previous frame from being reported in this one. ``rail_within`` > 0
        (``lowobj.rail_start_within``, 26.09, on at 4 m) keeps a low track that was not
        reported in the previous frame from being reported while its cluster of this frame is
        rail geometry (``Cluster.rail_line``, ``lowobj.mark_rail_line``) and it was never matched
        at or beyond ``rail_within``: the rail heads just ahead of a standing train. A track already
        reported, or once matched that far (an object approached from afar), is not affected; the
        association is unchanged, so this can only withhold a report. ``thin``
        (``stop_keep_thin``, 26.09, off) are clusters flatter than ``cluster.min_height``: after the
        association of ``clusters`` they may continue a track that nothing matched
        (:meth:`_continue_thin`), never start one. ``far_thin`` (``thin_far_min_distance``, 27.09,
        on): far scan lines (and weak far clusters) inside the gauge that overlap no
        cluster of ``clusters`` (the detector selects them); they continue unmatched tracks and start
        new ones (:meth:`_far_thin`), and a track ever matched by such a hit (``Track.far_evidence``)
        whose gauge vote needs those hits becomes a STOP only while it approaches
        (:meth:`_approaching`); otherwise it is reported as advisory (``Track.approach_block``), never
        hidden. A track whose clean hits alone vote gauge (:meth:`_clean_gauge`: within
        ``thin_far_min_distance`` every hit is clean, so the vote clears within ``zone_window`` hits)
        and a STOP in the previous frame keep the usual rules. ``low_frame_dt`` is the
        actual positive stamp interval when ``frame_dt`` was clipped for motion/fit rules;
        it advances only the bounded low-height continuation clock."""
        c = self.cfg
        if c.ego_veto_min_speed > 0:
            self._odometry(odo_speed, frame_dt)
        # Weak low evidence is never a normal hit or a seed, even when supplied directly
        # by another caller. The detector normally passes it separately.
        low_height = list(low_height or []) + [cl for cl in clusters if cl.low_height_weak]
        clusters = [cl for cl in clusters if not cl.low_height_weak]
        # widen the gate by the distance a static object travels in the *measured* interval, so a
        # dropped frame (0.2-0.3 s gap in the node) does not throw a 17 m/s approach out of the gate
        step = c.ego_speed_max * (float(frame_dt) if frame_dt is not None and frame_dt > 0 else c.frame_dt)
        if frame_dt is not None:
            self._timed = True
        dt = float(frame_dt) if frame_dt is not None else 0.0
        # 26.09 (stop_keep_max_s): the sensor time of this frame for the keep cap (the nominal period
        # when the caller gives no interval), so that the cap is in seconds at any input rate
        kdt = dt if dt > 0 else float(c.frame_dt)
        low_dt = float(low_frame_dt) if low_frame_dt is not None and low_frame_dt > 0 else kdt
        for t in self.tracks:
            t.low_since_clean += low_dt
        self._clock += kdt
        n_t, n_c = len(self.tracks), len(clusters)
        matched_t = np.zeros(n_t, dtype=bool)
        matched_c = np.zeros(n_c, dtype=bool)
        zw, hw = max(1, int(c.zone_window)), max(1, int(c.hit_window))
        nk = max(1, int(c.near_escalate_hits)) if c.near_escalate_voxels > 0 else 0
        if n_t and n_c:
            # greedy nearest-neighbour association on predicted positions
            static = np.array([-float(ego_shift), 0.0, 0.0])
            pred = np.stack([t.centroid + (t.velocity if t.hits > 1 else static) for t in self.tracks])
            cen = np.stack([cl.centroid for cl in clusters])
            # along-track motion towards the vehicle is allowed up to ``step`` extra
            d = self._gated(pred, cen, np.array([t.centroid[0] for t in self.tracks]), step)
            while True:
                if not np.isfinite(d).any():
                    break
                i, j = np.unravel_index(np.argmin(d), d.shape)
                t, cl = self.tracks[i], clusters[j]
                t.since_clean = 0.0 if cl.zone == "gauge" else t.since_clean + kdt
                keep = self._keeps(t, cl)
                t.velocity = 0.5 * t.velocity + 0.5 * (cl.centroid - t.centroid) if t.hits > 1 else (cl.centroid - t.centroid)
                t.centroid = cl.centroid
                t.hits += 1
                t.misses = 0
                t.age += 1
                t.span_s += dt
                t.confidence = min(1.0, t.confidence + c.conf_gain * cl.score)
                t.last = cl
                t.low_clean = cl if cl.kind == "low" else None
                if cl.kind == "low" and cl.zone == "gauge":
                    t.low_since_clean = 0.0
                if self.record:
                    t.obs = (t.obs + [observation(cl)])[-OBS_KEEP:]
                g = cl.zone == "gauge" or keep
                t.kept = keep
                t.gauge_hits += int(g)
                t.zone_hist = (t.zone_hist + [g])[-zw:]
                t.column_hist = (t.column_hist + [cl.reason == "column"])[-zw:]
                t.hit_hist = (t.hit_hist + [True])[-hw:]
                if nk:
                    t.near_hist = (t.near_hist + [self._near(cl)])[-nk:]
                self._note(t, cl, False, zw, "ordinary")
                t.history.append(cl.distance)
                matched_t[i] = matched_c[j] = True
                d[i, :] = np.inf
                d[:, j] = np.inf
        used: List[Cluster] = []
        if c.stop_keep_thin and thin:
            used = self._continue_thin(thin, matched_t, ego_shift, step, dt, zw, hw, nk, kdt)
        new_thin: List[Cluster] = []
        if c.thin_far_min_distance > 0 and far_thin:
            new_thin = self._far_thin([cl for cl in far_thin if not any(cl is u for u in used)],
                                      matched_t, ego_shift, step, dt, zw, hw, nk, kdt)
        if c.stop_keep_low_s > 0 and low_height:
            self._continue_low_height(low_height, matched_t, ego_shift, dt, zw, hw, nk, kdt)
        # unmatched tracks
        for i, t in enumerate(self.tracks):
            if not matched_t[i]:
                t.since_clean += kdt
                t.misses += 1
                t.age += 1
                t.span_s += dt
                t.centroid = t.centroid + t.velocity
                if t.hold > 0:              # a calibration re-seed hold: this miss does not count
                    continue
                t.clean_run = 0
                t.confidence = max(0.0, t.confidence - c.conf_decay)
                t.hit_hist = (t.hit_hist + [False])[-hw:]
        self.tracks = [t for t in self.tracks if t.misses <= c.max_misses or (t.hold > 0 and t.reported)]
        # new tracks
        for j, cl in enumerate(clusters):
            if not matched_c[j]:
                self.tracks.append(Track(
                    id=self._next_id, centroid=cl.centroid, velocity=np.zeros(3),
                    confidence=c.conf_gain * cl.score, last=cl, history=[cl.distance],
                    gauge_hits=int(cl.zone == "gauge"), zone_hist=[cl.zone == "gauge"], hit_hist=[True],
                    span_s=dt, zone_min_fraction=c.zone_min_fraction, zone_min_votes=int(c.zone_min_votes),
                    column_hist=[cl.reason == "column"], column_hold=int(c.column_hold),
                    near_hist=[self._near(cl)] if nk else [], near_hits=nk,
                    since_clean=0.0 if cl.zone == "gauge" else float("inf"),
                    obs=[observation(cl)] if self.record else [],
                    low_clean=cl if cl.kind == "low" else None,
                ))
                self._note(self.tracks[-1], cl, False, zw, "ordinary")
                self._next_id += 1
        for cl in new_thin:
            t = Track(id=self._next_id, centroid=cl.centroid, velocity=np.zeros(3),
                      confidence=c.conf_gain * cl.score, last=cl, history=[cl.distance],
                      gauge_hits=1, zone_hist=[True], hit_hist=[True], span_s=dt,
                      zone_min_fraction=c.zone_min_fraction, column_hist=[False],
                      column_hold=int(c.column_hold), near_hist=[False] if nk else [], near_hits=nk,
                      since_clean=float("inf"))
            self._note(t, cl, True, zw, "far_thin")
            self.tracks.append(t)
            self._next_id += 1
        # reported: confirmed now, or reported in the previous frame and missed for at most
        # hold_misses frames (a single missed frame does not drop a STOP; review 23.09), or inside
        # a re-seed hold window (reseed; matched or not)
        fresh_blocked_tracks = set()
        for t in self.tracks:
            was_reported = t.reported
            earned_stop = t.stop_earned
            was_blocked = t.fresh_blocked
            fresh_blocked = False
            t.fresh_blocked = False
            q = self._qualifies(t)
            if c.thin_far_min_distance > 0:
                # 27.09: a track whose gauge vote needs far scan-line / weak evidence becomes a STOP only
                # while it approaches, advisory otherwise (the ride: weak hits turned the zone vote of an
                # advisory fixture ahead of a standing train into a STOP); a STOP in the previous frame
                # keeps the usual rules (taking it down split a STOP episode of the ride)
                block = (t.far_evidence and not t.was_stop and not self._approaching(t)
                         and not self._clean_gauge(t))
                # 27.09 (judges' review): the block holds the track advisory, it never hides it, and it
                # applies only while the gauge vote needs the far hits: a track whose clean hits alone
                # vote gauge (a person walking up to a standing train after one weak far hit, an object
                # whose track a bed scan line started) keeps the usual rules
                t.approach_block = bool(block and (t.reported or q))
            if q and not low_ok and not t.reported and t.last is not None and t.last.kind == "low":
                q = False
            if (q and rail_within > 0 and not t.reported and t.last is not None and t.last.kind == "low"
                    and t.last.rail_line and max(t.history) < rail_within):
                q = False
            if (q and c.start_clean and not t.reported and t.last is not None and t.zone == "gauge"
                    and t.last.zone != "gauge" and not t.near_escalated):
                # 27.09 (P4 history, start_clean): the earlier hits' vote alone does not start a STOP
                # on a frame whose own cluster is advisory or outside the envelope
                q = False
            if q and c.fresh_stop_evidence and not earned_stop and t.rule_zone == "gauge":
                # Onset only: an already earned STOP remains governed by hold_misses and the
                # stop-keep rules, including through a reasonable occlusion. A far track that the
                # existing approach guard has made advisory must remain a visible advisory track,
                # rather than being hidden by this STOP-only candidate.
                q = self._fresh_stop_ok(t)
                fresh_blocked = not q
                if fresh_blocked:
                    fresh_blocked_tracks.add(id(t))
            if (q and c.explained_run > 0 and not earned_stop and t.rule_zone == "gauge"
                    and not t.near_escalated and any(t.explained_hist) and t.clean_run < c.explained_run) or (
                    q and c.ego_veto_min_speed > 0 and not earned_stop and t.rule_zone == "gauge"
                    and not t.near_escalated and self._carried_along(t)):
                # 29.09 (explained_run): a history of explained (demoted) hits needs a clean run before
                # a new STOP; the track stays a visible advisory meanwhile
                q = False
                fresh_blocked = explained_blocked = True
                fresh_blocked_tracks.add(id(t))
            else:
                explained_blocked = False
            t.reported = (q or (t.reported and 0 < t.misses <= c.hold_misses)
                          or (t.reported and t.hold > 0) or (explained_blocked and t.misses == 0))
            if was_blocked and not q and t.reported and t.misses > 0:
                # 29.09: a blocked advisory held through a missed frame stays blocked; otherwise its
                # zone vote would report it as a STOP on the very frame nothing was seen
                fresh_blocked = True
                fresh_blocked_tracks.add(id(t))
            if fresh_blocked and was_reported and not earned_stop and t.misses == 0:
                # The candidate blocks an advisory-to-STOP transition, but does not make an
                # already reported advisory track disappear on the matched frame.
                t.reported = True
            if (t.hold <= 0 and t.last is not None and t.last.low_height_weak
                    and t.low_since_clean > c.stop_keep_low_s + 1e-9):
                # The ordinary missed-frame hold must not extend the weak-evidence budget.
                # An independent calibration hold keeps its existing fixed countdown.
                t.reported = False
            t.fresh_blocked = bool(fresh_blocked and t.reported)
            if t.misses == 0:
                t.seen_reported = t.reported
            if t.hold > 0:
                t.hold -= 1
        if self.opinion is not None:
            self._doubt()
        for t in self.tracks:
            # Use the final report and zone, after weak-low expiry and opinion withholding.
            # Otherwise a rejected continuation could bypass the next fresh-onset check.
            t.stop_earned = (id(t) not in fresh_blocked_tracks and t.reported and t.zone == "gauge")
        if c.thin_far_min_distance > 0:
            # after the track opinion: a STOP withheld by it is not a STOP of this frame
            for t in self.tracks:
                t.was_stop = t.reported and t.zone == "gauge"
        return self.tracks

    @staticmethod
    def _low_height_agrees(t: Track, cl: Cluster, predicted: np.ndarray) -> bool:
        """A compact low blob near the predicted centre and similar to the last clean
        low shape. Comparing against the clean shape prevents gradual growth or shrinkage
        through a chain of weak observations. The 25 cm centre gate is deliberately much
        tighter than the normal range-dependent association gate."""
        clean = t.low_clean
        if (clean is None or t.last is None or t.last.kind != "low" or clean.rail_line
                or cl.kind != "low" or cl.zone != "gauge" or not cl.low_height_weak
                or cl.reason or cl.rail_line or not cl.points_idx.size):
            return False
        if np.linalg.norm(cl.centroid - predicted) > 0.25:
            return False
        # Degenerate observed extents (one scan line or a flat face) get only a small
        # absolute allowance; an enlarged surrounding bed patch is not the same object.
        size = clean.size
        return bool(np.all(cl.size >= 0.5 * size)
                    and np.all(cl.size <= 2.0 * np.maximum(size, [0.1, 0.1, 0.05])))

    def _continue_low_height(self, candidates: List[Cluster], matched: np.ndarray, ego_shift: float,
                             dt: float, zw: int, hw: int, nk: int, kdt: float) -> None:
        """Continue a reported low STOP using current straddle returns whose top alone
        narrowly fails the clean threshold. No seeds, no new confirmations, no confidence
        gain, and no reset of either clean-hit clock. Both association and the shape reference
        are bounded; a cluster agreeing with more than one track is unused."""
        static = np.array([-float(ego_shift), 0.0, 0.0])
        predictions = [t.centroid if matched[i] else t.centroid + (t.velocity if t.hits > 1 else static)
                       for i, t in enumerate(self.tracks)]
        for cl in candidates:
            owners = [i for i, t in enumerate(self.tracks)
                      if self._low_height_agrees(t, cl, predictions[i])]
            if len(owners) != 1:
                continue
            i = owners[0]
            t = self.tracks[i]
            if (matched[i] or not t.reported or t.zone != "gauge"
                    or t.low_since_clean > self.cfg.stop_keep_low_s + 1e-9):
                continue
            t.since_clean += kdt
            t.velocity = 0.5 * t.velocity + 0.5 * (cl.centroid - t.centroid)
            t.centroid = cl.centroid
            t.last = cl
            t.hits += 1
            t.age += 1
            t.span_s += dt
            t.misses = 0
            t.kept = True
            t.gauge_hits += 1
            t.zone_hist = (t.zone_hist + [True])[-zw:]
            t.column_hist = (t.column_hist + [False])[-zw:]
            t.hit_hist = (t.hit_hist + [True])[-hw:]
            if nk:
                t.near_hist = (t.near_hist + [False])[-nk:]
            self._note(t, cl, False, zw, "keep_low")
            t.history.append(cl.distance)
            matched[i] = True

    def _doubt(self) -> None:
        """27.09 (``tracking.doubt_extra_hits`` > 0 with ``doubt_model``): a track about to become a
        STOP (reported in zone gauge by the rules, not a STOP after the previous update) whose track
        opinion (``resense/opinion.py``) is below ``doubt_threshold`` and whose cluster is beyond
        ``doubt_near`` is withheld as advisory (zone 'warning', reason 'doubt') until it has stayed a
        STOP candidate, matched, for ``doubt_extra_hits`` more frames; the opinion is asked again on
        every such frame and releases it at once when it rises (with ``doubt_sticky`` the opinion at
        the onset decides: only the extra frames or ``doubt_near`` release it). The extra frames are a
        budget for the life of the track: a frame withheld over a miss spends it too, and a track that
        stops qualifying and qualifies again does not get it back, so no track is withheld for more
        than ``doubt_extra_hits`` frames in all. Never a veto: it only asks more persistence of a track
        the rules would report, never within ``doubt_near``, and never for a standing body (a cluster at
        least ``doubt_body_height`` tall) within ``doubt_body_range``."""
        c = self.cfg
        for t in self.tracks:
            if not (t.reported and t.rule_zone == "gauge"):
                t.withheld = False
            elif t.stop_prev and not t.withheld:
                pass                        # already a STOP: unchanged
            elif t.misses > 0:
                if t.withheld and self._doubt_exempt(t):
                    t.withheld = False      # reached doubt_near (or the body range) while missed
                elif t.withheld:            # held over a miss: the budget still runs
                    t.doubt += 1
                    t.withheld = t.doubt <= c.doubt_extra_hits
            elif not t.obs or self._doubt_exempt(t):
                t.withheld = False
            elif not (c.doubt_sticky and t.withheld) and (
                    self.opinion.prob(track_features(t.obs, t.hits, t.hit_fraction)) >= c.doubt_threshold):
                t.withheld = False
            else:
                t.doubt += 1
                t.withheld = t.doubt <= c.doubt_extra_hits
            t.stop_prev = t.reported and t.zone == "gauge"

    def _doubt_exempt(self, t: Track) -> bool:
        """27.09: ``t`` may not be withheld by the opinion: its distance (the predicted one over a
        missed frame) is within ``doubt_near``, or its last cluster stands at least
        ``doubt_body_height`` tall within ``doubt_body_range``."""
        c = self.cfg
        if t.last is None:
            return True
        d = float(t.last.distance) + (float(t.centroid[0] - t.last.centroid[0]) if t.misses > 0 else 0.0)
        return d <= c.doubt_near or (c.doubt_body_height > 0 and d <= c.doubt_body_range
                                     and t.last.height_max - t.last.height_min >= c.doubt_body_height)

    def _continue_thin(self, thin: List[Cluster], matched_t: np.ndarray, ego_shift: float, step: float,
                       dt: float, zw: int, hw: int, nk: int = 0, kdt: float = 0.0) -> None:
        """26.09 (``stop_keep_thin``): tracks that no cluster matched in this frame are associated,
        greedily and with the same gate and prediction, with the clusters flatter than
        ``cluster.min_height`` (one scan line: the part of an object inside the envelope thinner than
        the ring spacing at range) that are inside the gauge (zone ``gauge``, or with
        ``stop_keep_signature`` demoted only by a shape signature) with ``stop_keep_min_voxels``
        strict voxels. Mode 1: only tracks reported as
        obstacles in the previous frame; mode 2: also a track not yet reported whose previous hit
        was inside the gauge (zone ``gauge``), so that one scan line counts towards its confirmation.
        A match is a hit like any other.
        Nothing else sees these clusters: they never start a track. A scan line is never a clean hit:
        with ``stop_keep_max_s`` a track is continued only while its last clean hit is within it."""
        c = self.cfg
        mode = int(c.stop_keep_thin)
        cand = []
        for i, t in enumerate(self.tracks):
            if matched_t[i] or t.last is None:
                continue
            stop = t.reported and t.zone == "gauge"
            if c.stop_keep_max_s > 0 and t.since_clean + kdt > c.stop_keep_max_s + 1e-9:
                continue
            if stop or (mode >= 2 and not t.reported and t.last.zone == "gauge"):
                cand.append(i)
        ok = [j for j, cl in enumerate(thin) if (cl.zone == "gauge" or (c.stop_keep_signature and cl.demoted))
              and cl.n_gauge >= c.stop_keep_min_voxels]
        used: List[Cluster] = []
        if not cand or not ok:
            return used
        static = np.array([-float(ego_shift), 0.0, 0.0])
        pred = np.stack([self.tracks[i].centroid + (self.tracks[i].velocity if self.tracks[i].hits > 1 else static)
                         for i in cand])
        cen = np.stack([thin[j].centroid for j in ok])
        d = self._gated(pred, cen, np.array([self.tracks[i].centroid[0] for i in cand]), step)
        for a, i in enumerate(cand):
            t = self.tracks[i]
            if not (t.reported and t.zone == "gauge"):
                # mode 2: a thin cluster demoted by a signature never counts for a track not reported
                for b, j in enumerate(ok):
                    if thin[j].zone != "gauge":
                        d[a, b] = np.inf
        while np.isfinite(d).any():
            a, b = np.unravel_index(np.argmin(d), d.shape)
            i = cand[a]
            t, cl = self.tracks[i], thin[ok[b]]
            stop = t.reported and t.zone == "gauge"
            t.since_clean += kdt
            t.velocity = 0.5 * t.velocity + 0.5 * (cl.centroid - t.centroid) if t.hits > 1 else (cl.centroid - t.centroid)
            t.centroid = cl.centroid
            t.hits += 1
            t.misses = 0
            t.age += 1
            t.span_s += dt
            t.confidence = min(1.0, t.confidence + c.conf_gain * cl.score)
            t.last = cl
            if self.record:
                t.obs = (t.obs + [observation(cl)])[-OBS_KEEP:]
            t.kept = stop
            t.gauge_hits += 1
            t.zone_hist = (t.zone_hist + [True])[-zw:]
            t.column_hist = (t.column_hist + [cl.reason == "column"])[-zw:]
            t.hit_hist = (t.hit_hist + [True])[-hw:]
            if nk:
                t.near_hist = (t.near_hist + [self._near(cl)])[-nk:]
            self._note(t, cl, False, zw, "keep_thin")
            t.history.append(cl.distance)
            matched_t[i] = True
            used.append(cl)
            d[a, :] = np.inf
            d[:, b] = np.inf
        return used

    def _note(self, t: Track, cl: Cluster, far_thin: bool, zw: int, source: str = "ordinary") -> None:
        """Record hit provenance and the existing far-evidence approach history.

        ``source`` is ``ordinary`` for a current cluster (including low-object evidence),
        ``far_thin`` for the detector's separate sparse-evidence path, ``keep_thin`` for a
        scan-line continuation, and ``keep_low`` for bounded weak-low continuation. Neither
        continuation source supplies fresh evidence for a new STOP onset.
        """
        c = self.cfg
        if c.ego_veto_min_speed > 0 and source in ("ordinary", "far_thin"):
            t.odo = (t.odo + [(self._odo_seg, self._odo_x, float(cl.distance))])[-10:]
        if c.explained_run > 0 and source == "ordinary":
            reasons = [r.strip() for r in str(c.explained_reasons).split(",") if r.strip()]
            explained = bool(cl.reason) and (not reasons or cl.reason in reasons)
            t.explained_hist = (t.explained_hist + [explained])[-max(1, int(c.explained_window)):]
            t.clean_run = t.clean_run + 1 if (cl.zone == "gauge" and not cl.reason) else 0
        if c.fresh_stop_evidence:
            n = max(1, int(c.fresh_stop_evidence_window))
            if source == "ordinary" and cl.zone != "gauge":
                source = "off_gauge"
            t.evidence_hist = (t.evidence_hist + [source])[-n:]
        if c.thin_far_min_distance <= 0:
            return
        t.far_evidence = t.far_evidence or bool(far_thin)
        t.thin_hist = (t.thin_hist + [bool(far_thin)])[-zw:]
        t.approach = (t.approach + [(self._clock, float(cl.distance))])[-max(2, int(c.approach_hits)):]

    def _odometry(self, speed: Optional[float], frame_dt: Optional[float]) -> None:
        """29.09 (ego_veto_*): integrate the train's travel from the per-frame speed; an unknown speed,
        an unusable interval or an implausible jump (> 1.5 m/s^2 + 0.3 m/s) starts a new segment."""
        dt = float(frame_dt) if frame_dt is not None else self.cfg.frame_dt
        v = None if speed is None or not np.isfinite(speed) else float(speed)
        if (v is None or not 0.0 < dt <= 0.35
                or (self._odo_v is not None and abs(v - self._odo_v) > 1.5 * dt + 0.3)):
            self._odo_seg += 1
            self._odo_v = None if v is None else v
            return
        self._odo_x += v * dt
        self._odo_v = v

    def _carried_along(self, t: Track) -> bool:
        """29.09 (ego_veto_*, after TunnelGuard ``_carried_along``): while the train demonstrably moves,
        a track whose distance does not fall with the travel (Theil-Sen slope of distance against
        travel above ``ego_veto_max_slope``) is not a static object ahead; no decision without
        enough hits and travel in the current odometry segment."""
        c = self.cfg
        if self._odo_v is None or self._odo_v < c.ego_veto_min_speed or t.last is None:
            return False
        if float(t.last.distance) < c.ego_veto_min_distance:
            return False
        o = np.array([(x, d) for seg, x, d in t.odo if seg == self._odo_seg], dtype=float)
        if len(o) < max(2, int(c.ego_veto_min_hits)) or float(np.ptp(o[:, 0])) < c.ego_veto_min_travel:
            return False
        i, j = np.triu_indices(len(o), 1)
        dx = o[j, 0] - o[i, 0]
        ok = np.abs(dx) > 0.5
        if ok.sum() < 3:
            return False
        return float(np.median((o[j, 1] - o[i, 1])[ok] / dx[ok])) > c.ego_veto_max_slope

    def _fresh_stop_ok(self, t: Track) -> bool:
        """Check bounded provenance for a new STOP onset.

        The current match must be strict gauge evidence, so an old gauge vote cannot confirm on an
        advisory/off-gauge frame. Ordinary and low-object gauge hits count directly. A far sparse
        hit counts only when its existing approach fit identifies an approaching target. Thin
        and weak-low continuation hits are deliberately excluded.
        """
        c = self.cfg
        if t.misses != 0 or t.last is None or t.last.zone != "gauge" or not t.evidence_hist:
            return False
        source = t.evidence_hist[-1]
        if source in ("keep_thin", "keep_low"):
            return False
        if source == "far_thin" and not self._approaching(t):
            return False
        approaching = self._approaching(t) if "far_thin" in t.evidence_hist else False
        eligible = sum(s == "ordinary" or (s == "far_thin" and approaching)
                       for s in t.evidence_hist)
        return eligible >= max(1, int(c.fresh_stop_evidence_min_hits))

    def _clean_gauge(self, t: Track) -> bool:
        """27.09: the zone vote of ``t`` is 'gauge' with its far scan-line / weak hits counted as not
        inside (``Track.thin_hist``, aligned with ``zone_hist``): the far evidence is not needed."""
        if not t.zone_hist:
            return False
        far = t.thin_hist[-len(t.zone_hist):]
        far = [False] * (len(t.zone_hist) - len(far)) + list(far)
        clean = sum(z and not f for z, f in zip(t.zone_hist, far))
        n = max(len(t.zone_hist), int(getattr(self.cfg, "zone_min_votes", 0) or 0))
        return clean >= t.zone_min_fraction * n - 1e-9

    def _approaching(self, t: Track) -> bool:
        """27.09 (``approach_*``): the distances of the track's last ``approach_hits`` hits lie on a
        line in sensor time (RMS residual at most ``approach_max_residual``) that approaches at
        ``approach_min_speed`` to ``ego_speed_max``: a static object ahead of a moving train, not a
        scan line of the bed or the vault (fixed in the sensor frame, or jumping with the pitch)."""
        c = self.cfg
        k = max(2, int(c.approach_hits))
        if len(t.approach) < k:
            return False
        p = np.asarray(t.approach[-k:], dtype=np.float64)
        tt = p[:, 0] - p[:, 0].mean()
        dd = p[:, 1] - p[:, 1].mean()
        var = float((tt * tt).sum())
        if var <= 0:
            return False
        s = float((tt * dd).sum()) / var
        rms = float(np.sqrt(np.mean((dd - s * tt) ** 2)))
        return -c.ego_speed_max - 1e-9 <= s <= -c.approach_min_speed and rms <= c.approach_max_residual

    def _far_thin(self, thin: List[Cluster], matched_t: np.ndarray, ego_shift: float, step: float,
                  dt: float, zw: int, hw: int, nk: int = 0, kdt: float = 0.0) -> List[Cluster]:
        """27.09 (``thin_far_min_distance``, on): far scan lines inside the gauge
        (selected by the detector: at least that far, zone ``gauge``, ``thin_far_min_voxels`` strict
        voxels, overlapping no other cluster of the frame) are associated, greedily with the same
        gate and prediction, with the tracks nothing matched in this frame; a match is a hit inside
        the gauge (never a clean hit for the keep cap) and marks the track (``Track.far_evidence``) so
        that it becomes a STOP only while it approaches (:meth:`_approaching`). Only an
        unambiguous scan line is used: one inside the gate of exactly one track, and that track
        unmatched in this frame, continues it; one inside the gate of no track starts a new track
        (returned); one inside the gates of several tracks, or of a track already matched this frame,
        is not used at all (the ride: a scan line between two tracks of one structure moved one of
        them and changed the next frame's association, which re-reported a false STOP)."""
        c = self.cfg
        if not thin:
            return []
        if not self.tracks:
            return list(thin)
        static = np.array([-float(ego_shift), 0.0, 0.0])
        # matched tracks are where their cluster of this frame is, the others where they are predicted
        pos = np.stack([t.centroid if matched_t[i] else t.centroid + (t.velocity if t.hits > 1 else static)
                        for i, t in enumerate(self.tracks)])
        cen = np.stack([cl.centroid for cl in thin])
        d = np.linalg.norm(pos[:, None, :] - cen[None, :, :], axis=2)
        dx = cen[None, :, 0] - pos[:, 0][:, None]
        allowed = np.array([self._gate(t.centroid[0]) for t in self.tracks])[:, None] + np.where(dx < 0, step, 0.0)
        inside = d <= allowed
        owners = inside.sum(axis=0)
        free = [j for j in range(len(thin)) if owners[j] == 0]
        usable = (owners == 1)[None, :] & inside & ~matched_t[:, None] & np.array(
            [t.last is not None for t in self.tracks])[:, None]
        d = np.where(usable, d, np.inf)
        cand = list(range(len(self.tracks)))
        while np.isfinite(d).any():
            a, b = np.unravel_index(np.argmin(d), d.shape)
            i = cand[a]
            t, cl = self.tracks[i], thin[b]
            t.since_clean += kdt
            t.velocity = 0.5 * t.velocity + 0.5 * (cl.centroid - t.centroid) if t.hits > 1 else (cl.centroid - t.centroid)
            t.centroid = cl.centroid
            t.hits += 1
            t.misses = 0
            t.age += 1
            t.span_s += dt
            t.confidence = min(1.0, t.confidence + c.conf_gain * cl.score)
            t.last = cl
            t.kept = False
            t.gauge_hits += 1
            t.zone_hist = (t.zone_hist + [True])[-zw:]
            t.column_hist = (t.column_hist + [False])[-zw:]
            t.hit_hist = (t.hit_hist + [True])[-hw:]
            if nk:
                t.near_hist = (t.near_hist + [False])[-nk:]
            self._note(t, cl, True, zw, "far_thin")
            t.history.append(cl.distance)
            matched_t[i] = True
            d[a, :] = np.inf
            d[:, b] = np.inf
        return [thin[j] for j in free]

    def _qualifies(self, t: Track) -> bool:
        c = self.cfg
        if (c.low_min_seen_distance > 0 and t.last is not None and t.last.kind == "low" and t.history
                and max(t.history) < c.low_min_seen_distance):
            # 26.09 (P3 start-up): a low track never matched as far as the learned bed cross-section
            # starts (the rail heads just ahead of a standing train under a young model)
            return False
        need_span = c.confirm_time_s if (self._timed and c.confirm_time_s > 0) else 0.0
        return (t.hits >= (c.low_confirm_hits if (t.last is not None and t.last.kind == "low") else c.confirm_hits)
                and t.confidence >= c.conf_threshold and t.misses == 0
                and t.span_s >= need_span - 1e-9
                and (c.min_hit_fraction <= 0 or t.hit_fraction >= c.min_hit_fraction - 1e-9))

    def confirmed(self) -> List[Track]:
        """The tracks reported after the last ``update``: confirmed in this frame, or held over
        ``hold_misses`` missed frames after being reported (their cluster is the last matched one)."""
        return [t for t in self.tracks if t.reported]
