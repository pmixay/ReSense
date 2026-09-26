"""Configuration of the detection pipeline (plain dataclasses, loadable from YAML)."""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import Any, List, Tuple

import yaml


@dataclass
class SensorConfig:
    """How to map the raw sensor frame onto the vehicle frame (X fwd, Y left, Z up).

    Each entry names the sensor axis (with sign) that points along the vehicle axis.
    Hackathon bags (frame_id ``hesai_lidar``): forward = -y, left = +x, up = +z.
    """
    forward: str = "-y"
    left: str = "+x"
    up: str = "+z"
    min_range: float = 2.5     # m, closer returns are the train's own nose / sensor artefacts
    max_range: float = 250.0   # m
    frame_id: str = "hesai_lidar"
    # v0.6: fixed mount correction applied after the axis mapping, p = Rz(yaw) Ry(pitch) Rx(roll) p_axes
    # (the values the automatic calibration reports as mount.roll_deg / pitch_deg / yaw_deg can be
    # frozen here, or set by hand for a known mount; the calibration then refines on top)
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0


@dataclass
class TrackConfig:
    """Track/floor model estimated per frame."""
    lateral_center: float = -0.1   # m, prior/fallback offset of the track axis (+ = left)
    yaw_deg: float = 0.0           # residual yaw of the corridor w.r.t. vehicle X axis
    curvature: float = 0.0         # 1/m, signed (left positive); 0 = straight
    floor_fit_range: Tuple[float, float] = (3.0, 120.0)
    floor_bin: float = 2.0         # m, along-track bin size for the floor profile
    floor_percentile: float = 20.0 # per-bin percentile of Z taken as floor reference (track bed)
    floor_halfwidth: float = 1.0   # m, lateral band around the track axis used for the fit
    floor_min_points: int = 15     # per bin
    floor_poly_degree: int = 2
    floor_max_residual: float = 0.35  # m, bins further from the fit are rejected (2nd pass)
    floor_smoothing: float = 0.5   # exponential smoothing of coefficients across frames (0 = off)
    # on since 25.09 (P3, docs/evidence/results/p3_rail_shadow_2026-09-25.json): the shadow of a large near
    # object in the bed band (set O, the 2 x 2 m box at 10-20 m tilted the fit through the roof behind
    # it): bins this far above the previous bed, two in a row starting within floor_shadow_range, start a
    # shadow; then only bed bins (within floor_max_residual of the previous bed) are fitted, never the
    # object's face, and the rail pair is searched in front of the face; with fewer than
    # floor_shadow_min_bins bed bins (or 2 m x that much track) in front the previous bed / rail model is
    # held. 0 = off
    floor_shadow_height: float = 1.0
    floor_shadow_range: float = 30.0   # m (40 fired at 37-38.5 m on doubleT_platform and added a false alarm, round 1)
    floor_shadow_min_bins: int = 5
    # review 25.09: at most this many held frames in a row (10 Hz), then the rule is released until no
    # shadow is found (a held bed is the next frame's reference: a pitch step held it for good); set O
    # #1 holds 14 frames in a row while the box closes from ~13 to ~3 m. 0 = no cap
    floor_shadow_max_hold: int = 20
    # 25.09 (P3 bed_bin): a far bed bin (centre >= floor_far_from) whose low points span less than
    # floor_far_min_width laterally, with >= floor_far_min_standing points standing on them, is the
    # foot of an object, not the bed, and is dropped from the fit (track._narrow_far_bins); 0 = off
    floor_far_min_width: float = 0.0
    floor_far_from: float = 90.0
    floor_far_min_standing: int = 2
    # --- rail-based self-calibration of the track axis (near range) ---
    rails_enabled: bool = True
    rails_range: Tuple[float, float] = (4.0, 30.0)   # m along track
    rails_search_halfwidth: float = 2.5             # m around the prior axis
    rails_bin: float = 0.05                         # m lateral bin of the height profile
    rails_percentile: float = 85.0                  # per-bin height percentile (rail head)
    rails_spacing: float = 1.59                     # m between rail-head centres (1520 gauge + head)
    rails_min_score: float = 0.05                   # m, ridge prominence needed to accept
    rails_head_height: Tuple[float, float] = (0.08, 0.5)  # plausible rail head above bed ref
    rails_smoothing: float = 0.7                    # EMA of the axis across frames
    rail_offset_default: float = 0.35               # rail head above bed reference if not measured
    # --- yaw / curvature of the axis from the tunnel boundaries (walls, column rows) ---
    walls_enabled: bool = True
    walls_range: Tuple[float, float] = (6.0, 160.0)  # m along track
    walls_band: Tuple[float, float] = (1.6, 2.8)     # height band above the rail head (above platforms)
    walls_bin: float = 4.0                           # m along-track bin
    walls_min_points: int = 3                        # per side per bin
    walls_percentile: float = 90.0                   # boundary = this percentile of |dy| per side
    walls_max_residual: float = 0.4                  # m, bins further from the fit are rejected
    walls_min_bins: int = 6
    walls_max_rms: float = 0.35
    walls_max_yaw: float = 0.09                      # |tan(yaw)| limit (~5 deg: mount yaw of ~1-1.5 deg in the bags plus the body angle in a curve; 0.035 in v0.3 saturated in every moving bag, 0.06 was within 0.6 deg of binding on roundT_doubleT frames 120-180)
    walls_min_radius: float = 150.0                  # m, curvature limit
    walls_smoothing: float = 0.6                     # EMA of (yaw, curvature) across frames
    walls_min_far_support: float = 0.0               # 25.09, 0 = off: with both sides fitted, a side keeping fewer than this fraction of its boundary bins beyond rails_range[1] within walls_max_residual of its fit does not set the axis shape when the other side's do and it is nearly straight (EXPERIMENTS §1h: the 82.9 m platform end)
    walls_far_support_max_curvature: float = 2.0e-4  # 1/m, walls_min_far_support only overrules towards a side this straight (R >= 5 km): never on a real curve
    walls_far_support_frames: int = 1                # walls_min_far_support applies from the N-th consecutive frame its condition holds (a station stop, not a one-frame spurious side)
    axis_valid_margin: float = 15.0                  # m beyond the last observed boundary bin the axis is trusted
    axis_valid_straight_bonus: float = 50.0          # extra trusted range when the tunnel is straight (|curv| < 1e-4) and both boundaries agree
    floor_valid_margin: float = 20.0                 # m beyond the fitted bed range the height reference is trusted without verification (60 in v0.3: the extrapolated bed was 0.3-0.65 m off at 85-105 m in the platform bags)
    # --- v0.5: yaw at the vehicle from the rail pair per along-track slab (the walls then give the curvature only) ---
    rails_yaw_enabled: bool = True                   # yaw from the rail-pair midpoints of several near slabs; off = free quadratic through the walls (v0.3)
    rails_yaw_slabs: int = 3                         # slabs between rails_range[0] and rails_range[1]
    rails_yaw_min_slabs: int = 2                     # slabs with a plausible rail pair needed for a yaw estimate
    rails_yaw_max_dev: float = 0.3                   # m, a slab's rail may sit this far from the global rail position
    rails_far_check_enabled: bool = False            # experimental station-wall curvature correction; opt-in until real-data A/B and timing
    axis_max_yaw_rate: float = 0.003                 # rad per frame (0.17 deg; a train at 15 m/s on R = 700 m yaws 0.12 deg per frame); larger changes are clipped; 0 = off
    axis_max_curvature_rate: float = 1.0e-4          # 1/m per frame, larger changes of the smoothed curvature are clipped; 0 = off
    axis_warmup_frames: int = 5                      # frames after a (re)seed of the track model during which the rate limits do not apply (v0.6)
    rates_per_period: bool = True                    # on since 25.09 (P3, SCORECARD #13): the two rate limits above and axis_warmup_frames count nominal frame periods (tracking.frame_dt), not processed frames: x k with k = the input rate in periods (median of the last 9 stamp intervals, rounded: 1 at 10 Hz, 2 at 5 Hz); the bed / rail smoothing stays per frame (it averages noise); 5 Hz five bags 13 / 17 -> 10 / 10 events / STOP episodes with walls_smoothing_per_period, 10 Hz gate identical (EXPERIMENTS.md section 1i, docs/evidence/results/p3_robustness_2026-09-25.json); false = per processed frame
    walls_smoothing_per_period: bool = True          # on since 25.09 (P3): walls_smoothing (the EMA of the axis yaw / curvature, which change with the distance travelled) per nominal frame period, a^k; floor_ / rails_smoothing stay per frame (squared at 5 Hz they lost 5 labelled frames of the object on the rail); false = per processed frame
    axis_sides_max_disagreement: float = 6.7e-4      # 1/m, both boundaries fitted and their curvatures differ by more (R 1500 m): axis trusted only to axis_disagree_range; 0 = off
    axis_disagree_range: float = 60.0                # m, trusted range of the axis when the two boundaries disagree
    axis_one_side_range: float = 120.0               # m, trusted range when only one boundary was fitted (it cannot tell a parallel wall from a diverging one); 0 = no cap
    # --- verification of the extrapolated bed beyond its fitted range (second height anchor) ---
    floor_verify_enabled: bool = True                # confirm the extrapolated bed with the base of the side structures
    floor_verify_band: Tuple[float, float] = (1.6, 3.5)  # m, |dy| band of walls / benches / ducts (outside the advisory corridor)
    floor_verify_bin: float = 5.0                    # m, along-track bin of the side-base profile
    floor_verify_window: float = 30.0                # m, window whose median deviation must stay within the tolerance
    floor_verify_tolerance: float = 0.5              # m, allowed deviation of the far side base from its near-range height
    floor_verify_min_points: int = 5                 # side points per bin for the bin to count
    floor_verify_max_range: float = 250.0            # m, how far the verification is attempted


