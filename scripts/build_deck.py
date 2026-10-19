#!/usr/bin/env python3
"""Fill the organizers' presentation template with the ReSense deck.

The template (37 slides, Montserrat, "Лидеры цифровой трансформации 2026") is exported from
Google Slides:

    curl -L -o template.pptx \\
      https://docs.google.com/presentation/d/17ciElVAWgeuPLiFHw7y5HMaAXmTo7g16/export/pptx
    python scripts/build_deck.py --template template.pptx --out docs/presentation/ReSense_LCT2026.pptx

Slides 7-11 (title, team, team cards, history, solution in short) keep their design and
structure as the organizers require; the solution slides use the template's own layouts
(12-29). Every measured number on the slides and in the speaker notes is written once: the numbers the
regression gate measures in ``GATE`` (one block at the top, the final gate of the
shipped detector; ``--check-gate <baseline.json>`` lists what differs from another gate), everything else in ``N``,
each with its source and, for timings, its machine: the node checks of 29.09
(docs/evidence/frame111_2026-09-29), the 28.09 VM and judgement timings, and older dated measurements
(docs/archive/EXPERIMENTS_log_2026-09.md, docs/archive/P4_AUDIT.md), which the slides date; the texts
derive the rest (per km, ranges, counts). The build refuses a deck with a ``<...>`` field on any slide.
The pictures are made by ``scripts/hero_view.py`` and ``resense run --render`` (``docs/img/``) and by
the web UI's gallery (``docs/images/``; paths in ``IMG``).

The PDF next to the deck is LibreOffice's export (Impress and the Montserrat fonts installed):

    soffice --headless --convert-to pdf --outdir docs/presentation docs/presentation/ReSense_LCT2026.pptx

PT1's word budget is enforced on every build: at most 80 visible words per slide and 1,100 total,
including chart labels, units and axis ticks. Speaker notes keep the technical detail. Audit a deck:

    python scripts/build_deck.py --audit docs/presentation/ReSense_LCT2026.pptx

Without ``--team`` the team slides show the four roles P1–P4 and what each owns (README "Team"),
with no ``<...>`` field; the build refuses a deck with one. With ``--team`` the same deck carries the
names and photos on slides 2–3 (P2's layout of 29.09). The team approved the named deck as the
committed one on 29.09; ``team.json`` and the photos stay outside git (``docs/presentation/private/``
is git-ignored):

    python scripts/build_deck.py --template template.pptx --team docs/presentation/private/team.json \
      --out docs/presentation/ReSense_LCT2026.pptx

``team.json`` holds the keys of ``TEAM`` below; photo paths are relative to the JSON file. A named
build requires the captain, the captain's specialty and, for each of the four cards, a name and a
photo; ``nick``, ``study``, ``study_short``, ``city``, ``formed`` and ``team_photo`` are shown when
given. Placeholder text (``<...>``) is rejected.

Without the template or team.json, the committed named deck is updated in place: ``--refresh`` runs the
same slide functions on it and re-writes the texts, charts, the demo picture and the notes of slides
4-16; the title and the team slides (names, photos) stay as built. Slides whose text did not change come
out semantically identical (checked 19.10 on slides 1-4, 6 and 9):

    python scripts/build_deck.py --refresh docs/presentation/ReSense_LCT2026.pptx

The deck of 19.10 shows the version 1.2.0 (``V12``), the second lidar (``FALCON``), the range by track
shape (``RANGE``) and the gauge display (``GAUGE``); those blocks name their sources.

Needs ``python-pptx`` (``pip install python-pptx``); not part of the runtime image.
"""
from __future__ import annotations

import argparse
import copy
import os
import re

from lxml import etree
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.util import Emu, Pt

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IMG = {
    "hero_person": "docs/img/hero_person.png",        # hero_view.py doubleT_obstacle --frame 24
    "hero_object": "docs/img/hero_object.png",        # hero_view.py doubleT_obstacle --frame 160
    "hero_ride": "docs/img/hero_ride.png",            # hero_view.py on a straight of new_data
    "ride_clean": "docs/img/hero_ride_clean.png",     # the same frame with --no-hud (data slide background)
    # the current web UI (docs/images/README.md): its cab view replaying the node's own /resense/status
    # from the Docker dry run on doubleT_obstacle; docs/img/ keeps the renders the scripts write
    "dashboard": "docs/images/dashboard-cab-real.png",
    "render": "docs/img/doubleT_obstacle_0024_v062.png",   # resense run --render, frame 24
    "chain": "docs/img/docker_chain_rviz.jpg",       # docs/video/docker_chain_rviz.mp4 at 35 s
    "logo": None,                                     # the template's own "Московский транспорт" logo
}


def metres(x):
    """A distance on a slide: whole metres, half up (52.5 -> 53)."""
    return int(x + 0.5)


# ==== FINAL — the numbers the regression gate measures, ALL of them here and nowhere else.
# The final gate of the shipped detector (29.09 night: explained_run and the ego veto on, the shell rule off
# after the safety review; seal docs/evidence/detector_freeze_2026-09-29_shell_off.json; 1 cm frame cache;
# docs/evidence/cycle_2026-09-29/shell_off/gate.json = the newest baseline below). A later gate: put its value
# into each line (the comment names the key), set GATE_RUN / GATE_SOURCE, rebuild; `build_deck.py
# --check-gate <baseline.json>` lists every line that differs, with the value to write. Everything below GATE
# derives from it (per km, "без пропусков", ranges, chart bars); the web/demo deck test pins the same keys.
GATE_RUN = "7464d80 (shell off)"
GATE_SOURCE = "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json"
# D1/PT1 pass 1 context, not J1's still-pending measurement of the next released seal.
# docs/evidence/judgement_2026-10-13/README.md §§3,5: node-faithful raw decode, whole ride in order;
# Docker node latency is separate from offline decode+detect and from end-to-end result age.
JUDGE = {"date": "13.10", "ride_episodes": 32, "ride_km": 13, "node_360_p95_ms": 111, "vcpus": 4,
         # §3: false STOP episodes in all obstacle-free data (five bags + ride), its seconds; CAUTION share;
         # §5: the node's 120° p95
         "empty_episodes": 36, "empty_s": 1430, "caution_pct": 43, "node_120_p95_ms": 84}
GATE = {
    "empty_events": 8,               # five_empty.alarm_events
    "empty_episodes": 12,            # five_empty.stop_episodes
    "ride_events": 27,               # ride.alarm_events            (per km = / 13, derived)
    "ride_episodes": 30,             # ride.stop_episodes
    "obstacle_stop": (193, 201),     # recordings.doubleT_obstacle.alarm_frames, .frames
    "obstacle_first_frame": 8,       # recordings.doubleT_obstacle.first_alarm_frame
    "person": (61, 61),              # recordings.doubleT_obstacle.labelled.per_label.person_crossing hits, frames
    "rail_object": (126, 126),       # ... .per_label.object_on_rail_from_frame_75 hits, frames
    "set_o_inside": (8, 8),          # set_O.inside_objects_with_stop, .inside_objects
    "set_o_outside": (6, 142.3),     # set_O.outside_false_stop_frames, .objects.big_outside.false_stop_from_m
    # set_O.objects.<key>: (first_stop_m, stop_frames, visible_frames, held = no missed_interval after
    # first_stop_frame, i.e. a STOP on every frame from the first STOP on)
    "set_o": {
        "big_above": (111.4, 56, 124, True),
        "big_center": (98.0, 208, 213, True),
        "long_low_on_rails": (87.2, 52, 86, True),
        "small_on_rail": (42.7, 23, 49, True),
        "small_center": (55.8, 32, 79, True),
        "small_edge_inside": (35.0, 18, 83, True),
        "big_edge_inside": (18.3, 7, 125, False),
        "thin_hanging": (30.1, 15, 42, True),
    },
    # set_F_straight.kinds.<kind>.first_detection_median_m
    "set_f": {"person": 151.0, "box1.0": 123.9, "trolley": 151.4, "cable": 98.9},
    "bed_box_found": (2, 6),         # set_F_straight.kinds.box0.5.detected, .sequences
}
# re-measured on the final commit, not by the gate: `python3 -m pytest -q` (29.09 night, the final branch: 1 284 pass,
# plus 74 web/demo dashboard tests); the deck test (web/demo/test_web.py) asks >= 667
TESTS = "1 284"
# ==== end of FINAL

# ---- every other measured number on the slides and in the speaker notes; each is written here once and
# the slide texts, charts and notes read it through the helpers below. Sources: GATE above, the cycle
# record docs/archive/QUALITY_CYCLE_2026-09-27.md (the held-out checks of the 27.09 detector),
# docs/evidence/cycle_2026-09-29/competitor_rules/gate_table.md (f_base: the detector before the rules of
# 29.09), docs/archive/EXPERIMENTS_log_2026-09.md "Current results" (§0, §2d, §2e, §3, §9),
# docs/archive/P4_AUDIT.md, docs/ARCHITECTURE.md "Native kernels", "GPU: evaluated, not used" ---------------
# The shipped detector: the 27.09 seal + PR #27/#28 (frame 111, thin_far 4 -> 3) + two false-alarm rules
# after other teams' case 5 solutions, on by default since 29.09 evening (tracking.explained_run,
# tracking.ego_veto_min_speed). The third, cluster.shell_min_top, was on from PR #29 and is off since
# a5455b3 (our safety review: it demoted floor-to-vault obstacles beyond 40 m)
N = {
    # the organizers' real recordings [real]: six recordings and the 20-minute ride (13.0 km)
    "frames_six": 2488, "frames_ride": 11271, "ride_km": 13,
    # doubleT_obstacle: the person crossing (GATE), the first alarm's delay after the person enters the
    # envelope (first_alarm_frame against the label's first frame inside, 8, at 10 Hz; 0 = on the first
    # frame inside), the largest distance error; the object on the rail after the person leaves (frame 75
    # on; GATE, 125 of 126 on 27.09), and v0.6.1's own hits on it before the object was clustered whole
    # (history); the person's distance at the STOP (the hero render, frame 24: 55.8 m; the Docker
    # dashboard run: 56.1 m)
    "person": GATE["person"], "person_delay_s": 0.0, "person_err_m": 0.23, "person_m": 56,
    "rail_object": GATE["rail_object"], "rail_object_v061": 2,
    # the whole recording: STOP frames of all frames, and the first STOP frame (GATE). With r_1e2ed82: from
    # frame 8 to the end with no gap, also offline on the original recording and through the ROS node in
    # Docker (CI run 36547463949, cold and warm; docs/evidence/frame111_2026-09-29). The 27.09 detector
    # gave 190 of 201 with a GO at frame 111 and CAUTION at 117 and 197; tracking.stop_keep_low_s 0.3
    # (PR #27, tuned on this recording) closed it
    "obstacle_stop": GATE["obstacle_stop"], "obstacle_first_frame": GATE["obstacle_first_frame"],
    # the person with the envelope from the rails alone (gauge.reference 0; quality-cycle screens of 27.09,
    # docs/organizers/answers.md §9): the gain to 61 is entirely the sensor-axis addition (the union, at
    # most 0.2 m wider within 60 m on straight track). The organizers measure the envelope from the rail
    # heads (their answer of 29.09); the union never narrows it
    "person_rails_only": 58,
    # false alarm events (ride / five empty recordings), in-sample: the rules and the track opinion's
    # negatives come from these recordings; the per-km figures are derived (/ ride_km). GATE (the
    # current detector) and, before the rules of 29.09, f_base (gate_table.md, the 27.09 seal + PR #27/28);
    # STOP episodes (GATE; the independent judgement counts episodes)
    "ride_events": GATE["ride_events"], "empty_events": GATE["empty_events"],
    "ride_events_before": 32, "empty_events_before": 11,
    "ride_episodes": GATE["ride_episodes"], "empty_episodes": GATE["empty_episodes"],
    # the rules of other teams' public case 05 solutions screened on 29.09 through the full gate: shipped
    # (explained_run, shell, ego veto) and rejected (lowobj.min_top 0.08, the clean run with range demotions
    # or shape signatures, fresh_stop_evidence, the quadratic edge margin, far ring rails) — CAPTAIN.md,
    # CHANGELOG; the shell rule then switched off by our safety review (a5455b3): the catalogue hanging
    # cable cable_low in the ray-cast tunnel at 22 m/s, first STOP with shell on / off, m
    "rules_tried": 8, "rules_rejected": 5, "shell_cable_m": (21, 74),
    # the ride held out, measured on the 27.09 detector (before the three rules; not re-measured since):
    # each pair of ride pieces run with an opinion model trained without them (cross-fitting): ride
    # events with the opinion off (the rules alone) -> with the held-out model
    "ride_cv": (43, 37),
    # the threshold is half the highest that delays no held-out synthetic object (a 2x margin); with no
    # margin the ride would give (in-sample, held-out) events on the 27.09 detector: kept for safety
    "ride_zero_margin": (25, 33),
    # ablations of the shipped code, one key off at a time: the far evidence off: first STOP of the box
    # at the envelope top and of the plank, m; the envelope reference off: the edge cube's first STOP, m
    # (the person: person_rails_only; the opinion off: ride_cv[0])
    "nofar_first": (101, 82), "noref_edge_cube_m": 5.2,
    # its bounds: at most this many processed frames of delay over a track's whole life
    # (tracking.doubt_extra_hits, resense/tracking.py _doubt: a withheld frame spends the budget, also
    # over a miss): ~1 s at 10 Hz, ~2 s at 5 Hz, up to ~3 s while the node works through a backlog
    # (catchup_step: 0.3 s of recording between processed frames); never within opinion_near_m (also
    # while the track is missed, at its predicted distance), never for a standing body (a cluster at
    # least body_m tall) within body_near_m
    "opinion_budget": 10, "opinion_catchup_s": 3, "opinion_near_m": 25, "opinion_body": (1.0, 40),
    # clear-scene false STOP and processing history: STOPs in the captured node histories, STOP events
    # of the history stress (the captures plus seeded dropped-frame / catch-up / offset / dither runs)
    "history_captured": (2, 0), "history_stress": (78, 55),
    # the organizers' own synthetic obstacles, set O (cloud_with_fake_obj: 10 objects, 1 510 frames, the
    # train drives up to them at 1.4–20 m/s, no speed given) [organizers' synthetic]. The eight objects
    # inside the envelope in the chart's order: gate key -> (chart name, then GATE's first STOP m, STOP
    # frames, visible frames, held: a STOP on every frame from the first STOP on (pink) or not (violet)).
    "fake_frames": 1510,
    "set_o": {key: (name,) + GATE["set_o"][key] for key, name in (
        ("big_above", "ящик 2 м: верх"),
        ("big_center", "ящик 2 м: центр"),
        ("long_low_on_rails", "доска"),
        ("small_on_rail", "куб 0,3 м: рельс"),
        ("small_center", "куб 0,3 м: центр"),
        ("small_edge_inside", "куб 0,3 м: край"),
        ("big_edge_inside", "ящик 2 м: край"),
        ("thin_hanging", "висящий 5 см"),
    )},
    # STOP on the 2 x 2 m box outside the envelope (big_outside): on the gate's cache GATE set_o_outside
    # (frames, from m). On the original recording the 27.09 detector gave 9 frames (563-571, 126-142 m),
    # identical offline and through the node (the 28.09 re-judgement's set O runs,
    # docs/evidence/judge_outputs_2026-09-28 offline/seto_offline and node_set_o, counted per frame by P2):
    # frames whose decision is STOP with a detection on the box's inner edge; scripts/score_fake_objects.py
    # credits 7 of them (in frames 569-570 the detection is 2-3 cm beyond its 1 m lateral tolerance)
    "fake_outside_false": GATE["set_o_outside"][0], "fake_outside_from_m": GATE["set_o_outside"][1],
    "fake_outside_orig": 9, "fake_outside_m": (126, 142),
    "fake_background": 0,             # alarm frames matching no object (score_fake_objects.py background)
    # the edge box's own track STOPs from here; the scorer, matching within 1 m of the centre of the
    # 2 m-wide box, credits the 7 frames from 18.3 m above
    "edge_box_track_m": 28.7,
    # the diagnostic overclaims: frames with an in-envelope object whose decision is GO with the
    # monitored range past it (final_acceptance.json, set_O_candidate target_by_decision GO)
    "overclaim_go": (46, 16),
    "axis_angle": "−0,24°",           # the rails against the sensor axis, the frame the organizers placed from
    # beyond this range a track may start from this many voxels; STOP only while it approaches on a
    # line, advisory (reported, never hidden) otherwise
    "far_weak": (60, 4),
    # gauge.reference 3, the union: within this range on straight track a return is also inside when it
    # is inside the envelope measured from the sensor axis (the offset clamped to axis_shift_m); it
    # takes the sensor-axis lateral only where that is nearer the centre, so the rails' envelope is
    # nowhere narrowed
    "axis_near_m": 60, "axis_shift_m": 0.2,
    # the pre-registered placement study (72 cases: four set O objects' own points at new places on the
    # five empty recordings and the ride, paired controls) [organizers' synthetic, held out]: matched
    # target frames before -> now, of the visible ones; cases with a match; paired-control matches.
    # (the final detector's run, plan registered in d572807, identical per case to the earlier runs; with
    # gauge.reference 0, the rails alone: 722)
    "novel_frames": (544, 723, 2458), "novel_cases": (45, 72), "novel_controls": 0,
    # set F: our objects ray-cast into the moving ride, straight track, first confirmed detection, median
    # of 6 approaches: person, trolley, crate and cable from GATE (set_F_straight, legacy placement;
    # identical from 27.09 to r_1e2ed82); the 30 cm box on the rail head and the object across the rail
    # from round 3 (24.09, not in the gate); the anchored person: round 4, 5 pairs, 150 m in the same
    # pairs with the legacy placement [synthetic in real frames, EXPERIMENTS §2d, P4_AUDIT]
    "set_f": {
        "person_anchored": ("человек 1,7 м · от рельсов", 154),
        "person": ("человек 1,7 м", metres(GATE["set_f"]["person"])),
        "trolley": ("тележка", metres(GATE["set_f"]["trolley"])),
        "crate": ("ящик 1 м", metres(GATE["set_f"]["box1.0"])),
        "cable": ("висящий кабель 3 см", metres(GATE["set_f"]["cable"])),
        "rail_box": ("ящик 30 см на рельсе", 49), "across_rail": ("предмет поперёк рельса", 46),
    },
    # the 0.5 m box on the bed between the rails: approaches with a detection (GATE; 1 of 6 on 27.09, 2
    # since thin_far 4 -> 3 of 29.09)
    "bed_box_found": GATE["bed_box_found"],
    "anchored_legacy": 150,
    "band_person": 115,               # the person in >= 90 % of the frames of every 10 m band from here
    "speed_person": 167,              # the person with the train speed given (5-frame accumulation)
    "curves": ("6 из 7", "58–86"),    # R ~ 350 m curves: approaches found, first confirmed (the sightline)
    # speed, always with its machine [real data]. End to end through ROS in Docker = the player's
    # publication of the cloud -> the node's result (freshness.source_age_s over the current results,
    # p95, 10 fps; scripts/check_dry_run.py on the raw /resense/status captures), 28.09, detector
    # 464f5bc: 360° doubleT_obstacle 81–82 ms in the two warm dry runs (recording in the page cache) and
    # 88 / 96 ms from the cold network disk on the team VM (Yandex Cloud, 8 vCPU = 4 physical cores;
    # docs/evidence/vm_2026-09-28/summary.md); 120° 49–78 ms on the independent judgement's 4-vCPU
    # sandbox (docs/evidence/judgement_2026-09-28). The rules of 29.09 (measured with all three on; the ego
    # veto is the cost) add +2.4 ms p95 on 360° frames and +1.6 ms on 120° (CHANGELOG, latency_ab.json). The
    # organizers' i7-9700E stand was not available. "hw": the machine of the detector-alone timings below
    "e2e_360": "81–82 мс", "e2e_360_cold": "88–96 мс", "e2e_120": "49–78 мс", "rules_ms": 2,
    "hw": "4 vCPU Xeon 2,1 ГГц",
    # the detector alone on hw, one core, the C++ kernels (resense bench, every frame, 28.09, before the
    # three rules): 360° mean 27.4 / p95 41.6 ms (judge A) and 31.4 / 47.1 ms (P2, --bag); 120° 23.8 /
    # 33.5 and 24.6 / 36.8 ms. (The 18–23 ms, p95 ≤ 33 ms of 27.09 came from a sandbox whose CPU was not
    # recorded and were not reproduced on hw: no longer quoted.)
    "detector_hw": ("24–31 мс", "34–47 мс"),
    "native_cut": (38, 57),           # optional C++ kernels: detector time cut in %, identical output
    "gpu_gain": "30–45 мс",           # the GPU study's upper bound per 360° frame against numpy
    "speed_err": "0,07 м/с",          # the opt-in LiDAR-only train speed, median error (0.06–0.08)
    "tests": TESTS,
}