@dataclass
class GaugeConfig:
    """Clearance-gauge cross-section, relative to the track axis and the rail head level.

    ``profile`` is a closed polygon [(dy, h), ...] with dy = lateral offset from the track
    axis (m, + left) and h = height above the rail head (m). Default since v0.6: **the train
    envelope the organizers gave in the Q&A session (2.1 m wide x 3.0 m high, all protruding
    elements included)**: half-width 1.05 m, from 0.12 m above the rail head (the rail heads,
    their fastenings and the joint bars stay out) to 3.0 m. Objects lower than 0.12 m on the
    track are the low-object stage's (``lowobj``). v0.5 used a 2.8 m x 3.5 m polygon assumed
    from the car body (1.36 m half-width + margin); it is now the advisory zone:
    ``warning_margin`` = 0.35 m widens the polygon laterally to 1.40 m.
    """
    profile: List[Tuple[float, float]] = field(default_factory=lambda: [
        (-1.05, 0.12), (1.05, 0.12), (1.05, 3.00), (-1.05, 3.00),
    ])
    warning_margin: float = 0.35   # m, extra lateral width of the advisory zone
    range_min: float = 3.0         # m along track
    range_max: float = 250.0
    lateral_growth_per_100m: float = 0.0  # widen corridor with range to absorb yaw uncertainty
    # v0.5: a voxel counts towards the strict-gauge decision only when it lies this far inside the
    # polygon's lateral edge (the axis is uncertain by ~0.1 deg, i.e. 0.1 m per 60 m of range);
    # candidates and the advisory zone are unaffected. 0 = off (v0.3 behaviour)
    edge_margin: float = 0.0
    edge_margin_per_100m: float = 0.15   # v0.6: 0.15 m per 100 m (0.3 m at 200 m) of axis uncertainty at the envelope edge
    no_rail_range: float = 40.0    # v0.6.2: m; in a frame without the rail pair in the near range (stations, switch caverns: the axis rests on walls alone) the corridor beyond this is advisory only; 0 = off
    # 26.09 (P3, judge A action 7; docs/evidence/results/p3_edge_axis_2026-09-26.json): the envelope also
    # measured from the SENSOR axis (the processed frame's X axis, the organizers' placement frame), as a
    # union with the rail envelope, only where the two agree: rail pair locked, |curvature| <=
    # axis_union_max_curvature, X <= axis_union_range and the rail axis within axis_union_max_offset of
    # the sensor axis. 0 = off; 1 = strict membership only (A); 2 = the corridor coordinate re-measured (B)
    axis_union: int = 0
    axis_union_range: float = 50.0          # m, near field only
    axis_union_max_offset: float = 0.30     # m, |c(X)| = rail axis minus sensor axis (below warning_margin)
    axis_union_max_curvature: float = 2e-4  # 1/m, straight track only (R >= 5 km)