# ==== 1.2.0 (19.10): the version shown at the defence and developed further; each number with its source.
# The candidate is the sealed development build on main aec88d2 (measured source 0779db7; detector files
# identical; `scripts/detector_freeze.py verify` PASS, 38 files), NOT released; 1.1.0 will not be released
# (the captain's decision, 19.10). Published: v1.0.0 (5d6e9b5), what the experts evaluated 30.09-14.10; 66/100 is
# our independent agent judge's score of v1.0.0 (13.10), not an organizer score. On the Pandar recordings the
# 1.2.0 gate equals GATE above (`build_deck.py --check-gate docs/evidence/b4_merge_reseal_2026-10-18/gate.json` ->
# "GATE matches", 19.10; positive control: the 27.09 baseline differs in 7 keys). Sources: CHANGELOG [1.2.0],
# docs/evidence/b4_merge_reseal_2026-10-18/README.md, docs/evidence/version_1.2.0_2026-10-18/README.md.
# tests: the host suite of the selected default cecab1b (18.10, version_1.2.0 README): 1,906 + 12 subtests
V12 = {"version": "1.2.0", "commit": "aec88d2", "released": "v1.0.0", "judge_score": 66, "tests": "1 906"}
# The second lidar, Seyond Falcon Prime: the organizers' real recording falcon_test_second_dark (16.10), a standing
# train and a person walking along the track toward it. The whole recording through one detector, 1.1.0:
# docs/evidence/falcon_full_2026-10-18 (B2, check_v110.json: 4 443 frames, 444 s; first STOP 124.8 m at 297 s;
# false STOP 1 + 3 frames on the static structure at 115 m and 8 frames on a floor patch at 9.4 m; CAUTION
# 975 + 1 424 + 604 + 59 = 3 062 of 4 443 = 69 %). Re-measured by the captain 19.10 through aec88d2 with
# identical decisions; the captain's 19.10 figures (pitch, height, first warning, detect time, STOP band) are
# not yet in a committed evidence file. The person's first returns at ~249 m: docs/evidence/n2_falcon_2026-10-18
# (raw review, frame 1725). Datasheet: docs/sensor/falcon_prime/README.md. The node crops at 250 m.
FALCON = {
    "frames": 4443, "seconds": 444,
    "pitch": ("−2,39°", "−2,37°"),          # the detector's / an independent bed-plane fit (captain, 19.10)
    "height_m": "1,77",                     # sensor above the rail head (captain, 19.10)
    "warn_m": "139–156", "stop_m": 125,      # first warning, first STOP on the person (B2: 124.8 m)
    "stop_band": (100, 20),                 # STOP on 100 % of the frames from 100 m down to 20 m (captain)
    "false": (12, 4, 115, 8, "9,4"),        # false STOP frames: all; on the 115 m structure; on the 9.4 m floor patch
    "caution_pct": 69, "caution_m": ("105,6", "115"),   # two static structures at the gauge edge
    "detect_ms": 21,                        # detector time per frame, median (captain, 19.10)
    "seen_m": 249, "seen_pts": "5–8",       # the person's first returns
    "bed_m": 150,                           # the bed and rails return nothing beyond ~150 m in this tunnel
    "datasheet_m": (250, 500),              # range at 10 % reflectivity / maximum
    "crop_m": 250,                          # the node's radial range crop
}
# The organizers' three new synthetic recordings (16.10), labelled by the team: docs/evidence/n5_labels_2026-10-17
N5_FRAMES = 1667
# Range by track shape, the judge's method of 13.10 reproduced 16.10 on 1.1.0 (`492e407`):
# docs/evidence/rejudge_2026-10-16/prebuild/summary_1.1.0.json and range_table.md. A world-static box starts 230 m
# ahead on the detector's own axis and rail-head height, ray-cast into real 120° frames with ideal returns
# (favourable); first STOP, m. Backgrounds: A straight (roundT_squareT_pressureGate_squareT), B curve into a
# double-track section (roundT_doubleT), C curves with a pressure gate (roundT_pressureGate_roundT), D braking into a
# platform (squareT_platform_squareT_switch). 1.2.0 = 1.1.0 on the Pandar data (full gate and X3, 40 cases /
# 29 765 rows, identical in every non-timing output: b4_merge_reseal_2026-10-18); the range jobs themselves were
# not re-run on 1.2.0. v1.0.0 (707ea9c / judge 13.10) differs only on C: person 73.9 m, 1 m cube 73.9 m.
RANGE = [  # (chart name, job, first STOP m, shape: straight / platform / curve)
    ("прямая: человек", "A_person", 218.38, "straight"),
    ("прямая: куб 1 м", "A_cube1", 151.1, "straight"),
    ("прямая: куб 0,3 м", "A_cube03", 44.86, "straight"),
    ("платформа: человек", "D_person", 105.82, "platform"),
    ("кривая, гермозатвор: человек", "C_person", 82.77, "curve"),
    ("кривая → двухпутный: человек", "B_person", 51.8, "curve"),
]
RANGE_V100 = {"C_person": 73.9}
# The gauge as a stable 3D box (N1): docs/evidence/n1_n4_2026-10-18/README.md "Final full-precision display replay"
# (core f5ff15f, all 2 308 frames): visible-edge jitter p90 at 40 / 80 / 120 m on set O against the registered
# limits; the cost: on the curve recording roundT_doubleT the drawn box is median 52 m of 141.9 m supported.
GAUGE = {"jitter_set_o": ("0,018", "0,030", "0,040"), "limits": ("0,05", "0,08", "0,15"), "jitter_max": "0,04",
         "curve_drawn_m": (52, 142)}
# The live demo's picture of the box: the unedited RViz window of the final local transport check (core f5ff15f,
# preserved roundT_doubleT curve frames, software rendering), cropped to its 3D view
RVIZ_BOX = ("docs/evidence/n1_n4_2026-10-18/final_core_f5ff15f/curve_rviz_rate_05/curve_rviz.png", (469, 250, 1440, 789))


def rng(job):
    """first STOP of a range job, whole metres"""
    return metres(next(m for _, j, m, _ in RANGE if j == job))


def false_per_hour():
    """'91': false STOP episodes per hour of obstacle-free tunnel, judge 13.10 (36 in 1 430 s, v1.0.0; the 1.2.0
    gate gives the same decisions on these recordings)"""
    return metres(JUDGE["empty_episodes"] * 3600 / JUDGE["empty_s"])


def num(x):
    """13759 -> '13 759', 0.23 -> '0,23' (runs_of glues the thousands with a no-break space)."""
    if isinstance(x, int):
        return f"{x:,}".replace(",", " ")
    return f"{x:g}".replace(".", ",")


def of(pair):
    return f"{pair[0]} из {pair[1]}"


def frames_total():
    return N["frames_six"] + N["frames_ride"]


def per_km(events=None):
    """ride events per km, '1,6' (the shipped detector's by default)"""
    events = N["ride_events"] if events is None else events
    return f"{events / N['ride_km']:.1f}".replace(".", ",")


def plural(n, one, few, many):
    """the Russian noun form after a number: 1 событие, 2 события, 5 событий"""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def events(n):
    return f"{n} {plural(n, 'событие', 'события', 'событий')}"


def of_frames(pair):
    """'61 из 61 кадра', '125 из 126 кадров' (the noun agrees with the last number)"""
    return f"{of(pair)} {plural(pair[1], 'кадра', 'кадров', 'кадров')}"


def novel():
    """'723 из 2 458 кадров (было 544)': the pre-registered placement study"""
    before, now, visible = N["novel_frames"]
    return f"{now} из {num(visible)} кадров (было {before})"


def set_o(key):
    """(name, first STOP m, STOP frames, visible frames, held) of a set O object"""
    return N["set_o"][key]


def set_o_first(key):
    return metres(set_o(key)[1])


def set_o_stopped():
    """'8 из 8': in-envelope objects with a STOP"""
    return of(GATE["set_o_inside"])


def cubes():
    """'43–53': first STOP of the two 0.3 m cubes inside (on the rail, in the air)"""
    lo, hi = sorted(set_o_first(k) for k in ("small_on_rail", "small_center"))
    return f"{lo}–{hi}"


def edge_frames():
    """'2 и 6': STOP frames of the edge cube and the edge box"""
    return f"{set_o('small_edge_inside')[2]} и {set_o('big_edge_inside')[2]}"


def edge_first():
    """'5–10': first STOP of the edge objects, m"""
    lo, hi = sorted(set_o_first(k) for k in ("small_edge_inside", "big_edge_inside"))
    return f"{lo}–{hi}"


def edge_from():
    """'35 и 18': first STOP of the edge cube and the edge box, m"""
    return f"{set_o_first('small_edge_inside')} и {set_o_first('big_edge_inside')}"