@dataclass
class ClusterConfig:
    eps: float = 0.35              # m, DBSCAN radius at range 0 (scaled by 1 + r / range_scale)
    range_scale: float = 40.0      # m
    voxel: float = 0.05            # m, voxel size in range-normalised space (merges dual returns)
    min_samples: int = 3
    min_points: int = 5            # minimum cluster size in voxels (near range)
    min_points_far: int = 3        # minimum cluster size beyond ``far_range``
    far_range: float = 100.0
    max_extent: float = 8.0        # m, larger clusters are tunnel structure, not obstacles
    # on since 25.09 (P3): > 0 = a cluster larger than max_extent is not dropped when its part inside the
    # strict gauge is at most this long along the track: an object touching a long line at the corridor
    # edge (the set O box at 9-21 m next to the line at 1.35-1.40 m; a person next to a conductor rail)
    # is re-described from that part; 0 = off (the whole cluster dropped)
    oversize_split_max_length: float = 3.0
    oversize_split_max_distance: float = 30.0  # m, ... and only when that part starts within this distance (the far corridor holds long sparse clusters with a few gauge voxels, round 1 of 25.09)
    # on since 25.09 (P3): true = the distance of a cluster inside the strict gauge is that of its nearest
    # point inside the gauge, not of a point in the advisory margin it touches; false = the nearest point (v0.1).
    # Since the review of 25.09 "inside" is the envelope widened by the axis-uncertainty margin
    # (gauge.edge_margin_per_100m; resense.gauge.gauge_reach_mask), never the strict-gauge mask shrunk by it
    gauge_distance: bool = True
    min_height: float = 0.08       # m, vertical extent (very flat clusters = floor noise)
    # linear infrastructure (rails, pipes, cables): long, thin, flat
    thin_min_length: float = 3.0
    thin_max_width: float = 0.35
    thin_max_height: float = 0.25
    # track hardware: low, narrow things on/next to the rails (clamps, cables, joint bars)
    hardware_max_top: float = 0.35     # m above rail head
    hardware_max_width: float = 0.4
    hardware_max_height: float = 0.3
    # linear structures along the track at the side (platform edges, ducts, cable trays)
    linear_min_aspect: float = 5.0     # length / width
    linear_max_height: float = 0.8
    linear_min_lateral: float = 0.8
    # wall-like clusters at the side of the corridor (columns, gate frames, platform walls)
    wall_min_height: float = 1.9
    wall_min_lateral: float = 1.2
    wall_segment_min_length: float = 4.0   # tall + long + narrow = wall segment (a train ahead is wide)
    wall_segment_max_width: float = 1.5
    gauge_min_points: int = 3      # voxels inside the strict gauge to classify as 'gauge'
    overhead_min_height: float = 3.0   # clusters entirely above this (m over rail head) are advisory only (v0.6: the envelope top; 2.4 in v0.5)
    # v0.5 infrastructure signatures measured on the organizer bags (EXPERIMENTS.md section 1b); each demotes
    # the cluster to advisory ('warning'), never drops it; 0 = rule off
    column_min_height: float = 2.2     # m, taller and narrower than column_max_width = column / post / gate leg (a person is 1.7 m)
    column_max_width: float = 1.0      # m
    column_min_width: float = 0.25     # m, v0.6: near the axis only clusters at least this wide are columns (a hanging cable is thinner)
    elevated_min_height: float = 1.2   # m, lowest point above this and wider than elevated_min_width = beam / roof strip / sign gantry
    elevated_min_width: float = 2.0    # m (a train ahead reaches down to the polygon bottom)
    floating_min_height: float = 0.7   # m, lowest point above this, lower than floating_max_height and narrower than floating_max_width = sign / lamp / bracket on the wall
    floating_max_height: float = 1.2   # m (a person is taller: a 1.5 m limit demoted a person on a platform edge, review 22.09)
    floating_max_width: float = 1.0    # m
    floating_long_min_length: float = 3.0  # m, on since 25.09 (decided on the ride; station false STOPs; 0 = off): > 0 = the floating shape also demotes a cluster longer than this along the track near the axis (an overhead duct / tray / beam running along the track; the lateral condition keeps shorter ones, e.g. a hanging cable)
    floating_long_min_bottom: float = 1.6  # m, since 25.09 (review): ... and only when its lowest point is above this (overhead infrastructure; a tray / duct / pipe fallen onto the axis lower in the envelope is an obstacle); 0 = no bottom condition (the first 25.09 rule)
    floating_free_max_size: float = 0.5   # m, on since 25.09 round 2 (pre-registered A of A / B / C, gate PASS; 0 = off): the floating signature does not demote a compact cluster hanging free inside the envelope (set O cube #2: STOP from 52.5 m instead of 34.0 m, six recordings and the ride identical per frame): every extent at most this,
    floating_free_max_dy: float = 0.95    # m, ... its outermost point at most this far off the axis (inside the 1.05 m envelope edge: not reaching the wall side of the corridor, 1.40 m),
    floating_free_max_top: float = 2.5    # m, ... and its top at most this high above the rail head (under the 3.0 m envelope top: not hanging from the vault); docs/evidence/results/p3_signatures_2026-09-25.json
    edge_min_lateral: float = 1.0      # m (v0.6: 1.2 with the 1.40 m polygon), |lateral| beyond this, longer than edge_min_aspect x width and lower than edge_max_height = duct / bench / platform-edge fragment
    edge_min_aspect: float = 2.5
    edge_max_height: float = 1.0       # m
    far_min_height: float = 0.6        # m, v0.6: beyond the trusted height reference (but within the trusted axis) only clusters at least this tall are obstacles,
    far_max_length: float = 3.0        # m, ... at most this long along the track (a face seen head-on, not a surface at grazing incidence),
    far_max_bottom: float = 1.0        # m, ... and reaching down below this height (not a sign hanging above the far corridor)
    far_axis_both_sides: int = 0       # 25.09 (far_switch), 0 = off: beyond the height reference, a far obstacle needs both fitted tunnel boundaries to support the axis there (the shorter side's last bin + axis_valid_margin); 1 = on every frame, the corridor itself ends there (+ the straight bonus); 2 = only on bent frames (no straight bonus), would-be obstacles demoted (beyond_axis); both measured, neither shipped (EXPERIMENTS 1h)
    signature_min_lateral: float = 0.6  # m, v0.6: the column and floating signatures apply only off the track centre (a cable / object hanging into the envelope near the axis is an obstacle)
    short_signature_max_length: float = 0.0   # m, candidate of 24.09 (P3 / P4), off (no-go 25.09 on the ride): > 0 = the elevated and floating signatures do not demote a cluster at most this long along the track
    short_signature_max_distance: float = 100.0  # m, ... and at most this far (the organizers' test objects are 0.3-2.2 m long; the platform structure these signatures must keep demoting is 3.9-5.7 m long at ~104 m); docs/P4_AUDIT.md, scripts/short_signature_experiment.py
    # on since 25.09 (SCORECARD #11; pre-registered candidate A, the first of A / B / C to pass the
    # regression gate; false = off): thin objects hanging from above into the envelope near the axis
    # (clustering.find_hanging). The organizers' 5 cm object dips 0.2-0.4 m below the envelope top with
    # 1-3 returns a frame and never reached min_points; linked to its part above the top it is a STOP
    # from 30.1 m (set O 0 -> 15 STOP frames), every other gate row identical, the ride included
    # (docs/evidence/results/p3_thin_hanging_2026-09-25.json)
    hanging_enabled: bool = True
    hanging_max_lateral: float = 0.8   # m, |dy| of the points searched
    hanging_min_height: float = 1.8    # m above the rail head, lowest point searched
    hanging_link_band: float = 0.6     # m above the envelope top in which the linking points are searched (the roof stays out)
    hanging_min_voxels: int = 1        # voxels inside the strict envelope, with at least one more above its top (2: candidate B)
    hanging_max_size: float = 0.5      # m, along and across the track (a cable or rod, not a duct, tray or ceiling)
    hanging_max_distance: float = 60.0  # m; beyond it the rings above the sensor (0.5 deg) are too sparse for a 0.3 m dip
    hanging_needs_rails: bool = True   # on since 25.09, round 2 (the captain's delegate; pre-registered in p3_thin_hanging_2026-09-25.json addendum_rail_lock, both conditions held): the hanging stage runs only on frames whose track model found the rail pair in the near range (track.rail_slabs > 0): 28 of the ride's 29 hanging groups were station column tops in frames without one; set O thin_hanging keeps 15 STOP frames from 30.1 m, the combined gate identical with and without it; false = every frame
    hanging_yield_gauge_only: bool = True   # 26.09 (safety review): a hanging cluster is dropped only for an overlapping cluster of the other stages that is an obstacle (zone 'gauge', no demotion reason); an advisory one there no longer removes it (a cable hanging to 1.85-2.2 m, 0.65-0.75 m off the axis, was demoted as floating and its hanging cluster dropped: no STOP); false = any overlapping cluster
    wall_face_min_height: float = 2.0  # m, taller than a person (1.5 demoted a person standing on a 1.1 m platform edge, review 22.09); taller than this, reaching above overhead_min_height, and its part below that level hugs the corridor edge (|dy| from wall_face_min_inner to beyond wall_face_edge) = wall / portal face pulled in by the axis
    wall_face_min_top: float = 2.8     # m, v0.6: the face reaches above this (just under the 3.0 m envelope top; v0.5 used overhead_min_height = 2.4 under a 3.5 m top)
    wall_face_edge: float = 1.3        # m (v0.6: the advisory zone now ends at 1.40 m; 1.6 with the 1.75 m zone of v0.5)
    wall_face_min_inner: float = 0.3   # m
    visibility_ratio: float = 0.15 # cluster is plausible if n >= ratio * expected points
    # retro-reflective infrastructure (signs, markers, reflectors): intensity is reflectivity %, > 100 = retro
    retro_intensity: float = 0.0       # intensity from which a return counts as retro-reflective; 0 = rule off (v0.5 default: the rule never fired on the six bags, < 1 % of returns reach 100, and it demoted an injected trolley of reflectivity 110 at 13-24 m; set 100 to enable)
    retro_min_fraction: float = 0.5    # fraction of retro returns for a cluster to count as a reflector
    retro_max_height: float = 1.2      # m, taller retro clusters (a person in a hi-vis vest, a train) are kept
    retro_max_width: float = 0.8       # m, narrower retro clusters (plate, sign, marker, post) are demoted to advisory