def set_f(key):
    return N["set_f"][key][1]


def native_cut():
    return f"{N['native_cut'][0]}–{N['native_cut'][1]} %"


def native_factor():
    """'1,6–2,3': the detector time without the kernels against with them, from native_cut"""
    lo, hi = (1 / (1 - p / 100) for p in N["native_cut"])
    return f"{lo:.1f}–{hi:.1f}".replace(".", ",")


def opinion_delay():
    """'10 обработанных кадров за жизнь трека (~1 с при 10 Гц, ~2 с при 5 Гц, до ~3 с, пока узел догоняет
    очередь)': the budget counts processed frames, so its time depends on the processed rate"""
    k = N["opinion_budget"]
    return (f"{k} обработанных кадров за жизнь трека (~{num(k / 10)} с при 10 Гц, ~{num(k / 5)} с при 5 Гц, "
            f"до ~{N['opinion_catchup_s']} с, пока узел догоняет очередь)")


def opinion_bounds(short=False):
    """'не больше 10 обработанных кадров за жизнь трека (...), не ближе 25 м и не для стоящего тела ≥ 1 м
    ближе 40 м'; ``short`` (a slide row): 'до 10 обработанных кадров ... дольше при догоняющей обработке),
    не ближе 25 м' (the body exemption stays in the notes)"""
    body_m, body_near = N["opinion_body"]
    k = N["opinion_budget"]
    if short:
        return (f"до {k} обработанных кадров за жизнь трека (~{num(k / 10)} с при 10 Гц, ~{num(k / 5)} с при 5 Гц, "
                f"дольше при догоняющей обработке), не ближе {N['opinion_near_m']} м")
    return (f"не больше {opinion_delay()}, не ближе {N['opinion_near_m']} м и не для стоящего тела "
            f"≥ {num(body_m)} м ближе {body_near} м")


def obstacle_no_gap():
    """True when the STOP runs from the first STOP frame to the last frame (193 of 201 from frame 8)"""
    stop, frames = N["obstacle_stop"]
    return stop == frames - N["obstacle_first_frame"]


def obstacle_run():
    """'STOP на 193 из 201 кадра — с кадра 8 до конца, без пропусков': doubleT_obstacle as a whole
    (the gap clause only when the numbers say so)"""
    head = (f"STOP на {of(N['obstacle_stop'])} {plural(N['obstacle_stop'][1], 'кадра', 'кадров', 'кадров')} — "
            f"с кадра {N['obstacle_first_frame']}")
    return head + (" до конца, без пропусков" if obstacle_no_gap() else ", с пропусками")


def gap_phrase():
    """'STOP без пропусков' or 'STOP с пропусками' (the person and the object on the rail)"""
    return "STOP без пропусков" if obstacle_no_gap() else "STOP с пропусками"


def e2e():
    """'p95 от публикации кадра до решения через ROS в Docker: 81–82 мс при 360° (4 ядра) и 49–78 мс при 120°
    (4 vCPU), 28.09; правила 29.09 — ещё ~2 мс'"""
    return (f"p95 от публикации кадра до решения через ROS в Docker: {N['e2e_360']} при 360° (ВМ, 4 ядра; "
            f"с холодного диска {N['e2e_360_cold']}) и {N['e2e_120']} при 120° (4 vCPU), замер 28.09; "
            f"правила 29.09 добавляют ~{N['rules_ms']} мс")


def rules_story(short=False):
    """the team's approach to other teams' ideas: tried through the full gate, rejected, shipped, one removed"""
    tried, rejected = N["rules_tried"], N["rules_rejected"]
    on, off = N["shell_cable_m"]
    if short:
        return (f"{tried} идей из открытых решений других команд прогнали через полный гейт: {rejected} отклонили, "
                f"{tried - rejected} включили, одно потом выключили после своей проверки безопасности")
    return (f"{tried} идей из открытых решений других команд кейса 05 прогнали через полный гейт на всех "
            f"записях: {rejected} отклонили, {tried - rejected} включили 29.09. Своя проверка безопасности "
            f"в тот же вечер выключила третье («обделка»): висящий от свода кабель получал STOP с {on} м "
            f"вместо {off} м")


def unseen_km():
    """'2,8': ride events per km measured with an opinion model that never saw the piece (27.09 detector)"""
    return per_km(N["ride_cv"][1])


def person_rails():
    """'строго от рельсов — 58': the person with the envelope from the rails alone"""
    return f"строго от рельсов — {N['person_rails_only']}"


def person_alarm():
    """when the alarm comes for the real person, as a phrase after 'тревога'"""
    if N["person_delay_s"] <= 0:
        return "с первого кадра в габарите"
    return f"через {num(N['person_delay_s'])} с"

# ---- the team (slides 7-10): the team is «Молоток», ReSense is the solution. Names and photos (and
# nicknames, place of study, city when given) come only from --team; team.json and the photos stay out
# of git, the named deck is the committed one since 29.09 (the team's approval). Without --team the team
# slides show the four roles P1-P4 as README "Team" states them, with no unfilled field. The pitch is
# the captain's since 29.09 evening (P2 made the deck design, the photos and the first video, and
# declined the pitch) -----------------------------------------------------------------------------
TEAM_NAME = "Молоток"
TEAM = {
    "captain": None, "captain_specialty": None, "members": "4 человека",
    "formed": None, "study": None, "study_short": None, "city": None, "team_photo": None,
    "cards": [{"name": None, "nick": None, "photo": None} for _ in range(4)],
}
# the public cards (README "Team"): (name line, role, what the member owns)
PUBLIC_CARDS = [
    ("P1 · капитан", "Системный аналитик, ROS 2", "требования, архитектура, узел ROS 2 и Docker, питч, сдача"),
    ("P2 · фронтенд", "Разработчик ПО (Python / JS)", "RViz, Foxglove, веб-дашборд, разметка, слайды, ролик"),
    ("P3 · зрение", "Инженер компьютерного зрения", "модель пути, габарит, кластеры, трекинг, дальность, скорость"),
    ("P4 · данные", "Специалист по данным", "датасет, синтетические препятствия, разметка, метрики, тесты, CI"),
]
# the named build: optional keys of team.json, shown only when given
OPTIONAL_TEAM = ("formed", "study", "study_short", "city", "team_photo")


def private():
    """True when the team's personal data were given with --team"""
    return bool(TEAM.get("_dir"))

PINK, DEEP, VIOLET, LIGHT = "FF0053", "520978", "8A83D1", "FFD6E4"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def qa(tag):
    return "{%s}%s" % (A, tag)


def qc(tag):
    return "{http://schemas.openxmlformats.org/drawingml/2006/chart}%s" % tag


# ------------------------------------------------------------------------------------ helpers
def _walk(shapes):
    for sh in shapes:
        yield sh
        if sh.shape_type == 6:                  # group: the template's browser frames carry text boxes
            yield from _walk(sh.shapes)


def shape(slide, sid):
    for sh in _walk(slide.shapes):
        if sh.shape_id == sid:
            return sh
    raise KeyError(f"shape id {sid} not on slide")


def placeholder(slide, idx):
    for ph in slide.placeholders:
        if ph.placeholder_format.idx == idx:
            return ph
    raise KeyError(f"placeholder idx {idx} not on slide")


def remove(sh):
    el = sh._element
    el.getparent().remove(el)


def runs_of(text):
    """'plain **bold** plain' -> [(text, bold)]; thousands and units are glued with no-break spaces"""
    text = re.sub(r"(\d) (\d{3})\b", "\\1\u00a0\\2", text)
    text = re.sub(r"(\d) (м|мс|км|с|%|кадр)", "\\1\u00a0\\2", text)
    out = []
    for k, part in enumerate(re.split(r"\*\*", text)):
        if part:
            out.append((part, k % 2 == 1))
    return out


def fill(sh, paras, size=None, color=None, bullet=None, space_before=None, line=None, bold_all=False,
         italic=False, align=None):
    """Replace the text of a shape, keeping the first paragraph's properties and the first
    run's character properties (so a template text box keeps its font, colour and bullets).

    paras: list of str (``**bold**`` markup) or (str, dict) with per-paragraph overrides
    (size, color, bullet, space_before, bold)."""
    tf = sh.text_frame
    body = tf._txBody
    ps = body.findall(qa("p"))
    ppr0 = rpr0 = None
    for p in ps:
        if ppr0 is None and p.find(qa("pPr")) is not None:
            ppr0 = p.find(qa("pPr"))
        r = p.find(qa("r"))
        if rpr0 is None and r is not None and r.find(qa("rPr")) is not None:
            rpr0 = r.find(qa("rPr"))
    if rpr0 is None:
        for p in ps:
            e = p.find(qa("endParaRPr"))
            if e is not None:
                rpr0 = e
                break
    ppr0 = copy.deepcopy(ppr0) if ppr0 is not None else None
    base = etree.Element(qa("rPr"))
    if rpr0 is not None:
        for k, v in rpr0.attrib.items():
            base.set(k, v)
        for ch in rpr0:
            base.append(copy.deepcopy(ch))
    base.set("lang", "ru-RU")
    for k in ("b", "i", "dirty"):
        base.attrib.pop(k, None)
    for p in ps:
        body.remove(p)
    for item in paras:
        text, o = (item, {}) if isinstance(item, str) else item
        p = etree.SubElement(body, qa("p"))
        ppr = copy.deepcopy(ppr0) if ppr0 is not None else etree.Element(qa("pPr"))
        b = o.get("bullet", bullet)
        if b is False:
            for tag in ("buFont", "buChar", "buAutoNum", "buNone", "buClr"):
                for e in ppr.findall(qa(tag)):
                    ppr.remove(e)
            ppr.set("marL", "0")
            ppr.set("indent", "0")
            etree.SubElement(ppr, qa("buNone"))
        al = o.get("align", align)
        if al:
            ppr.set("algn", al)
        sb = o.get("space_before", space_before)
        ln = o.get("line", line)
        if sb is not None or ln is not None:
            for tag in ("lnSpc", "spcBef"):
                for e in ppr.findall(qa(tag)):
                    ppr.remove(e)
            pos = 0
            if ln is not None:
                lel = etree.Element(qa("lnSpc"))
                etree.SubElement(lel, qa("spcPct")).set("val", str(int(ln * 1000)))
                ppr.insert(pos, lel)
                pos += 1
            if sb is not None:
                sel = etree.Element(qa("spcBef"))
                etree.SubElement(sel, qa("spcPts")).set("val", str(int(sb * 100)))
                ppr.insert(pos, sel)
        # schema order inside pPr: lnSpc, spcBef, spcAft, bu*... keep it by re-sorting the known tags
        order = ["lnSpc", "spcBef", "spcAft", "buClrTx", "buClr", "buSzTx", "buSzPct", "buSzPts", "buFontTx",
                 "buFont", "buNone", "buAutoNum", "buChar", "buBlip", "tabLst", "defRPr", "extLst"]
        kids = sorted(list(ppr), key=lambda e: order.index(etree.QName(e).localname)
                      if etree.QName(e).localname in order else 99)
        for e in list(ppr):
            ppr.remove(e)
        for e in kids:
            ppr.append(e)
        p.append(ppr)
        for t, bold in runs_of(text):
            r = etree.SubElement(p, qa("r"))
            rpr = copy.deepcopy(base)
            if bold or o.get("bold", bold_all):
                rpr.set("b", "1")
            elif italic or o.get("italic"):
                rpr.set("i", "1")
            sz = o.get("size", size)
            if sz:
                rpr.set("sz", str(int(sz * 100)))
            col = o.get("color", color)
            if col:
                for e in rpr.findall(qa("solidFill")):
                    rpr.remove(e)
                sf = etree.Element(qa("solidFill"))
                # "FF0053": an RGB colour; "tx1" and other non-hex names: a theme colour (as the template's runs)
                rgb = bool(re.fullmatch(r"[0-9A-Fa-f]{6}", col))
                etree.SubElement(sf, qa("srgbClr" if rgb else "schemeClr")).set("val", col)
                # solidFill goes after ln and before latin/ea/cs in CT_TextCharacterProperties
                ln_el = rpr.find(qa("ln"))
                rpr.insert(list(rpr).index(ln_el) + 1 if ln_el is not None else 0, sf)
            r.append(rpr)
            te = etree.SubElement(r, qa("t"))
            te.text = t
            if t != t.strip():
                te.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")


def _jpeg(path, quality=92):
    """A large PNG render goes into the deck as JPEG (a point-cloud render: 1.6 MB -> ~0.5 MB)."""
    import io
    from PIL import Image
    if not isinstance(path, str) or not path.lower().endswith(".png") or os.path.getsize(path) < 400_000:
        return path                             # a file object (already prepared) or a small picture
    buf = io.BytesIO()
    Image.open(path).convert("RGB").save(buf, "JPEG", quality=quality)
    buf.seek(0)
    return buf


def picture_cover(slide, path, left, top, width, height):
    """Add a picture that fills the box (cropped, aspect kept)."""
    from PIL import Image
    pic = slide.shapes.add_picture(_jpeg(path), left, top, width, height)
    iw, ih = Image.open(path).size
    box, img = width / height, iw / ih
    if img > box:
        c = (1 - box / img) / 2
        pic.crop_left = pic.crop_right = c
    else:
        c = (1 - img / box) / 2
        pic.crop_top = pic.crop_bottom = c
    return pic


def picture_in_placeholder(ph, path):
    return ph.insert_picture(_jpeg(path))


def placeholder_picture(slide, idx, image):
    """The picture of placeholder ``idx``, filled and cropped to the placeholder's box as insert_picture does;
    with --refresh the placeholder already holds a picture: swap its image (the old one is dropped)."""
    if not REFRESH:
        return picture_in_placeholder(placeholder(slide, idx), image)
    pic = placeholder(slide, idx)
    blip = pic._element.blipFill.blip
    old = blip.rEmbed
    image_part, rid = slide.part.get_or_add_image_part(image)
    blip.rEmbed = rid
    if rid != old:
        slide.part.drop_rel(old)
    blip_fill = pic._element.blipFill
    for rect in blip_fill.findall(qa("srcRect")):    # crop_to_fit adds one more: the old crop goes first
        blip_fill.remove(rect)
    pic._element.crop_to_fit(image_part._px_size, (pic.width, pic.height))
    return pic


def rviz_box_view():
    """RVIZ_BOX: the RViz screenshot cut to its 3D view, as a JPEG in memory"""
    import io
    from PIL import Image
    path, box = RVIZ_BOX
    buf = io.BytesIO()
    Image.open(os.path.join(ROOT, path)).convert("RGB").crop(box).save(buf, "JPEG", quality=92)
    buf.seek(0)
    return buf


def photo_into_frame(slide, sid, path):
    """Replace a template photo frame (a picture placeholder) with the photo cropped to the frame's
    box; the picture takes the frame's place in the drawing order, so the text above stays above."""
    frame = shape(slide, sid)
    el = frame._element
    pic = picture_cover(slide, path, frame.left, frame.top, frame.width, frame.height)
    el.addprevious(pic._element)
    el.getparent().remove(el)
    return pic


def team_photo(name):
    """Absolute path of a photo named in the --team JSON, or None."""
    return os.path.join(TEAM["_dir"], name) if name and TEAM.get("_dir") else None


def validate_private_team(data, directory):
    """Fail before building if the private team slides would contain gaps."""
    from PIL import Image

    def bad(value):
        return not isinstance(value, str) or not value.strip() or "<" in value or ">" in value

    missing = []
    for key in ("captain", "captain_specialty"):
        if bad(data.get(key)):
            missing.append(key)
    for key in OPTIONAL_TEAM:                  # optional, but never a placeholder
        if data.get(key) is not None and bad(data.get(key)):
            missing.append(f"{key} (empty or a placeholder: leave it out instead)")
    if data.get("team_photo") and not bad(data["team_photo"]):
        try:
            with Image.open(os.path.join(directory, data["team_photo"])) as image:
                image.verify()
        except (OSError, ValueError):
            missing.append("team_photo (image unavailable)")
    cards = data.get("cards")
    if not isinstance(cards, list) or len(cards) != 4:
        missing.append("cards (exactly four members)")
    else:
        for index, card in enumerate(cards, 1):
            if not isinstance(card, dict):
                missing.append(f"cards[{index}]")
                continue
            for key in ("name", "photo"):
                if bad(card.get(key)):
                    missing.append(f"cards[{index}].{key}")
            if card.get("nick") is not None and bad(card.get("nick")):
                missing.append(f"cards[{index}].nick (empty or a placeholder: leave it out instead)")
            photo = card.get("photo")
            if isinstance(photo, str) and photo.strip() and "<" not in photo and ">" not in photo:
                path = os.path.join(directory, photo)
                try:
                    with Image.open(path) as image:
                        image.verify()
                except (OSError, ValueError):
                    missing.append(f"cards[{index}].photo (image unavailable)")
    if missing:
        raise SystemExit("private deck needs: " + ", ".join(missing))


# --refresh: re-fill an already built deck (the committed named one) in place. The slide functions below run
# unchanged, but skip the one-time steps of a build from the template (pictures cut into placeholders, the data
# slide's background, removed placeholders, resized charts) and find the text boxes a build added by their
# position, so the texts, charts and notes are the ones a new build writes, and the names and photos stay.
REFRESH = False


def textbox(slide, left, top, width, height, paras, size=12, color="FFFFFF", bold=False, anchor=None):
    if REFRESH:                                 # the box an earlier build added at this place
        tb = next((sh for sh in slide.shapes if sh.shape_type == 17 and sh.left == left and sh.top == top), None)
        if tb is None:
            raise KeyError(f"no text box at ({left}, {top}) to refresh")
        fill(tb, paras, size=size, color=color, bold_all=bold)
        return tb
    tb = slide.shapes.add_textbox(left, top, width, height)
    tf = tb.text_frame
    tf.word_wrap = True
    if anchor:
        tf._txBody.find(qa("bodyPr")).set("anchor", anchor)
    fill(tb, paras, size=size, color=color, bold_all=bold)
    return tb


def title_chip(slide, chip_id, title_sh, text, per_char=205000, pad=520000):
    fill(title_sh, [text])
    chip = shape(slide, chip_id)
    chip.width = Emu(max(chip.width, pad + per_char * len(text)))


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def all_category_labels(chart):
    """Draw every category name: with the template's fixed plot box LibreOffice (and the PDF made with
    it) skips every other one of seven long names. Let the plot area size itself around the names and
    ask for every label (``c:tickLblSkip`` 1, in its schema place inside ``c:catAx``)."""
    for ml in chart._chartSpace.findall(".//%s/%s/%s" % (qc("plotArea"), qc("layout"), qc("manualLayout"))):
        ml.getparent().remove(ml)
    ax = chart._chartSpace.find(".//" + qc("catAx"))
    for e in ax.findall(qc("tickLblSkip")):
        ax.remove(e)
    skip = etree.Element(qc("tickLblSkip"))
    skip.set("val", "1")
    after = [qc(t) for t in ("tickMarkSkip", "noMultiLvlLbl", "extLst")]
    nxt = next((e for e in ax if e.tag in after), None)
    if nxt is None:
        ax.append(skip)
    else:
        nxt.addprevious(skip)


def bar_labels(plot, texts, size=12, color=None):
    """Value labels at the bar ends ("148 м"); a text in ``texts`` (one per point, None = the value)
    replaces that bar's label. python-pptx creates ``c:dLbls`` with ``showVal 0``, and a series-level
    ``c:dLbls`` (made by any per-point label) overrides the plot's: switch the value on at both levels."""
    from pptx.enum.chart import XL_LABEL_POSITION
    plot.has_data_labels = True
    ser = plot.series[0]
    for dl in (plot.data_labels, ser.data_labels):
        dl.number_format = '0" м"'
        dl.number_format_is_linked = False
        dl.show_value = True
        dl.position = XL_LABEL_POSITION.OUTSIDE_END
        dl.font.size = Pt(size)
        dl.font.bold = True
        if color:
            dl.font.color.rgb = RGBColor.from_string(color)
    for pt, text in zip(ser.points, texts):
        if not text:
            continue
        lab = pt.data_label
        lab.position = XL_LABEL_POSITION.OUTSIDE_END
        tf = lab.text_frame
        tf.text = text
        for r in tf.paragraphs[0].runs:
            r.font.size = Pt(size)
            r.font.bold = True
            if color:
                r.font.color.rgb = RGBColor.from_string(color)


# ------------------------------------------------------------------------------------ slides
def s07_title(sl, logo_path):
    fill(placeholder(sl, 0), [TEAM_NAME])
    body = placeholder(sl, 12)
    fill(body, ["Кейс 05 · решение ReSense", "Обнаружение посторонних объектов в тоннеле метро по данным 3D-лидара"],
         size=15)
    for ppr in body.text_frame._txBody.iter(qa("pPr")):     # the template's first-line indent, for every line
        ppr.set("marL", ppr.get("indent", "268288"))
        ppr.set("indent", "0")
    ph = placeholder(sl, 11)
    left, top, height = ph.left, ph.top, ph.height
    pic = picture_in_placeholder(ph, logo_path)
    pic.crop_left = pic.crop_right = pic.crop_top = pic.crop_bottom = 0
    from PIL import Image
    iw, ih = Image.open(logo_path).size
    h = int(height * 0.62)
    pic.left, pic.top = Emu(left), Emu(top + (height - h) // 2)
    pic.height = Emu(h)
    pic.width = Emu(int(h * iw / ih))


def s08_team(sl):
    fill(shape(sl, 18), [f"КОМАНДА «{TEAM_NAME}»"])
    zones = ("P1 — узел ROS 2, Docker и питч; P2 — интерфейс", "P3 — алгоритм, P4 — данные, метрики и тесты")
    if private():   # the named build: what team.json gives, the zones P1-P4 for the rest
        lines = [
            f"**Капитан:** {TEAM['captain']}, {TEAM['captain_specialty']}",
            f"**Кол-во участников:** {TEAM['members']}",
            "**Краткое описание:**",
            (TEAM.get("formed") or zones[0], {"italic": False}),
            (f"место учёбы: {TEAM['study']}" if TEAM.get("study") else zones[1], {}),
        ]
        if TEAM.get("city"):
            lines.append(f"**Город и регион:** {TEAM['city']}")
    else:   # the public deck: roles, no personal data (README "Team")
        lines = [
            "**Капитан:** P1 — системный аналитик, ROS 2",
            f"**Кол-во участников:** {TEAM['members']}",
            "**Краткое описание:**",
            (zones[0], {"italic": False}),
            (zones[1], {}),
            "**Имена и контакты** — в очной версии",
        ]
    fill(shape(sl, 14), lines)
    # the template's bullets for the two sub-items ("-") come from paragraphs 4-5
    body = shape(sl, 14).text_frame._txBody
    ps = body.findall(qa("p"))
    for p in ps[3:5]:
        ppr = p.find(qa("pPr"))
        for e in ppr.findall(qa("buNone")):
            ppr.remove(e)
        ppr.set("marL", "289376")
        ppr.set("indent", "-144688")
        etree.SubElement(ppr, qa("buFont")).set("typeface", "Arial")
        etree.SubElement(ppr, qa("buChar")).set("char", "–")
    d = shape(sl, 5)
    d.height = Emu(1780000)
    fill(d, ["LiDAR → модель тоннеля → препятствие в габарите 2,1 × 3,0 м → решение и расстояние. "
             "ROS 2, Docker, CPU."], size=15)
    u = shape(sl, 8)
    u.height = Emu(1350000)
    fill(u, ["Модель среды без карты и классов объектов. Возможны пропуски и ложные тревоги."], size=15)
    if team_photo(TEAM.get("team_photo")):
        photo_into_frame(sl, 2, team_photo(TEAM["team_photo"]))


def s09_cards(sl):
    fill(shape(sl, 7), [f"КОМАНДА «{TEAM_NAME}»"])
    cards = [  # (card, photo, name, details) shape ids, left to right
        (17, 2, 15, 9), (56, 3, 58, 57), (59, 4, 61, 60), (62, 5, 64, 63), (65, 6, 67, 66)]
    for (card, photo, name, det), who, pub in zip(cards, TEAM["cards"], PUBLIC_CARDS):
        # the role and what the member owns (README "Team"); the named build adds the nick and the
        # place of study when team.json gives them, and the name under the photo (below)
        fill(shape(sl, name), [pub[0]])
        extra = [x for x in (who.get("nick"), TEAM.get("study_short")) if private() and x]
        fill(shape(sl, det), [pub[1], pub[2]] + extra, size=11)
    for sid in cards[4]:                       # a team of four: the fifth card goes
        remove(shape(sl, sid))
    step = shape(sl, 56).left - shape(sl, 17).left
    span = 3 * step + shape(sl, 17).width
    dx = (12192000 - span) // 2 - shape(sl, 17).left
    for group in cards[:4]:
        for sid in group:
            s = shape(sl, sid)
            s.left = Emu(s.left + dx)
    for (card, photo, name, det), who in zip(cards, TEAM["cards"]):
        if not private():
            continue
        frame = shape(sl, photo)
        label = shape(sl, name)
        # the name under the photo, surname over first name, above the P1-P4 line (as P2 laid it out);
        # the P1-P4 line and the details move down to make room (the cards have it below the details)
        for sid in (name, det):
            shape(sl, sid).top = Emu(shape(sl, sid).top + 320000)
        top = frame.top + frame.height + 50000
        tb = textbox(sl, Emu(label.left), Emu(top), Emu(frame.width + frame.left - label.left),
                     Emu(max(label.top - top - 10000, 300000)), who["name"].split(" ", 1),
                     size=14, color="4B0E73", bold=True)
        tf = tb.text_frame
        tf.margin_right = tf.margin_top = tf.margin_bottom = 0      # left: the label's own inset
        for p in tf.paragraphs:
            p.line_spacing = 0.9
        if team_photo(who.get("photo")):
            photo_into_frame(sl, photo, team_photo(who["photo"]))


def s10_history(sl):
    fill(shape(sl, 7), ["ИСТОРИЯ КОМАНДЫ"])
    fill(shape(sl, 37), ["Четыре роли: ROS 2 и интеграция, визуализация, компьютерное зрение, данные и тесты."], size=15)
    fill(shape(sl, 43), ["Реальных препятствий мало. Ищем отклонения от геометрии тоннеля; "
                         "синтетические объекты проверяем на реальных фонах."], size=15)
    fill(shape(sl, 40), [f"Идеи других команд: {N['rules_tried']} проверили, {N['rules_rejected']} отклонили, "
                         "3 включили. Одно правило выключили после своей проверки: оно скрывало кабель. "
                         "Изменения — через шлюз."], size=15)


def s11_short(sl):
    fill(shape(sl, 3), [
        "ROS 2 Humble · Python + C++ · Docker · только CPU",
        "PointCloud2 → модель пути → габарит 2,1 × 3,0 м → кластеры",
        "GO / CAUTION / STOP / FAULT, расстояние, /resense/status",
        "Лидары: Pandar128 и Falcon Prime",
        f"Показываем {V12['version']} (не выпущен); эксперты оценивали {V12['released']}",
    ], size=15, space_before=6)
    fill(shape(sl, 7), [
        "**Применение:** контроль габарита поезда",
        "**В работе:** габарит на поворотах, пыль, 300 м, меньше ложных STOP",
        "**Внедрение:** адаптер торможения — отдельный этап",
    ], size=15, space_before=6)


def s_problem(sl):          # template slide 24: problem / alternatives / solution
    title_chip(sl, 2, shape(sl, 9), "ПРОБЛЕМА И ПОДХОД")
    cols = {
        26: ("Проблема", "Беспилотному поезду нужно видеть препятствия заранее. "
                         "Реальных размеченных объектов почти нет."),
        31: ("Альтернативы", "3D-детектору нужны примеры препятствий; карте — локализация "
                             "и повторный проезд."),
        32: ("Наше решение", "Описать нормальный тоннель по рельсам и стенам. "
                             "Искать постороннее внутри габарита без карты. Проверять дальность по геометриям пути."),
    }
    for idx, (head, text) in cols.items():
        # the body's theme colour is written out (the template's own), so --refresh does not carry the
        # heading's pink into it
        fill(placeholder(sl, idx), [(head, {"bold": True, "size": 16, "color": PINK}),
                                    (text, {"space_before": 8})], size=13, bullet=False, color="tx1")


def s_data(sl):             # template slide 12: text left, picture right
    fill(placeholder(sl, 0), ["ДАННЫЕ И СЕНСОР"])
    fill(placeholder(sl, 1), [
        f"**{num(frames_total())} реальных кадров Pandar128:** 6 записей и 20-минутная поездка",
        "**~210 м:** дальше отражений Pandar в этих записях нет",
        f"**Falcon Prime, 16.10:** {num(FALCON['frames'])} реальных "
        f"{plural(FALCON['frames'], 'кадр', 'кадра', 'кадров')} — человек идёт к стоящему поезду",
        f"**Синтетика 16.10:** 3 записи, {num(N5_FRAMES)} кадров, разметка наша",
        "Реальные препятствия: человек и предмет на рельсе (Pandar), человек (Falcon)",
        "Все записи — данные разработки, не скрытая проверка",
    ], size=15, space_before=8)
    if REFRESH:                                 # the background below is cut once, by the build
        return
    # the template draws this slide's right half from its background picture (the partners' logos
    # are part of it): put the LiDAR view into the right half and keep the logos on top of it
    import io
    from PIL import Image
    R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
    blip = sl._element.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}bg").find(".//" + qa("blip"))
    tmpl = Image.open(io.BytesIO(sl.part.related_part(blip.get(R)).blob)).convert("RGB")
    W, H = tmpl.size
    view = Image.open(os.path.join(ROOT, IMG["ride_clean"])).convert("RGB")
    view = view.resize((int(view.width * H / view.height), H))
    x0 = int(W * 6456363 / 12192000)
    w = W - x0
    c = (view.width - w) // 2 + int(0.02 * view.width)
    out = tmpl.copy()
    out.paste(view.crop((c, 0, c + w, H)), (x0, 0))
    band = (int(0.55 * W), 0, W, int(0.13 * H))                # the logo row, white on the template's purple
    logos = tmpl.crop(band)
    mask = logos.convert("L").point(lambda v: 255 if v > 170 else 0)
    out.paste(logos, band[:2], mask)
    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=88)
    buf.seek(0)
    _, rid = sl.part.get_or_add_image_part(buf)
    old = blip.get(R)
    blip.set(R, rid)
    sl.part.drop_rel(old)                      # the template's picture is not written again