@dataclass
class AccumulationConfig:
    """Ego-motion compensated accumulation of far corridor candidates over several frames."""
    enabled: bool = True           # merge only with a trustworthy speed: a given one (node parameter / odometry, eval sequences) or, with estimate_speed, the estimator
    n_frames: int = 5              # frames merged (the current one included)
    min_range: float = 40.0        # m, only candidates beyond this range are accumulated (near objects stay single-frame)
    min_points_scale: float = 0.3  # per accumulated frame the voxel-count thresholds grow by this fraction (x1.5 at 5 frames)
    estimate_speed: bool = False   # v0.5 default off: the estimated-speed merge added 31 false-alarm frames on the five empty bags at full rate (119 vs 88, 21.09) and no real-data recall, and costs 7-8 ms per real frame; the synthetic gain (person 189 vs 178 m) is documented; true = the v0.4 behaviour
    speed_min_confidence: float = 0.5  # below this the estimate is not used: source 'none', no accumulation
    speed_max: float = 30.0        # m/s, search range of the estimator (metro line speed limit is ~22 m/s)
    speed_max_step: float = 3.0    # m/s, larger frame-to-frame jumps of the estimate halve its confidence
    speed_warmup_frames: int = 3   # frames the estimator observes before it reports (static-pattern background)
    tracks_min_speed: float = 1.0  # m/s, the tracks cue reports nothing below this: a stopped train must not merge frames (a person walking across the track smears laterally; 21.09 review)
    min_speed: float = 1.0         # m/s, below this (given or estimated) nothing is merged: a stopped train gains no density from identical frames but loses marginal objects to the scaled thresholds (P4 static sets, 21.09)
    smear_max_length: float = 2.0  # m, an accumulated cluster longer than this along X falls back to its current-frame points
    smear_max_width: float = 1.0   # m, the same guard across the track (a moving object merged over 0.5 s); 0 = off
    max_points_per_frame: int = 20000  # cap on stored far candidates per frame (strided subsample above)
    stamp_dt_range: Tuple[float, float] = (0.02, 0.5)  # s, stamp differences outside are replaced by tracking.frame_dt