def s_algorithm(sl):        # template slide 25: timeline 1-5
    title_chip(sl, 12, shape(sl, 15), "АЛГОРИТМ")
    steps = {  # (title idx, text idx): step number 1..5 by the timeline boxes
        (26, 27): ("Автокалибровка", "ориентация и наклон по рельсам и полотну"),
        (32, 33): ("Модель пути", "полотно, рельсы, ось; кривизна по стенам"),
        (28, 29): ("Габарит", "коридор 2,1 × 3,0 м вдоль оси; 3D-бокс в RViz"),
        (34, 35): ("Кластеры", "адаптивный радиус; проверка инфраструктуры"),
        (30, 31): ("Решение", "подтверждение 0,5 с → GO / CAUTION / STOP / FAULT"),
    }
    for (ti, di), (t, d) in steps.items():
        fill(placeholder(sl, ti), [t], size=15, bullet=False)
        fill(placeholder(sl, di), [d], size=11, bullet=False)


def s_hero(sl):             # template slide 13: big white card
    fill(placeholder(sl, 0), ["ГЛАВНЫЙ КАДР"])
    card = shape(sl, 4)
    m = 170000
    h = card.height - 2 * m
    w = int(h * 16 / 9)
    if not REFRESH:
        remove(placeholder(sl, 1))
        picture_cover(sl, os.path.join(ROOT, IMG["hero_person"]), Emu(card.left + m), Emu(card.top + m), Emu(w), Emu(h))
    x = card.left + m + w + 200000
    tail = " до конца без пропусков" if obstacle_no_gap() else ""
    textbox(sl, Emu(x), Emu(card.top + m), Emu(card.left + card.width - x - m), Emu(h), [
        ("Реальная запись организаторов", {"bold": True, "size": 14, "color": DEEP}),
        (f"Увидел за {N['person_m']} м", {"bold": True, "size": 26, "color": PINK, "space_before": 6}),
        ("человек переходит путь — STOP", {"size": 13}),
        (f"Найден в **{of(N['person'])}** кадра внутри габарита", {"space_before": 8}),
        (f"Тревога {person_alarm()} после входа в габарит" if N["person_delay_s"] > 0
         else f"Тревога {person_alarm()}", {"space_before": 6}),
        (f"Ошибка дальности ≤ {num(N['person_err_m'])} м", {"space_before": 6}),
        (f"Вся запись: STOP на **{of(N['obstacle_stop'])}** кадра — с кадра {N['obstacle_first_frame']}{tail}; "
         f"предмет на рельсе — {of(N['rail_object'])}", {"space_before": 6}),
    ], size=12, color="1C1D22", anchor="ctr")
    big = set_o("big_center")
    notes(sl, "Вот тоннель — двухпутный, поезд стоит, лидар на кабине. Вот облако одного кадра — сотни тысяч "
              "точек за 0,1 с. Зелёным — габарит поезда, который алгоритм сам протянул вдоль оси пути по рельсам "
              "и стенам. Жёлтым — всё, что попало в коридор. А вот препятствие, которое наш алгоритм увидел за "
              f"{N['person_m']} метров: человек переходит путь, красная рамка, решение STOP — {person_alarm()}. "
              "Справа — его точки крупно. Когда человек уходит, на рельсе остаётся предмет 45 × 60 × 30 см — "
              f"алгоритм держит и его: {obstacle_run()}; предмет на рельсе — {of(N['rail_object'])} кадров. "
              "До 29.09 в кадре 111 был один GO: верх предмета на 4–7 мм ниже порога высоты. Исправили правилом "
              "удержания уже подтверждённого низкого STOP на 0,3 с — подобрано на этой же записи, и мы это говорим. "
              "Здесь поезд стоит; на едущем поезде — синтетика организаторов: ящик 2 × 2 м алгоритм увидел за "
              f"{metres(big[1])} метров, с первого появления (слайд «Объекты организаторов»). "
              f"Версия {V12['version']} даёт на этой записи те же числа: её полный гейт совпадает с гейтом 29.09 "
              "(build_deck.py --check-gate docs/evidence/b4_merge_reseal_2026-10-18/gate.json → GATE matches, 19.10). "
              "Источник чисел: docs/evidence/results/regression_baseline_2026-09-29_shell_off.json; независимая "
              "оценка 13.10 воспроизвела 193 из 201 и 61 из 61 (docs/evidence/judgement_2026-10-13/README.md §3).")


def s_demo(sl):             # template slide 27: two browser frames
    title_chip(sl, 2, shape(sl, 55), "ДЕМОНСТРАЦИЯ")
    # left: the 1.2.0 gauge box in RViz (until 19.10: the dashboard, IMG["dashboard"]); right: the fallback clip
    placeholder_picture(sl, 14, rviz_box_view())
    if not REFRESH:
        picture_in_placeholder(placeholder(sl, 18), os.path.join(ROOT, IMG["chain"]))
    fill(shape(sl, 10), [f"rviz2 · {V12['version']}"])
    fill(shape(sl, 33), ["docker run resense"])
    fill(placeholder(sl, 15), ["RViz в контейнере: габарит — 3D-бокс по поддержанной геометрии; "
                               "на кривой короче."], size=14)
    fill(placeholder(sl, 16), ["Запасной ролик: Docker + RViz, STOP около 56 м. "
                               f"Архив 23.09, 69 с; не {V12['version']}."], size=14)
    textbox(sl, Emu(1210643), Emu(5640000), Emu(9770000), Emu(640000),
            [("run_demo.sh: Pandar → Falcon в одном узле · пауза · замедление", {"align": "ctr"}),
             ("вручную: docker load → docker run → ros2 bag play → /resense/decision",
              {"align": "ctr", "size": 12, "bold": False, "space_before": 4})], size=16,
            color=DEEP, bold=True, anchor="ctr")


def s_results(sl):          # template slide 20: left card + five rows
    title_chip(sl, 2, shape(sl, 14), "РЕЗУЛЬТАТЫ")
    # 19.10: by the experts' criteria of 16.10 (range, gauge, false negatives / positives, 10 Hz, launch)
    fill(placeholder(sl, 14), [
        (of(N["person"]), {"size": 36, "bold": True, "color": PINK}),
        ("кадр с человеком — STOP · Pandar, реальная запись", {"size": 13}),
        (f"~{FALCON['stop_m']} м", {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        ("первый STOP: человек идёт к поезду · Falcon", {"size": 13}),
        (f"≤ {GAUGE['jitter_max']} м", {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        ("дрожание края габарита, p90 до 120 м", {"size": 13}),
    ], bullet=False, color="1C1D22")
    rows = [
        f"**Дальность:** прямая {rng('A_person')} м, кривые {rng('B_person')}–{rng('C_person')} м",
        f"**Пропуски:** STOP у {set_o_stopped()} объектов организаторов",
        f"**Ложные:** {N['ride_events']} событий за {N['ride_km']} км в выборке; "
        f"≈{num(round(JUDGE['ride_episodes'] / JUDGE['ride_km'], 1))} эпизода/км ({JUDGE['date']})",
        f"**10 Гц:** Falcon — {FALCON['detect_ms']} мс/кадр; Pandar 360° — p95 {JUDGE['node_360_p95_ms']} мс",
        "**Запуск:** пауза, замедление, смена бэгов без перезапуска",
    ]
    for idx, text in zip(range(15, 20), rows):
        fill(placeholder(sl, idx), [text], size=12, bullet=False)


def s_range(sl):            # template slide 22: horizontal bar chart + four notes
    # 19.10: range by track shape (RANGE, the judge's method), not one headline; until 19.10 this chart showed
    # set F, our synthetic objects in the straight ride (N["set_f"], still in the notes of 22 below)
    title_chip(sl, 2, shape(sl, 15), "ДАЛЬНОСТЬ ПО ФОРМЕ ПУТИ")
    gf = shape(sl, 12)
    cd = CategoryChartData()
    data = list(reversed(RANGE))                        # a bar chart draws the first category at the bottom
    cd.categories = [c for c, _, _, _ in data]
    cd.add_series("первый STOP, м", [metres(v) for _, _, v, _ in data])
    ch = gf.chart
    ch.replace_data(cd)
    all_category_labels(ch)
    plot = ch.plots[0]
    for dpt in plot.series[0]._element.findall(qc("dPt")):    # every bar is coloured again below
        dpt.getparent().remove(dpt)
    bar_labels(plot, [None] * len(data), size=12)
    colour = {"straight": PINK, "platform": DEEP, "curve": VIOLET}
    for pt, (_, _, _, kind) in zip(plot.series[0].points, data):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = RGBColor.from_string(colour[kind])
    ch.value_axis.maximum_scale = 300                   # the ТЗ's "excellent"; the experts' ideal (16.10)
    ch.value_axis.minimum_scale = 0
    ch.value_axis.major_unit = 100
    ch.category_axis.tick_labels.font.size = Pt(11)
    ch.value_axis.tick_labels.font.size = Pt(10)
    pairs = [
        (21, 18, "Метод судьи 13.10", "лучевая синтетика, реальные фоны"),
        (22, 23, f"Кривые: {rng('B_person')}–{rng('C_person')} м", "ось отстаёт от поворота — в работе"),
        (24, 25, f"С {V12['released']}", f"гермозатвор {metres(RANGE_V100['C_person'])} → {rng('C_person')} м"),
        (26, 27, f"{V12['version']} = 1.1.0", "на данных Pandar"),
    ]
    for ti, di, t, d in pairs:
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=12, bullet=False)
    textbox(sl, Emu(346075), Emu(5820000), Emu(5800000), Emu(520000),
            ["Первый STOP, м; человек — бокс 1,75 м"],
            size=10, color="6B6B6B")


def s_fake(sl):             # template slide 21: column chart (turned into bars) + three cards
    """The organizers' own synthetic obstacles (set O): the only check built by the organizers."""
    title_chip(sl, 2, shape(sl, 13), "ОБЪЕКТЫ ОРГАНИЗАТОРОВ")
    shape(sl, 13).width = Emu(shape(sl, 2).width - 2 * (shape(sl, 13).left - shape(sl, 2).left))
    gf = shape(sl, 10)
    # (name, first STOP m, label replacing the value or None, STOP held); the first category is drawn at the bottom
    data = [(name, metres(first), None, held) for name, first, _, _, held in reversed(list(N["set_o"].values()))]
    cd = CategoryChartData()
    cd.categories = [c for c, _, _, _ in data]
    cd.add_series("первый STOP, м", [v for _, v, _, _ in data])
    ch = gf.chart
    ch.replace_data(cd)
    space = ch._chartSpace
    space.find(".//" + qc("barDir")).set("val", "bar")  # horizontal bars: the category names are long
    for tag, pos in (("catAx", "l"), ("valAx", "b")):
        space.find(".//%s/%s" % (qc(tag), qc("axPos"))).set("val", pos)
    all_category_labels(ch)
    ch.has_legend = False
    plot = ch.plots[0]
    plot.gap_width = 60
    plot.overlap = 0
    bar_labels(plot, [lab for _, _, lab, _ in data], size=11, color="FFFFFF")
    for pt, (_, _, _, held) in zip(plot.series[0].points, data):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = RGBColor.from_string(PINK if held else VIOLET)
    ch.value_axis.maximum_scale = 150
    ch.value_axis.minimum_scale = 0
    ch.value_axis.major_unit = 50
    ch.category_axis.tick_labels.font.size = Pt(11)
    ch.value_axis.tick_labels.font.size = Pt(10)
    if not REFRESH:                             # made once, by the build
        gf.height = Emu(gf.height - 300000)
    textbox(sl, Emu(346075), Emu(gf.top + gf.height + 40000), Emu(5749925), Emu(560000),
            [f"Синтетика; гейт {V12['version']} = 29.09. Сиреневый: неустойчиво."],
            size=10, color="E6E1F5")
    top = set_o("big_above")
    cards = [
        (21, 18, "Доска",
         f"доска — с {set_o_first('long_low_on_rails')} м"),
        (22, 23, "Верх",
         f"{of(top[2:4])}; непрерывно с {metres(top[1])} м"),
        (24, 25, "Кубы",
         f"Кэш: {cubes()} м; node-path: 48–56 м."),
    ]
    for ti, di, t, d in cards:
        fill(placeholder(sl, ti), [t], size=15, bold_all=True)
        fill(placeholder(sl, di), [d], size=11, bullet=False)


def s_falcon(sl):           # template slide 16: four cards (until 19.10 «Надёжность», now in the notes of 27 and 17)
    """The second lidar: the organizers' real Falcon Prime recording through 1.2.0 (FALCON)."""
    title_chip(sl, 10, shape(sl, 14), "ВТОРОЙ ЛИДАР: FALCON")
    f = FALCON
    cards = [
        (49, 37, 38, "Оси и калибровка", "Профили falcon_ros / falcon_native; ориентация — с 1-го кадра; "
                                         "без неё CAUTION, не GO"),
        (50, 39, 40, "Человек", f"Предупреждение со {f['warn_m']} м, STOP с ~{f['stop_m']} м; "
                                f"от {f['stop_band'][0]} до {f['stop_band'][1]} м — STOP в каждом кадре"),
        (51, 41, 42, "Ложные", f"{f['false'][0]} кадров STOP за {f['seconds']} с; CAUTION {f['caution_pct']} % — "
                               "конструкции у края габарита"),
        (52, 43, 44, "300 м", f"Человек виден с ~{f['seen_m']} м ({f['seen_pts']} точек), полотно — до "
                              f"~{f['bed_m']} м; дальность — в работе"),
    ]
    for k, (ni, ti, di, t, d) in enumerate(cards):
        fill(placeholder(sl, ni), [f"0{k + 1}"])
        fill(placeholder(sl, ti), [t], size=15)
        fill(placeholder(sl, di), [d], size=14)


def s_hard(sl):             # template slide 15: five lined rows
    fill(placeholder(sl, 0), ["СЛОЖНЫЕ СЛУЧАИ"])
    rows = [
        "**Столбы:** высокий узкий объект получает CAUTION, не STOP — не исправлено",
        f"**Кривые:** ось отстаёт от поворота; первый STOP с {rng('B_person')}–{rng('C_person')} м — в работе",
        f"**Ложные STOP:** ≈{false_per_hour()} эпизод в час пустого тоннеля ({JUDGE['date']}) — снижаем",
        "**Пыль:** на своей синтетической пыли приёмку не проходим — в работе",
        f"**Мелкое:** кубы 0,3 м — с {cubes()} м; висящий 5 см — с {set_o_first('thin_hanging')} м",
    ]
    for idx, text in zip(range(15, 20), rows):
        ph = placeholder(sl, idx)
        ph.width = Emu(11200000)
        fill(ph, [text], size=13, bullet=False)


def s_next(sl):             # template slide 17: three cards
    fill(placeholder(sl, 0), ["ИТОГИ И ПЛАНЫ"])
    cards = [
        (49, 37, 38, "Что получилось", "ROS 2-модуль на CPU в Docker; два лидара; стабильный 3D-габарит; "
                                       f"пауза и смена бэгов без перезапуска; {V12['tests']} тестов"),
        (50, 39, 40, "Что дальше", "В работе: габарит по повороту, пыль, дальность Falcon к 300 м, "
                                   "меньше ложных STOP"),
        (51, 41, 42, "Внедрение", "docker load → run → run_demo.sh. "
                                  "Адаптер торможения требует разработки и проверки."),
    ]
    for k, (ni, ti, di, t, d) in enumerate(cards):
        fill(placeholder(sl, ni), [f"0{k + 1}"])
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=13)


NOTES = {  # speaker notes per template slide (the main shot's are set in s_hero); the 5-minute speech is
    # docs/PRESENTATION.md «Речь на 5 минут», these are the fuller reference per slide
    8: "Мы — команда «Молоток», четыре инженерные роли. Наше решение называется ReSense. "
       "Описываем нормальный тоннель и ищем препятствия в габарите; возможны пропуски и ложные тревоги.",
    9: "Роли: капитан — ROS 2, Docker, интеграция и питч; визуализация, дашборд, презентация и видео; "
       "компьютерное зрение — модель пути и трекинг; данные, синтетика, метрики и тесты. Каждый отвечал за "
       "свою часть, код общий.",
    10: "Почему эта задача: реальных препятствий в данных почти нет. Мы описываем нормальный тоннель, "
        "а обученное мнение о треке работает на отрицательных примерах из поездок. Ложные остановки "
        f"сократились, но остались. Как мы работали с чужими идеями: {rules_story()}. "
        "Проверка на новых данных нужна.",
    11: "Одной фразой: описываем нормальный тоннель и ищем препятствия в габарите поезда. "
        "Работает в ROS 2 и Docker. Решает геометрия; обученная часть одна — «мнение» о треке, и оно может "
        f"только отложить сомнительный STOP, не больше чем на {opinion_delay()}, но не отменить его. "
        f"Задержку называем с машиной: {e2e()}; стенд организаторов мы не мерили. GPU мы оценили и не "
        "используем: выигрыш — десятки миллисекунд, а контейнер с запросом GPU не стартует на машине без "
        "nvidia-container-toolkit.",
    24: "Почему не нейросеть: реальных препятствий в данных почти нет, а на 100+ м у объекта единицы точек. "
         "Переносимость правил и обученного мнения на другой маршрут требует независимой проверки.",
    12: f"Все числа дальше — на всех {num(frames_total())} кадрах организаторов. Каждая запись обрывается на "
        "209–210 м: дальше в тоннеле нет ни одного отражения, и это предел для любого алгоритма на этих данных.",
    25: f"Пять шагов на каждый кадр. На одном ядре {N['hw']} детектор тратит {N['detector_hw'][0]} в среднем "
        f"(p95 {N['detector_hw'][1]}; замер 28.09, правила 29.09 добавляют ~{N['rules_ms']} мс); это с "
        f"необязательными ядрами на C++, без них время детектора в {native_factor()} раза больше при том же "
        "выходе бит в бит. Калибровка крепления — сама, по рельсам; кривизна — по стенам, поэтому коридор "
        "осмыслен и там, где рельсов уже не видно. Запрет эго-движения: пока поезд едет быстрее 4 м/с, трек, "
        "расстояние до которого не сокращается вместе с ходом поезда, STOP не начинает.",
    27: "Цепочка организаторов прогнана в Docker на реальных записях: узел в одном контейнере, bag play из "
        "другого, от обычного пользователя. Решение — топик /resense/decision: GO, CAUTION, STOP, FAULT. "
         "Слева — дашборд по статусу того же узла. Для исторического проигрывания нужен "
         "freshness_mode:=replay и поддерживаемая процедура из README. Потребителю недостаточно одного "
         "decision: проверяйте время действия /resense/status.",
    20: f"Человек на пути — {of_frames(N['person'])}, тревога {person_alarm()}; три кадра из них — благодаря "
        f"добавке до {num(N['axis_shift_m'])} м по оси лидара ближе {N['axis_near_m']} м, строго от рельсов "
        f"было бы {N['person_rails_only']}. Вся запись — {obstacle_run()} (на кэше гейта; через узел ROS в "
        f"Docker без пропусков — прогон CI 29.09, до правил 29.09); предмет на рельсе — {of(N['rail_object'])}. Одиночный GO в кадре 111 закрыт 29.09 правилом, "
        "подобранным на этой же записи. "
        f"Задержка — {e2e()}. "
        f"Ложных событий в 20-минутной поездке — {per_km()} на км ({N['ride_events']} за {N['ride_km']} км, "
        f"было {N['ride_events_before']} до правил 29.09), но это на тех же данных, где мы подбирали "
        "правила и откуда взяты отрицательные примеры «мнения» о треке. Вне выборки мы мерили только «мнение», "
        f"на детекторе 27.09: каждую пару кусков поездки прогнали с моделью, которая их не видела, — "
        f"{events(N['ride_cv'][1])}, {unseen_km()} на км (в выборке тогда было {N['ride_events_before']}). "
        f"На объектах организаторов большой ящик — с {set_o_first('big_center')} м, кубы 30 см — с {cubes()} м, "
        f"у края — с {edge_from()} м.",
    22: f"Первое подтверждение человека — {set_f('person')} м, медиана шести подходов. В пяти парных подходах — "
        f"{N['anchored_legacy']} м, а если ставить его по ближним рельсам, а не по нашей же дальней оси, — "
         f"{set_f('person_anchored')} м: пять пар на знакомых фонах не доказывают независимость. Со скоростью поезда "
        f"— {N['speed_person']} м; свою скорость мы меряем по лидару с ошибкой {N['speed_err']}, но раньше STOP "
        "она не даёт; с 29.09 она питает запрет эго-движения. Дальше 210 м отражений нет. Всё это синтетика в "
        "реальных кадрах поездки.",
    21: "Это синтетика организаторов на использованных фонах, не скрытая проверка: поезд едет к объектам до "
        f"20 м/с. Большой ящик — с первого появления, {set_o_first('big_center')} м; доска поперёк рельсов — с "
        f"{set_o_first('long_low_on_rails')} м. Кубы 30 см — только с {cubes()} м: на 60–115 м от них 2–4 точки в "
        f"кадре. Висящий предмет 5 см — с {set_o_first('thin_hanging')} м; ящик у верха габарита — непрерывно с "
        f"{set_o_first('big_above')} м. У края — с {edge_from()} м; трек ящика у края — STOP с "
        f"{num(N['edge_box_track_m'])} м, а счётчик засчитывает кадры с {set_o_first('big_edge_inside')} м: он "
        "ищет обнаружение в метре от центра двухметрового ящика. Габарит организаторы отсчитывают от головки "
        f"рельсов (их ответ 29.09); ближе {N['axis_near_m']} м на прямой мы добавляем к нему до "
        f"{num(N['axis_shift_m'])} м по оси лидара — нигде не уже, чем от рельсов; без этой добавки куб у края — "
        f"лишь с {num(N['noref_edge_cube_m'])} м. Синтетика, по словам организаторов, расставлена приблизительно, "
        "и при проверке они это учтут. "
        f"Дальние слабые треки дали ящику у верха габарита и доске {set_o_first('big_above')} и "
        f"{set_o_first('long_low_on_rails')} м вместо {N['nofar_first'][0]} и {N['nofar_first'][1]}. "
        f"Ложный STOP у ящика снаружи габарита — {N['fake_outside_false']} "
        f"{plural(N['fake_outside_false'], 'кадр', 'кадра', 'кадров')} на кэше гейта, с "
        f"{metres(N['fake_outside_from_m'])} м; на исходной записи детектор 27.09 давал {N['fake_outside_orig']} "
        f"кадров подряд на {N['fake_outside_m'][0]}–{N['fake_outside_m'][1]} м: обнаружение на его внутреннем крае.",
    16: "Калибруем поддерживаемое крепление и находим вход. При потере свежести — FAULT либо "
        "удержание STOP с последней дистанцией; потребителю нужен свой таймер статуса. "
        "Ложный STOP на пустой сцене больше не зависит от того, как узел получал кадры: в записанных историях "
        f"узла — {N['history_captured'][1]} (было {N['history_captured'][0]}), в стресс-тесте с пропусками и "
        f"догонялками — {events(N['history_stress'][1])} (было {N['history_stress'][0]}; 28.09).",
    15: "Что не сработало и почему: полотно полно железа, станции — главный источник ложных остановок, "
        "мелкие объекты организаторов видим поздно, тонкие — только вблизи. Два правила 29.09 взяты из "
        "открытых решений других команд (TunnelGuard, Tactical-Inventor) и прошли полный гейт: «чистая серия» — "
        "новый STOP у известной инфраструктуры ждёт пять чистых попаданий; запрет эго-движения — трек дальше 25 м, "
        "который едет вместе с поездом, STOP не начинает, пока поезд быстрее 4 м/с. Третье — «обделку» — мы "
        "выключили после своей проверки безопасности: висящий от свода кабель получал STOP лишь с "
        f"{N['shell_cable_m'][0]} м вместо {N['shell_cable_m'][1]} м. Независимая проверка 13.10 "
        "нашла другие пропуски v1.0.0, описанные ниже. "
        "«Мнение» о треке обучено на "
        "синтетике: непохожий реальный объект — мусор, лежащий человек — оно может задержать, но "
        f"{opinion_bounds()}; предел {N['opinion_near_m']} м действует и по предсказанной дистанции, пока трек "
        "не виден; STOP оно никогда не отменяет. "
        "Порог — половина наибольшего, который не задерживает ни одного отложенного синтетического объекта; "
        f"без этого запаса на детекторе 27.09 было бы {N['ride_zero_margin'][0]} событий в поездке и "
        f"{N['ride_zero_margin'][1]} на невиданных кусках — запас оставили ради безопасности.",
    17: "Итог: работающий модуль, честные цифры, понятные следующие шаги — мелкие объекты раньше, скорость "
        "от одометрии, независимая проверка двух правил 29.09 и замер на стенде организаторов.",
}

# PT1 pass 1: keep the technical detail in the notes, with its pipeline and date. The visual cuts do
# not turn the gate's cache numbers or older VM timings into measurements of a future release.
NOTES[8] += (" Модель включает полотно, рельсы, ось и кривизну по стенам. Выходы GO / CAUTION / STOP / FAULT "
             "и расстояние; обученное мнение только задерживает сомнительный STOP в ограниченном бюджете. "
             "Дальность контроля — оценка, пропуски возможны и внутри неё.")
NOTES[10] += (" Станции и стрелки похожи на препятствия; нужны доверенная ось и подтверждение 0,5 с. "
              "Входы 120°/360° и два топика; крепление калибруется по рельсам.")
NOTES[11] += (f" Реальный человек — {of_frames(N['person'])}; кэш шлюза 29.09: {per_km()} события/км, "
              f"не node-path. {JUDGE['date']} на {JUDGE['vcpus']} vCPU нода 360° дала p95 "
              f"{JUDGE['node_360_p95_ms']} мс, только 35/201 актуальных результатов; "
              "исторические 81–82 мс на ВМ команды 28.09 этого не опровергают.")
NOTES[24] += (" Цели ТЗ: 100 / 200 / 300 м. При 80 км/ч и замедлении 1–1,3 м/с² тормозной путь "
              "190–250 м без задержек. Сравнение с картой требует локализации. "
              "Качество обученного 3D-детектора на этих тоннелях не измерялось.")
NOTES[12] += (f" Шесть записей: {num(N['frames_six'])} кадров; поездка {num(N['frames_ride'])}, "
              f"20 минут, {N['ride_km']} км, 7 остановок, кривые R≈350 м. Дополнительно набор O: "
              f"{num(N['fake_frames'])} кадров синтетики организаторов. Объект 0,5 м: около 7 точек "
              "на 100 м и 1–2 на 200 м; стены видны на 150–200 м, полотно примерно до 100 м. "
              "Предел ~210 м относится к исходным реальным отражениям, не добавленной синтетике: "
              "судья 13.10 нашёл добавленные точки набора O до ~298 м.")
NOTES[20] += (f" Пять пустых записей на кэше: {events(N['empty_events'])}, "
              f"{N['empty_episodes']} эпизодов; поездка {N['ride_events']} событий / {N['ride_episodes']} "
              "эпизодов. Проверка 13.10 v1.0.0: пять бэгов 4 эпизода / 13 кадров; поездка "
              f"{JUDGE['ride_episodes']} эпизода / 160 кадров, ≈2,5 эпизода/км. "
              "Эпизод — серия STOP, событие шлюза — подтверждённый трек; сравнивать их как одну метрику нельзя. "
              "Все частоты в выборке. Нода на 4 vCPU: p95 111 мс на 360°, 84 мс на 120°; "
              "это время обработки, не возраст результата. Первая версия графиков — подготовка PT1; "
              "окончательные числа и речь обновляет P1 после J1 и O1.")
NOTES[22] += (f" Исторические кривые набора F, 24.09: {N['curves'][0]} подходов, {N['curves'][1]} м. "
              f"Устойчивость человека ≥90% каждой 10-метровой полосы — с {N['band_person']} м. "
              "Нынешняя оценка 13.10 v1.0.0: лучевой человекообразный бокс 218 м на прямой, "
              "52 м на кривой в двухпутность, 74 м на кривой с гермозатвором, 106 м перед платформой; "
              "идеальные возвраты на собственной оси — благоприятная постановка. Это не реальные люди "
              "и не J1 следующей печати. После J1 заменить этот исторический график на ≥3 геометрии пути.")
NOTES[21] += (f" Ящик у верха габарита на кэше: {of(set_o('big_above')[2:4])} кадров STOP. "
              "Куб на рельсе / по центру: 42,7 / 55,8 м на кэше; 48,0 / 55,8 м node-path 13.10, "
              "краевой куб 35 м в обоих. Ранее заявленная проверка новых мест относится к старому "
              "детектору 27.09, не к выпущенной или будущей версии.")
NOTES[16] += (" 8 проверенных ориентаций вокруг вертикальной оси — не любое крепление. "
              "Свежесть проверяет также потребитель. Удаление двойных возвратов меняет модель пути "
              "и решения (проверка 13.10); побитовое совпадение numpy/C++ этого не исключает.")
NOTES[15] += (f" История: наивный порог полотна давал 1 482 события за 20 минут; набор F box0.5 "
              f"на кэше найден в {of(N['bed_box_found'])} подходов. На рельсе — {of(N['rail_object'])} кадров; "
              "правило удержания 0,3 с подобрано на doubleT_obstacle. Два критичных пропуска "
              "обнаружены независимо 13.10: tall narrow → column и oversize merge на кривой. "
              "Исправления final/silent-misses ещё не прошли весь цикл выпуска; не объявлять их готовыми.")
NOTES[17] += (" План после оценки: BACKLOG, H1–H6 перед выпуском, затем J1. "
              "Новая печать, проверка на нетронутых данных G3, дальность по геометриям, свежесть S1, "
              "стенд S5; подключение к торможению требует отдельной разработки и проверки.")

# PT1 pass 2 (19.10): the deck for the defence of 23.10 shows 1.2.0 (V12) and the experts' criteria of 16.10.
# The notes of every slide whose text changed are rewritten here; each number names its source. The 5-minute
# speech, the Q&A drill and the numbers table: docs/PRESENTATION.md.
_V = V12["version"]
_F = FALCON
SRC_FALCON = ("прогон капитана 19.10: вся запись через aec88d2, решения совпадают с прогоном 1.1.0 "
              "docs/evidence/falcon_full_2026-10-18 (B2)")
NOTES[11] = (
    "Одной фразой: описываем нормальный тоннель и ищем препятствия в габарите поезда; ROS 2 и Docker, только CPU. "
    f"Версия: показываем и развиваем {_V} — кандидат, запечатанная сборка разработки на main {V12['commit']} "
    "(измеренный источник 0779db7, файлы детектора те же; detector_freeze verify PASS, 38 файлов). Она не выпущена, "
    "даты выпуска нет. 1.1.0 выпускаться не будет (решение капитана 19.10). Опубликован "
    f"{V12['released']} — его эксперты оценивали 30.09–14.10; {V12['judge_score']}/100 от 13.10 — оценка нашего "
    "независимого агента-судьи, не организаторов. Лидары: Pandar128 (все записи организаторов) и Falcon Prime "
    "(реальная запись 16.10; профили осей falcon_ros / falcon_native). Решает геометрия; обученная часть одна — "
    f"«мнение» о треке: оно может только отложить сомнительный STOP, не больше чем на {opinion_delay()}, но не "
    f"отменить его. Задержку называем с машиной: {e2e()}; {JUDGE['date']} на {JUDGE['vcpus']} vCPU нода 360° — "
    f"p95 {JUDGE['node_360_p95_ms']} мс, 120° — {JUDGE['node_120_p95_ms']} мс ({V12['released']}); Falcon — "
    f"детектор {_F['detect_ms']} мс на кадр, медиана (прогон капитана 19.10). Стенд организаторов мы не мерили. "
    "GPU оценили и не используем: выигрыш — десятки миллисекунд, а контейнер с запросом GPU не стартует без "
    "nvidia-container-toolkit. Источники: CHANGELOG [1.2.0]; docs/evidence/b4_merge_reseal_2026-10-18/README.md; "
    "docs/evidence/version_1.2.0_2026-10-18/README.md; docs/evidence/judgement_2026-10-13/README.md §5.")
NOTES[12] = (
    f"Pandar128: {num(frames_total())} реальных кадров организаторов — шесть записей ({num(N['frames_six'])}) и "
    f"поездка ({num(N['frames_ride'])}, 20 минут, {N['ride_km']} км, 7 остановок, кривые R≈350 м). Каждая запись "
    "обрывается на 209–210 м: дальше нет ни одного отражения. Набор O — "
    f"{num(N['fake_frames'])} кадров синтетики организаторов (добавленные точки — до ~298 м, судья 13.10). Объект "
    "0,5 м: около 7 точек на 100 м и 1–2 на 200 м; стены видны на 150–200 м, полотно примерно до 100 м. "
    f"Falcon Prime (Seyond), выдан 16.10: реальная запись falcon_test_second_dark, {num(_F['frames'])} кадра за "
    f"{_F['seconds']} с; поезд стоит, человек идёт по пути к нему. Топик /iv_points, оси ROS (+X вперёд, +Y влево, "
    "+Z вверх), ~95 тыс. точек на кадр, без поля ring; сырые отражения до 510 м, узел обрезает на "
    f"{_F['crop_m']} м (docs/evidence/n2_falcon_2026-10-18/README.md). Паспорт: {_F['datasheet_m'][0]} м при "
    f"отражательной способности 10 %, максимум {_F['datasheet_m'][1]} м (docs/sensor/falcon_prime/README.md). "
    f"Три новые синтетические записи организаторов: {num(N5_FRAMES)} кадров, 12 объектов; разметку сделали сами, "
    "от организаторов её нет (docs/evidence/n5_labels_2026-10-17/README.md). Все эти записи — данные разработки: "
    "по ним настраивали и проверяли, скрытой проверки у нас нет.")
NOTES[25] += (" Габарит в RViz и веб-виде — 3D-бокс: ширина 2,1 м, от 0,12 до 3,0 м над головкой рельса; рисуется "
              "только там, где ось подтверждена геометрией, и не дальше доверенной дальности. Сглаживание — только "
              "для картинки, в решения не возвращается; при устаревшем входе бокс сереет и исчезает "
              "(docs/evidence/n1_n4_2026-10-18/HOWTO.md).")
NOTES[27] = (
    f"Живой показ — версия {_V} (образ, собранный из main {V12['commit']}). Один узел: сначала Pandar, запись "
    "doubleT_obstacle — STOP около 56 м в первые секунды; затем без перезапуска контейнера Falcon с профилем "
    "falcon_ros — ориентация с первого кадра, 3D-бокс габарита, CAUTION у конструкций, STOP по человеку. Пробел — "
    "пауза, стрелки вверх и вниз — скорость. Проверено 18.10 на образе разработки cecab1b: 40 из 40 кадров "
    "Pandar, затем 100 из 100 кадров Falcon в одном узле, без перезапуска и потерь; пауза и смена скорости "
    "0,5 → 0,4 работают (docs/evidence/n1_n4_2026-10-18/README.md). Слева — снимок RViz того же отображения на "
    "кривой (программный рендер, 18.10): бокс короче там, где ось не подтверждена. Справа — запасной ролик "
    f"docker_chain_rviz.mp4: архив 23.09 (v0.6.2), не {_V}. Надёжность: нет свежих данных — FAULT или удержание "
    "STOP; потребитель проверяет время действия /resense/status своим таймером; при смене бэга узел явно "
    "сбрасывает очередь, калибровку, треки и свежесть. Команды: docs/PRESENTATION.md «Демонстрация», "
    "docs/evidence/n1_n4_2026-10-18/HOWTO.md.")
NOTES[20] = (
    f"По критериям экспертов 16.10. {of(N['person'])}: человек в габарите на реальной записи doubleT_obstacle — "
    f"STOP в каждом кадре, {person_alarm()}; вся запись — {obstacle_run()}; предмет на рельсе — "
    f"{of(N['rail_object'])} (гейт 29.09 = гейт {_V}; независимая оценка 13.10 воспроизвела). ~{_F['stop_m']} м: "
    f"Falcon, первый STOP по идущему человеку — 124,8 м на 297 с ({SRC_FALCON}). ≤ {GAUGE['jitter_max']} м: "
    "дрожание видимого края габарита между кадрами, p90 на 40 / 80 / 120 м — "
    f"{' / '.join(GAUGE['jitter_set_o'])} м на наборе O при пределах {' / '.join(GAUGE['limits'])} м "
    "(docs/evidence/n1_n4_2026-10-18/README.md); цена — на кривой бокс медианно "
    f"{GAUGE['curve_drawn_m'][0]} м из {GAUGE['curve_drawn_m'][1]} м поддержанных. Дальность — следующий слайд. "
    f"Пропуски: STOP у {set_o_stopped()} объектов организаторов в габарите (гейт); известные пропуски — столбы и "
    f"мелкое вдали (слайд «Сложные случаи»). Ложные: {N['ride_events']} событий / {N['ride_episodes']} эпизодов "
    f"STOP за {N['ride_km']} км поездки на кэше гейта — в выборке, правила подбирали на этих данных; узловой путь "
    f"судьи {JUDGE['date']} ({V12['released']}): {JUDGE['ride_episodes']} эпизода, ≈2,5 эпизода/км; все пустые "
    f"данные — {JUDGE['empty_episodes']} эпизодов за {num(JUDGE['empty_s'])} с, ≈{false_per_hour()} в час; на "
    f"этих записях {_V} даёт те же решения. Falcon: {_F['false'][0]} ложных кадров STOP за {_F['seconds']} с. "
    f"10 Гц: Falcon — детектор {_F['detect_ms']} мс на кадр, медиана (прогон капитана 19.10); Pandar 360° — нода "
    f"p95 {JUDGE['node_360_p95_ms']} мс на {JUDGE['vcpus']} vCPU, 120° — {JUDGE['node_120_p95_ms']} мс "
    f"({JUDGE['date']}, {V12['released']}); стенд организаторов не мерили. Запуск: run_demo.sh / play_bag.sh "
    "--interactive — пауза, замедление, несколько бэгов в одном узле, RViz в контейнере, программный рендер "
    "(docs/evidence/n1_n4_2026-10-18/HOWTO.md). «Фильтр» (критерий 7) организаторы не определили — вопрос "
    "отправлен. Эпизод — серия STOP, событие гейта — подтверждённый трек: это разные метрики.")
NOTES[22] = (
    "Дальность — по форме пути, а не одним числом. Метод судьи 13.10, повторён 16.10 на 1.1.0: неподвижный бокс "
    "ставится в 230 м впереди на собственную ось детектора и высоту головки рельса и лучами вписывается в "
    "реальные кадры 120°; возвраты идеальные — постановка благоприятная, это не реальные люди. Первый STOP: прямая "
    f"— человек (бокс 0,5 × 0,5 × 1,75 м) {rng('A_person')} м, куб 1 м — {rng('A_cube1')} м, куб 0,3 м — "
    f"{rng('A_cube03')} м; перед платформой — {rng('D_person')} м; кривые с гермозатвором — {rng('C_person')} м; "
    f"кривая в двухпутный участок — {rng('B_person')} м. На кривых объект виден раньше, но ось пути отстаёт от "
    "поворота (наша кривизна −0,0006…−0,0011 против −0,0025 1/м по трём независимым свидетелям, "
    "docs/evidence/gauge_stability_2026-10-18/README.md); исправление оси (K1/K2) в работе, результата пока нет. "
    f"С {V12['released']} изменилась только кривая с гермозатвором: {metres(RANGE_V100['C_person'])} → "
    f"{rng('C_person')} м. {_V} = 1.1.0 на данных Pandar: полный гейт и X3 (40 случаев, 29 765 строк) совпадают во "
    "всех не-временных выходах (docs/evidence/b4_merge_reseal_2026-10-18/README.md); сами задания дальности на "
    f"{_V} не перезапускались. Источник: docs/evidence/rejudge_2026-10-16/prebuild/summary_1.1.0.json, "
    "range_table.md, RELEASE_DAY.md. Прежний график — наша синтетика в прямой поездке (набор F, гейт 29.09): "
    f"человек {set_f('person')} м, тележка {set_f('trolley')}, ящик 1 м {set_f('crate')}, кабель 3 см "
    f"{set_f('cable')}; со скоростью поезда — {N['speed_person']} м. Pandar в этих записях не даёт отражений "
    "дальше 209–210 м.")
NOTES[21] += (f" Версия {_V} даёт те же числа: её гейт совпадает с гейтом 29.09 (build_deck.py --check-gate "
              "docs/evidence/b4_merge_reseal_2026-10-18/gate.json → GATE matches, 19.10).")
NOTES[16] = (
    f"Второй лидар — Seyond Falcon Prime, реальная запись организаторов: {num(_F['frames'])} кадра за "
    f"{_F['seconds']} с, поезд стоит, человек идёт по пути к нему. Оси у Pandar и Falcon разные, профиль "
    "выбирается явно: pandar128 (−Y/+X/+Z), falcon_ros (+X/+Y/+Z, как в записи), falcon_native (+Z/−Y/+X, "
    "нативные оси корпуса); из имени топика он не выводится. Автокалибровка ищет ориентацию; пока она не "
    "подтверждена — CAUTION с нулевой свободной дальностью, никогда не молчаливый GO. На этой записи правильная "
    f"ориентация принята с первого кадра; наклон по детектору {_F['pitch'][0]}, по независимой подгонке плоскости "
    f"полотна {_F['pitch'][1]}; лидар в {_F['height_m']} м над головкой рельса. Человек: первое предупреждение — "
    f"со {_F['warn_m']} м, первый STOP — около {_F['stop_m']} м (124,8 м, 297 с), от {_F['stop_band'][0]} до "
    f"{_F['stop_band'][1]} м — STOP в 100 % кадров. Ложные: {_F['false'][0]} кадров STOP за {_F['seconds']} с — "
    f"{_F['false'][1]} на неподвижной конструкции в {_F['false'][2]} м и {_F['false'][3]} на участке пола в "
    f"{_F['false'][4]} м; причина второго не установлена. CAUTION на {_F['caution_pct']} % кадров: две неподвижные "
    f"конструкции у края габарита, {_F['caution_m'][0]} и {_F['caution_m'][1]} м. 300 м: человек виден лидару с "
    f"~{_F['seen_m']} м ({_F['seen_pts']} точек), а первый STOP — с ~{_F['stop_m']} м; работа над дальностью "
    f"Falcon идёт, результата пока нет. По паспорту — {_F['datasheet_m'][0]} м при отражательной способности 10 % "
    f"(максимум {_F['datasheet_m'][1]} м); в этом тоннеле полотно и рельсы не отражают дальше ~{_F['bed_m']} м, "
    f"поэтому габарит дальше можно только продлевать; код обрезает облако на {_F['crop_m']} м. Детектор — "
    f"{_F['detect_ms']} мс на кадр, медиана. Источники: {SRC_FALCON} (первый STOP 124,8 м; ложные 4 + 8 кадров; "
    "CAUTION 3 062 из 4 443); профили и ориентация — docs/evidence/n2_falcon_2026-10-18/README.md; паспорт — "
    "docs/sensor/falcon_prime/README.md. Наклон, высота, первое предупреждение и время на кадр — замеры капитана "
    "19.10, пока не в коммите.")
NOTES[15] = (
    "Честно о слабом. Столбы: высокий узкий объект в габарите понижается до CAUTION (правило column) — критичный "
    "пропуск, найден независимой оценкой 13.10; исправление H1 отозвано 16.10, потому что теряло другие "
    f"положительные (CHANGELOG [1.1.0]); в {_V} не исправлено. Кривые: ось пути отстаёт от поворота, первый STOP "
    f"{rng('B_person')}–{rng('C_person')} м; исправление оси (K1/K2) в работе. Ложные STOP: судья "
    f"{JUDGE['date']} — {JUDGE['empty_episodes']} эпизодов за {num(JUDGE['empty_s'])} с пустого тоннеля "
    f"(≈{false_per_hour()} в час), CAUTION на {JUDGE['caution_pct']} % пустых кадров ({V12['released']}; на этих "
    f"записях {_V} даёт те же решения); главные источники — платформы, стрелки, конструкции у края; работа F1 "
    "идёт, результата нет. Пыль: свой генератор синтетической пыли и полное измерение — 30 875 прогонов кадров "
    "на 9b92df5 (= 1.1.0); при средней плотности пустые записи дают 22–71 эпизод STOP вместо 0–3, реальный "
    "человек теряется; нашу приёмку детектор не проходит, работа идёт, исправления нет "
    "(docs/evidence/n3_dust_2026-10-18/README.md). Мелкое: кубы 0,3 м — STOP с "
    f"{cubes()} м, ящик 0,5 м на полотне — в {of(N['bed_box_found'])} подходов; висящий предмет 5 см — с "
    f"{set_o_first('thin_hanging')} м. Как мы работаем с чужими идеями: {rules_story()}. «Мнение» о треке обучено "
    f"на синтетике: непохожий реальный объект оно может задержать, но {opinion_bounds()}; STOP оно никогда не "
    "отменяет.")
NOTES[17] = (
    "Итог: работающий ROS 2-модуль на CPU в Docker; два лидара с явными профилями осей; габарит — стабильный "
    "3D-бокс по поддержанной геометрии; запуск с паузой, замедлением и сменой бэгов без перезапуска. Тесты: "
    f"{V12['tests']} тестов хост-набора кандидата 18.10 (cecab1b, плюс 12 подтестов; "
    "docs/evidence/version_1.2.0_2026-10-18/README.md); слияние B4 — 676 затронутых тестов "
    "(docs/evidence/b4_merge_reseal_2026-10-18/README.md). В работе, без результатов: габарит синхронно с "
    "поворотом (K1/K2), устойчивость к пыли, дальность Falcon к 300 м, меньше ложных STOP (F1). "
    f"{_V} — кандидат, не выпущен: облачный CI заблокирован биллингом аккаунта, даты выпуска нет. Подключение к "
    "торможению требует отдельной разработки и проверки безопасности. Вопросы организаторам — формат питча, "
    "можно ли показать и перепрогнать обновлённую версию, как читать CAUTION, что в скрытом наборе, что такое "
    "«фильтр», новые данные, проигрывание бэгов — отправлены капитаном; ответов пока нет.")


def slide_word_counts(prs):
    """Count slide text, including grouped shapes, tables and chart labels (not speaker notes).

    Whitespace counting matches PT1's original audit; include numeric labels and chart categories
    so moving prose into a chart cannot evade the limit. Raster screenshots are illustrations.
    """
    counts = []
    for slide in prs.slides:
        texts = []
        for sh in _walk(slide.shapes):
            if sh.has_text_frame:
                texts.append(sh.text)
            if sh.has_table:
                texts.extend(cell.text for row in sh.table.rows for cell in row.cells)
            if sh.has_chart:
                chart = sh.chart
                if chart.has_title and chart.chart_title.has_text_frame:
                    texts.append(chart.chart_title.text_frame.text)
                for plot in chart.plots:
                    texts.extend(str(c.label) for c in plot.categories)
                    if chart.has_legend:
                        texts.extend(s.name for s in plot.series)
                    for series in plot.series:
                        for point, value in zip(series.points, series.values):
                            if point.data_label.has_text_frame:
                                texts.append(point.data_label.text_frame.text)
                            elif plot.has_data_labels:
                                # e.g. 0" м" renders two words (111 м), not just the number.
                                units = " ".join(re.findall(r'"([^"]*)"', plot.data_labels.number_format))
                                texts.append(f"{value} {units}")
                axis = chart.value_axis
                lo, hi, step = axis.minimum_scale, axis.maximum_scale, axis.major_unit
                if lo is not None and hi is not None and step and step > 0:
                    texts.extend(str(lo + i * step) for i in range(int((hi - lo) / step) + 1))
        counts.append(len(" ".join(texts).split()))
    return counts


def audit_deck(prs):
    """PT1's strict task limit (80/slide) and acceptance total (1,100), printed for the handoff."""
    counts = slide_word_counts(prs)
    for index, count in enumerate(counts, 1):
        print(f"slide {index:02}: {count} words")
    print(f"total: {sum(counts)} words; max: {max(counts, default=0)}; limits: 1100 total / 80 per slide")
    return 0 if counts and sum(counts) <= 1100 and max(counts) <= 80 else 1

# template slide number -> filler, in the order of the deck
PLAN = [(7, None), (8, s08_team), (9, s09_cards), (10, s10_history), (11, s11_short),
        (24, s_problem), (12, s_data), (25, s_algorithm), (13, s_hero), (27, s_demo), (20, s_results),
        (22, s_range), (21, s_fake), (16, s_falcon), (15, s_hard), (17, s_next)]
# the template's layout of each planned slide: --refresh checks that a deck's slides are the planned ones
LAYOUTS = {7: "Титульный слайд", 8: "1_Описание команды", 9: "Команда", 10: "Команда", 11: "Содержание_1",
           24: "Проблема и решение", 12: "Заголовок и объект", 25: "Стадии", 13: "Заголовок и объект",
           27: "1_Демо_1", 20: "Пункты", 22: "2_Статистика", 21: "Статистика", 16: "Содержание_1",
           15: "Пункты", 17: "Содержание_1"}
# kept as built: the title and the team slides (the named build's names and photos come only from --team)
KEEP_ON_REFRESH = (7, 8, 9)


def refresh(path, out=None):
    """Re-fill a deck built by this script (e.g. the committed named deck) in place: the texts, charts and
    notes of every slide but the title and the team slides, as a build from the template writes them now."""
    global REFRESH
    prs = Presentation(path)
    slides = list(prs.slides)
    if len(slides) != len(PLAN):
        raise SystemExit(f"{path}: {len(slides)} slides, the plan has {len(PLAN)}")
    for k, (sl, (tmpl, fn)) in enumerate(zip(slides, PLAN), 1):
        if sl.slide_layout.name != LAYOUTS[tmpl]:
            raise SystemExit(f"{path}: slide {k} has layout {sl.slide_layout.name!r}, the plan {LAYOUTS[tmpl]!r}")
    REFRESH = True
    try:
        for sl, (tmpl, fn) in zip(slides, PLAN):
            if tmpl not in KEEP_ON_REFRESH:
                fn(sl)
            if tmpl in NOTES:
                notes(sl, NOTES[tmpl])
    finally:
        REFRESH = False
    check_no_fields(prs)
    if audit_deck(prs):
        raise ValueError("deck exceeds PT1's word budget; move detail into speaker notes")
    prs.save(out or path)
    print(f"{out or path}: refreshed {len(PLAN) - len(KEEP_ON_REFRESH)} of {len(PLAN)} slides, notes on all")


def check_no_fields(prs):
    """no unfilled "<...>" field on any slide, public or private (the judges read them as unfinished)"""
    placeholders = []
    for slide_number, slide in enumerate(prs.slides, 1):
        for sh in _walk(slide.shapes):
            if sh.has_text_frame and re.search(r"<[^<>\n]+>", sh.text):
                placeholders.append(slide_number)
    if placeholders:
        raise ValueError(f"deck still has placeholders on slides {sorted(set(placeholders))}")


def gate_from_baseline(path):
    """GATE's keys read from a regression baseline / gate JSON (the keys named in the GATE comments)."""
    import json
    with open(path, encoding="utf-8") as fh:
        b = json.load(fh)
    obst = b["recordings"]["doubleT_obstacle"]
    lab = obst["labelled"]["per_label"]
    objs = b["set_O"]["objects"]
    kinds = b["set_F_straight"]["kinds"]

    def held(o):
        return not any(i["start_frame"] > o["first_stop_frame"] for i in o.get("missed_intervals", []))

    return {
        "empty_events": b["five_empty"]["alarm_events"],
        "empty_episodes": b["five_empty"]["stop_episodes"],
        "ride_events": b["ride"]["alarm_events"],
        "ride_episodes": b["ride"]["stop_episodes"],
        "obstacle_stop": (obst["alarm_frames"], obst["frames"]),
        "obstacle_first_frame": obst["first_alarm_frame"],
        "person": (lab["person_crossing"]["hits"], lab["person_crossing"]["frames"]),
        "rail_object": (lab["object_on_rail_from_frame_75"]["hits"], lab["object_on_rail_from_frame_75"]["frames"]),
        "set_o_inside": (b["set_O"]["inside_objects_with_stop"], b["set_O"]["inside_objects"]),
        "set_o_outside": (b["set_O"]["outside_false_stop_frames"], objs["big_outside"]["false_stop_from_m"]),
        "set_o": {k: (objs[k]["first_stop_m"], objs[k]["stop_frames"], objs[k]["visible_frames"], held(objs[k]))
                  for k in GATE["set_o"]},
        "set_f": {k: kinds[k]["first_detection_median_m"] for k in GATE["set_f"]},
        "bed_box_found": (kinds["box0.5"]["detected"], kinds["box0.5"]["sequences"]),
    }


def check_gate(path):
    """Print every GATE line that differs from the baseline at ``path`` (with the value to write); 0 if none."""
    new = gate_from_baseline(path)
    diff = []
    for key, value in new.items():
        if isinstance(value, dict):
            diff += [(f"{key}[{k!r}]", GATE[key][k], v) for k, v in value.items() if GATE[key][k] != v]
        elif GATE[key] != value:
            diff.append((key, GATE[key], value))
    for key, old, value in diff:
        print(f"GATE {key}: deck {old!r} -> baseline {value!r}")
    print(f"{path}: {len(diff)} GATE value(s) differ" if diff else f"{path}: GATE matches")
    return 1 if diff else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--template", help="the organizers' template exported as .pptx")
    ap.add_argument("--out")
    ap.add_argument("--team", default=None, help="JSON with the team's names and photos (the JSON and photos stay "
                                                 "out of git; keys as TEAM, photo paths relative to the file)")
    ap.add_argument("--check-gate", metavar="BASELINE_JSON",
                    help="compare GATE with a regression baseline / gate JSON and exit (no build)")
    ap.add_argument("--audit", metavar="PPTX", help="count visible words and check PT1's 80/slide, 1100 total limits")
    ap.add_argument("--refresh", metavar="PPTX", help="re-fill the texts, charts and notes of a deck this script built "
                                                      "(slides 4-16; title, names and photos kept), in place or to --out")
    ap.add_argument("--check-node-source", metavar="DECLARATION_JSON", help="verify explicit P4 node-path source references (separate from GATE)")
    ap.add_argument("--render-node-chart", metavar="DIRECTORY", help="with --check-node-source: render the complete source table and shared card input")
    ap.add_argument("--final-node-source", action="store_true", help="require release/raw verification and recorded P1/P4 approvals")
    a = ap.parse_args()
    if a.check_node_source:
        from p2_chart_sources import load_sources, render_sources
        data = load_sources(a.check_node_source, final=a.final_node_source)
        if a.render_node_chart:
            render_sources(a.check_node_source, a.render_node_chart, final=a.final_node_source)
        print(f"node source parity PASS: {len(data['rows'])} rows; declaration {data['declaration_sha256']}")
        return
    if a.check_gate:
        raise SystemExit(check_gate(a.check_gate))
    if a.audit:
        raise SystemExit(audit_deck(Presentation(a.audit)))
    if a.refresh:
        refresh(a.refresh, a.out)
        return
    if not a.template or not a.out:
        ap.error("--template and --out are required (unless --check-gate, --audit or --refresh)")
    if a.team:
        import json
        with open(a.team, encoding="utf-8") as fh:
            data = json.load(fh)
        validate_private_team(data, os.path.dirname(os.path.abspath(a.team)))
        TEAM.update(data)
        TEAM["_dir"] = os.path.dirname(os.path.abspath(a.team))
    prs = Presentation(a.template)
    slides = list(prs.slides)
    # the "Московский транспорт" logo from the template's logo slide (6)
    logo = None
    for sh in slides[5].shapes:
        if sh.shape_type == 13 and sh.left == 8797880 and sh.top == 3680027:
            logo = sh.image
    logo_path = os.path.join(os.path.dirname(os.path.abspath(a.out)), "_logo_mostrans." + logo.ext)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(logo_path, "wb") as f:
        f.write(logo.blob)
    for num, fn in PLAN:
        sl = slides[num - 1]
        if num == 7:
            s07_title(sl, logo_path)
        else:
            fn(sl)
        if num in NOTES:
            notes(sl, NOTES[num])
    cp = prs.core_properties
    cp.title = "ReSense — ЛЦТ 2026, кейс 05: посторонние объекты в тоннеле метро по данным 3D-лидара"
    cp.author = cp.last_modified_by = f"Команда «{TEAM_NAME}»"
    cp.subject = "Лидеры цифровой трансформации 2026"
    cp.keywords = "LiDAR, ROS 2, метро, габарит, обнаружение препятствий"
    # the layouts' sample prompts ("Образец текста", "Заголовок", ...) are never shown by PowerPoint,
    # but LibreOffice and a PDF export draw some of them: blank them in the layouts the deck uses
    for num, _ in PLAN:
        for ph in slides[num - 1].slide_layout.placeholders:
            if ph.placeholder_format.type in (1, 3, 13, 15, 16) or not ph.has_text_frame:   # titles, numbers, dates, footers
                continue
            for t in ph.text_frame._txBody.iter(qa("t")):
                t.text = ""
    # keep only the planned slides, in the planned order
    lst = prs.slides._sldIdLst
    ids = list(lst)
    keep = [ids[num - 1] for num, _ in PLAN]
    for sid in ids:
        lst.remove(sid)
        if sid not in keep:
            prs.part.drop_rel(sid.rId)
    for sid in keep:
        lst.append(sid)
    check_no_fields(prs)
    if audit_deck(prs):
        raise ValueError("deck exceeds PT1's word budget; move detail into speaker notes")
    prs.save(a.out)
    os.remove(logo_path)
    print(f"{a.out}: {len(keep)} slides")


if __name__ == "__main__":
    main()