@dataclass
class TrackingConfig:
    gate_base: float = 1.5         # m, association gate at range 0
    gate_per_m: float = 0.02       # m per metre of range
    ego_speed_max: float = 25.0    # m/s, obstacles approach at most this fast (no odometry)
    frame_dt: float = 0.1          # s
    confirm_hits: int = 3          # consecutive frames before an obstacle is reported
    low_confirm_hits: int = 5      # v0.6: hits before a low (bed-level) object is reported: it is static and in view for seconds, while rail-area clutter flickers for 2-3 frames
    confirm_time_s: float = 0.5    # s of sensor time a track must have been observed (frames x interval, first frame included: 0.5 s = 5 frames at 10 Hz, v0.6.2; 0.3 = 3 frames, the v0.3-v0.6.1 persistence); applied when the caller supplies the frame interval (the Detector does); 0 = hits only
    hit_window: int = 10           # frames of a track's recent history kept for min_hit_fraction
    min_hit_fraction: float = 0.6  # a track must have been matched in this share of its last hit_window frames (flickering structures are not reported); 0 = off
    zone_window: int = 10          # hits over which the zone (gauge / advisory) is decided (5 in v0.3)
    zone_min_fraction: float = 0.6 # share of those hits inside the strict gauge for the track to be an obstacle (0.5 = majority, v0.3)
    column_hold: int = 2           # 25.09: a track whose cluster was demoted as a column (cluster.column_*) in at least this many of its last zone_window hits is advisory: a column far away shows more than column_min_height of itself in some frames only (roundT_doubleT, EXPERIMENTS.md 3a; 2 = the highest pre-registered candidate that passed, docs/evidence/results/column_hold_2026-09-25.json); 0 = off
    max_misses: int = 3            # frames a track survives without a match
    hold_misses: int = 1           # frames a reported track stays reported without a match (at its predicted distance): one missed frame does not drop a STOP (review 23.09); 0 = the v0.6.2 behaviour
    reseed_hold: int = 5           # 26.09 (safety review; a fixed window since the re-review of 26.09): after a mount-calibration change the tracks are rotated into the corrected frame, and a track reported in zone gauge (a STOP) at that moment stays reported for a window of this many frames from the change (the change frame the first; from its last match if it was already missing at the change), matched or not: a match refreshes the track but does not end the window (it did, so a loss from the frame after the change was not covered); when the change re-seeds the track model the window lasts at least until the model has its floor-shadow reference again (1 + ceil(track.axis_warmup_frames / periods) frames: 6 at 10 Hz, 4 at 5 Hz); a missed frame in the window is reported at the predicted distance and not counted against the track: the geometry re-seed must not drop a confirmed STOP; on a change above 1 deg only such tracks are kept (the others dropped, as the reset did); a new orientation still resets the tracker; 0 = the tracker is reset on a change above 1 deg and nothing is held
    low_min_seen_distance: float = 0.0  # tried 26.09 (P3 start-up, candidate c), NOT shipped: m; a low (bed-level) track is reported only once it has been matched at or beyond this distance; 4 m removed a fresh start's STOP on the rail heads 3.0-3.6 m ahead of a standing train but never reports a real low object that stays within 4 m (standing train, or one that falls there): a blind zone; 0 = off
    conf_gain: float = 0.35        # confidence added per hit
    conf_decay: float = 0.25       # confidence removed per miss
    conf_threshold: float = 0.6    # report obstacles with confidence >= threshold

    def frames_to_confirm(self, frame_dt: float | None = None) -> int:
        """Consecutive frames a static, always-matched object needs before it is reported
        (the larger of ``confirm_hits`` and ``confirm_time_s`` in frames, first frame
        included): 5 at 10 Hz with the defaults."""
        dt = self.frame_dt if frame_dt is None else frame_dt
        by_time = int(math.ceil(self.confirm_time_s / dt - 1e-9)) if (self.confirm_time_s > 0 and dt > 0) else 0
        return max(self.confirm_hits, by_time)


@dataclass
class LowObjectConfig:
    """Low foreign objects on the bed (v0.6, ``resense/lowobj.py``): bumps above the learned
    track-bed cross-section, below the gauge polygon bottom (organizers' size criterion
    300 x 300 x 100 mm)."""
    enabled: bool = True
    half_width: float = 1.05           # m, |dy| of the search band (the train envelope)
    min_excess: float = 0.05           # m above the local bed template (a 10 cm object lying on a rail head clears it by ~5 cm)
    max_excess: float = 1.0            # m
    min_top: float = 0.0               # m above the rail head the top of a low cluster must reach: the bed is full of fixtures 5-40 cm tall that stay below the rail head by design (EXPERIMENTS.md §1d); -1 = any bump above the bed
    min_point_top: float = 0.03        # m above the rail head every low candidate point must be (the rail-area fixtures - guard rails, joints, fastenings - reach the rail-head level; a candidate must rise above it); -1 = off
    template_range: Tuple[float, float] = (4.0, 30.0)   # m along track where the cross-section is learned
    template_bin: float = 0.025        # m lateral bin of the template
    template_percentile: float = 30.0  # per-bin percentile of the height (the bed surface)
    template_min_points: int = 12
    template_dilate: float = 0.05      # m, max-filter of the template (rail heads and flanks belong to it)
    template_smoothing: float = 0.8    # EMA of the template across frames
    local_bin: float = 2.0             # m along-track bin of the local bed offset
    local_min_points: int = 5          # bed returns per bin for the bin to count as observed
    range_max: float = 60.0            # m, the bed is observed at grazing incidence: beyond this nothing is reported
    foot_max_top: float = 0.35         # m, a low cluster with corridor points higher than this above it is the foot of something taller (the corridor stage decides)
    eps: float = 0.2                   # DBSCAN radius of the low candidates (range-normalised like cluster.eps: 0.48 m at 56 m)
    min_points: int = 3                # voxels of a low cluster
    min_height: float = 0.0            # m, vertical extent of a low cluster (0: a flat top face at close range is enough, its excess over the bed is the height)
    max_length: float = 1.5            # m along the track (rails, guard rails, cables and ducts are longer)
    min_length: float = 0.0            # m along the track; used by the compact near-bed opt-in path
    max_width: float = 2.2             # m across the track: the envelope is 2.1 m wide (v0.6.2: 1.6 m rejected a person lying across the track, EXPERIMENTS.md §2d)
    min_width: float = 0.15            # m, a low cluster narrower than this across the track is a rail-head sliver / fastening
    straddle_enabled: bool = True      # v0.6.2: objects straddling the envelope floor (lowobj.py step 4)
    straddle_min_top: float = 0.10     # m above the rail head the top of such a cluster must reach (rail fittings reach 1-8 cm)
    straddle_band: float = 0.30        # m above the envelope floor from which corridor points join that clustering
    straddle_min_width: float = 0.35   # m across the track: trackside devices beside a rail (train stops, lubricators,
                                       # signalling) are mounted along it and narrow across it; an object lying across
    straddle_max_length: float = 0.8   # m along the track      a rail is wide across it and short along it
    near_enabled: bool = False         # opt-in: real-ride false-positive cost has not been measured
    near_range: float = 30.0           # m, only where the cross-section is learned from dense returns
    near_half_width: float = 0.55      # m from the track axis; rail heads/fastenings are near +-0.8 m
    near_min_excess: float = 0.05      # m above the local bed; shape gates reject flat infrastructure
    near_min_width: float = 0.24      # m observed width; a ray-cast 0.30 m box is ~0.245 m at 20 m
    near_max_width: float = 0.55      # m; wider patches are bed/structure, not a compact object
    near_min_length: float = 0.0      # m observed along-track extent; a 30x30x10 cm box at 12-28 m is one scan line (~0.03 m)
    near_min_height: float = 0.0      # m; top-surface returns may have zero observed vertical extent
    near_min_bed_lateral_bins: int = 20  # support must span the central bed, not only the object footprint
    near_min_points: int = 5          # distinct occupied voxels; that box returns 5-10 at 12-28 m (10 rejected it)
    near_max_length: float = 0.75     # m along track; reject cables, guard rails, long drain covers
    # 26.09 (P3 start-up, docs/evidence/results/p3_startup_2026-09-26.json), candidates a / b:
    pending_advisory: bool = False       # (a) while the mount calibration is 'pending' a confirmed low track beyond pending_advisory_within is advisory (reason 'calibration_pending'), not STOP
    pending_advisory_within: float = 0.0  # m; (a) a low track at most this far stays a STOP
    min_model_age: int = 0               # (b) a low track does not become a STOP while the track model is younger than this (frames since its (re)seed); one already reported stays; 0 = off


@dataclass
class CalibrationConfig:
    """Automatic mount calibration (v0.6, ``resense/calibration.py``): sensor orientation, roll,
    pitch and a large mount yaw measured from the rails and the bed in the first frames."""
    enabled: bool = True
    frames: int = 20               # observations (frames with a rail pair) whose median roll / pitch / yaw is frozen
    obs_spacing: int = 10          # frames between those observations (20 x 10 = 20 s: a moving train's cant and lean average out)
    provisional_frames: int = 5    # the first observations, for a provisional correction ...
    provisional_min_deg: float = 2.5   # ... applied only for a clearly tilted rig (larger roll or pitch)
    max_frames: int = 400          # give up (keep the configured mapping, report 'fallback') after this many frames
    search_orientations: bool = True   # try other axis-aligned orientations when the configured mapping shows no rails
    keep_up_axis: bool = True      # only orientations whose up axis is the configured one, upright or inverted (8 of 24):
                                   # a spinning LiDAR is mounted with its spin axis vertical; false = all 24 (a flat
                                   # tunnel wall with cable trays then competes with the bed, EXPERIMENTS.md section 6)
    orientation_votes: int = 2     # frames on which the same candidate orientation must win before it is adopted
    min_rail_score: float = 0.05   # m, ridge prominence of the rail pair (as track.rails_min_score)
    apply_min_deg: float = 0.75    # roll / pitch corrections below this are not applied: 1.5x the p90 error of the 20-observation median on a moving train (0.5 deg; at 0.5 a noise-level +0.51 deg roll was applied on a ride piece and added 6 false events, review 23.09)
    min_yaw_deg: float = 3.0       # the mount yaw is corrected only above this (the track model follows smaller / dynamic yaw, and the rails' tangent at the sensor includes the chord angle of the car in a curve)
    max_tilt_deg: float = 15.0     # larger roll / pitch estimates are rejected as implausible
    monitor_period: int = 50       # frames between drift checks after freezing; 0 = off
    drift_warn_deg: float = 1.5    # residual tilt (median of the last checks) that raises a health warning
    drift_window: int = 10         # checks in that median (10 x 50 frames = 50 s: a curve is not a drift)
    time_cadence: bool = True      # on since 25.09 (P3, SCORECARD #13): obs_spacing, monitor_period and max_frames count nominal frame periods (tracking.frame_dt) at the input rate from the stamps, not processed frames, so 5 Hz calibrates in the same 20 s as 10 Hz (the 20 x 10-frame window took 40 s at 5 Hz and never completed on a 25 s bag); false = processed frames
    refine_min_deg: float = 0.0    # OFF since 26.09 (safety review of round 2; docs/evidence/results/p3_round2_review_fixes_2026-09-26.json): while a provisional tilt is applied (at least provisional_frames spaced observations), the tilt the final would set from the spaced observations so far replaces it when it differs by at least this (deg) in roll or pitch. On 0.5 in round 2 (25.09: +3 deg roll five bags 16 / 17 -> 11 / 13, the first 5 consecutive frames of roundT_doubleT are 1.6-2 deg off in roll), but a refined tilt costs a STOP frame of doubleT_obstacle that the provisional one keeps (5 Hz, rig (0, -1.5 deg): frame 182, in every refinement variant tried) and each refinement re-seeded the track model; 0 = off
    provisional_per_axis: bool = False  # 25.09 (P3), tried, not shipped: the provisional tilt corrects roll and pitch each only when that axis reaches provisional_min_deg (+3 deg roll / pitch five bags 11 -> 19 / 16 -> 19 events on top of the other flags); false = both when either does
    keep_within_deg: float = 0.25  # on since 25.09 (P3): a final tilt within this (deg, roll and pitch) of the applied provisional one keeps the applied correction: no re-seed of the track model for a change below the final's own error (doubleT_obstacle: +3.02 / -0.88 over +3.18 / -0.81 re-seeded and lost frame 191; 185 -> 186 labelled hits); 0 = off
    # 26.09 (safety review of the round-2 items; docs/evidence/results/p3_round2_review_fixes_2026-09-26.json)
    refine_raw_trigger: bool = False  # tried 26.09 (candidate C1), not shipped: each axis triggered by its RAW median moving refine_min_deg from the one behind its applied value, the other axes kept; it kept noise-level provisional values the final would zero (+3 deg roll five bags 11 / 13 -> 14 / 16 events / STOP episodes); false = the shipped trigger (the zeroed target against the applied tilt, all axes replaced)
    refine_confirm_obs: int = 2       # 26.09 (safety review): spaced observations in a row on which the refinement condition must hold before it is applied (1 = at once): a one-off move of the 5-observation median (doubleT_obstacle 5 Hz, rig +2 / +2 deg: roll 1.19 -> 1.69, the final 1.15) is not applied
    refine_max: int = 1               # 26.09 (safety review): refinements per calibration (0 = unlimited): the correction cannot flap (a median hovering at apply_min_deg re-seeded the track model 4 times on roundT_doubleT +3 deg pitch); the final follows
    reseed_keep_max_deg: float = 1.0  # a correction change up to this (deg) keeps the track model: it is rotated into the corrected frame (bed, rail head, axis, age and the floor-shadow reference kept) instead of re-seeded from nothing, and the accumulation buffer is kept; larger changes and a new orientation re-seed; 0 = always re-seed (a sub-degree refinement re-seeded the model and lost a confirmed STOP on doubleT_obstacle for 2 frames)


@dataclass
class HealthConfig:
    """Production guards (v0.6, ``resense/health.py``): input sanity, visibility, track lock,
    latency budget. They never change a detection; they set ``health.level`` and the
    monitored (verified-clear) range."""
    min_points: int = 20000        # valid returns per frame below which the input is a fault
    low_points_fraction: float = 0.5   # warn when a frame has fewer than this share of the running median
    near_range: float = 2.5        # m, returns closer than this are window dirt / the train's nose
    max_near_fraction: float = 0.2 # warn when more than this share of the returns is that close (blocked / dirty window, spray)
    min_visibility: float = 60.0   # m, warn when the tunnel ahead is visible less far than this
    sector_deg: float = 10.0       # azimuth sectors for the blockage check (central +-30 deg)
    lock_window: int = 20          # frames over which the rail lock rate is computed
    min_lock_rate: float = 0.3     # warn below this share of frames with a rail pair
    latency_budget_ms: float = 100.0   # warn when the p95 of the recent frames exceeds it
    latency_window: int = 50
    # 26.09 (judgements of 24.09 and 26.09): a latency p95 over the budget is a health warning
    # (level, messages, /resense/health, the status JSON) but no longer turns GO into CAUTION on
    # /resense/decision - on a loaded machine it did on most frames (set O 690 of 1 510). STOP,
    # FAULT and every other warning are unchanged. true = the v0.6 behaviour
    latency_affects_decision: bool = False
    # 25.09 (SCORECARD §6 row 6, docs/evidence/results/p3_clear_distance_2026-09-25.json): cap the
    # verified-clear distance at the nearest candidate of this frame that touches the envelope
    # although it is not a confirmed obstacle (unconfirmed, advisory); never changes a detection
    # or the decision. false = clear_distance counts confirmed obstacles only (v0.6). On since
    # 25.09, round 2, candidate R1 (the sub-parameters below), shipped by the captain's delegate
    # although it MISSED its pre-registered clutter limit: set O overclaim 172 -> 82
    # object-frames, but the median clear distance of the five obstacle-free recordings -5.5 %
    # (limit -5 %), the ride -3.1 % (1.49 % of the frames under 60 m); EXPERIMENTS §1i
    clear_cap: bool = True
    clear_cap_min_gauge: int = 1       # voxels of the cluster inside the strict envelope (Cluster.n_gauge, edge margin applied)
    clear_cap_min_hits: int = 1        # frames the cluster's track has been matched, this one included
    clear_cap_margin: float = -1.0     # m; >= 0: a cluster also touches with a point of this frame inside the envelope widened laterally by this (no edge margin); < 0 = n_gauge only
    clear_cap_points: int = 0          # > 0: also cap at the X of the k-th nearest strict-envelope corridor return of the frame (low candidates excluded); 0 = off
    clear_cap_skip_columns: bool = True    # a cluster demoted as a column (or its track held advisory by tracking.column_hold) does not cap (round 2; false = round 1)
    clear_cap_lost: bool = True            # 26.09 (safety review): also cap at the predicted distance of a track that was reported when it was last matched and missed this frame (until the tracker drops it after tracking.max_misses), so a lost STOP does not turn into a long verified-clear distance; false = this frame's clusters only


@dataclass
class DetectorConfig:
    sensor: SensorConfig = field(default_factory=SensorConfig)
    track: TrackConfig = field(default_factory=TrackConfig)
    gauge: GaugeConfig = field(default_factory=GaugeConfig)
    cluster: ClusterConfig = field(default_factory=ClusterConfig)
    tracking: TrackingConfig = field(default_factory=TrackingConfig)
    accumulation: AccumulationConfig = field(default_factory=AccumulationConfig)
    lowobj: LowObjectConfig = field(default_factory=LowObjectConfig)
    calibration: CalibrationConfig = field(default_factory=CalibrationConfig)
    health: HealthConfig = field(default_factory=HealthConfig)
    voxel: float = 0.0             # optional voxel downsampling of corridor candidates (0 = off)

    # ---- (de)serialisation -------------------------------------------------
    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "DetectorConfig":
        cfg = cls()
        for section in ("sensor", "track", "gauge", "cluster", "tracking", "accumulation", "lowobj", "calibration", "health"):
            if section in d and d[section]:
                obj = getattr(cfg, section)
                for k, v in d[section].items():
                    if not hasattr(obj, k):
                        raise KeyError(f"unknown parameter {section}.{k}")
                    if k == "profile":
                        v = [tuple(p) for p in v]
                    elif isinstance(getattr(obj, k), tuple):
                        v = tuple(v)
                    setattr(obj, k, v)
        if "voxel" in d:
            cfg.voxel = float(d["voxel"])
        return cfg

    @classmethod
    def from_yaml(cls, path: str) -> "DetectorConfig":
        with open(path, "r", encoding="utf-8") as fh:
            d = yaml.safe_load(fh) or {}
        return cls.from_dict(d.get("resense", d))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_yaml(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            yaml.safe_dump({"resense": self.to_dict()}, fh, sort_keys=False, allow_unicode=True)
