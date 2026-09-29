#!/usr/bin/env python3
"""Fill the organizers' presentation template with the ReSense deck.

The template (37 slides, Montserrat, "Лидеры цифровой трансформации 2026") is exported from
Google Slides:

    curl -L -o template.pptx \\
      https://docs.google.com/presentation/d/17ciElVAWgeuPLiFHw7y5HMaAXmTo7g16/export/pptx
    python scripts/build_deck.py --template template.pptx --out docs/presentation/ReSense_LCT2026.pptx

Slides 7-11 (title, team, team cards, history, solution in short) keep their design and
structure as the organizers require; the solution slides use the template's own layouts
(12-29). Every measured number on the slides and in the speaker notes is written once, in ``N``
below, each with its source and, for timings, its machine: the current detector's regression gate
``BASELINE`` (29.09 evening, the three false-alarm rules on, run ``r_1e2ed82`` on the 1 cm frame
cache), the node checks of 29.09 (docs/evidence/frame111_2026-09-29), the 28.09 VM and judgement
timings, and older dated measurements (docs/archive/EXPERIMENTS_log_2026-09.md, docs/archive/P4_AUDIT.md),
which the slides date; the texts derive the rest (per km, ranges, counts). The build refuses a deck
with a ``<...>`` field on any slide. The pictures are made by ``scripts/hero_view.py`` and ``resense run
--render`` (``docs/img/``) and by the web UI's gallery (``docs/images/``; paths in ``IMG``).

The PDF next to the deck is LibreOffice's export (Impress and the Montserrat fonts installed):

    soffice --headless --convert-to pdf --outdir docs/presentation docs/presentation/ReSense_LCT2026.pptx

The team's personal data (names, photos, and optionally nicknames, place of study, city) are not in
the repository (team rule of 25.09): without ``--team`` the team slides show the four roles P1–P4 and
what each owns (README "Team"), with no ``<...>`` field; the build refuses a deck with one. The named
deck for the defence is built from a ``team.json`` kept outside git (``docs/presentation/private/`` is
git-ignored):

    python scripts/build_deck.py --template template.pptx --team docs/presentation/private/team.json \
      --out docs/presentation/private/ReSense_LCT2026.pptx

``team.json`` holds the keys of ``TEAM`` below; photo paths are relative to the JSON file. A named
build requires the captain, the captain's specialty and, for each of the four cards, a name and a
photo; ``nick``, ``study``, ``study_short``, ``city``, ``formed`` and ``team_photo`` are shown when
given. Placeholder text (``<...>``) is rejected.

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

# ---- every measured number on the slides and in the speaker notes; each is written here once and the
# slide texts, charts and notes read it through the helpers below. Sources: the current detector's
# regression gate BASELINE (keys named as there; identical to the sealed run f_seal and to the
# 27.09 baseline docs/evidence/results/regression_baseline_2026-09-27_quality.json wherever a comment
# below does not say otherwise), docs/evidence/cycle_2026-09-29/competitor_rules/gate_table.md, the
# cycle record docs/archive/QUALITY_CYCLE_2026-09-27.md (the held-out checks of the 27.09 detector),
# docs/archive/EXPERIMENTS_log_2026-09.md "Current results" (§0, §2d, §2e, §3, §9), docs/archive/P4_AUDIT.md,
# docs/ARCHITECTURE.md "Native kernels", "GPU: evaluated, not used" --------------------------------
# The current detector: the 27.09 seal + PR #27/#28 (frame 111, thin_far 4 -> 3) + the three
# false-alarm rules after other teams' case 5 solutions, on by default since 29.09 evening
# (tracking.explained_run, cluster.shell_min_top, tracking.ego_veto_min_speed), sealed at 1e2ed82
# (docs/evidence/detector_freeze_2026-09-29_competitor_rules.json)
BASELINE = "docs/evidence/cycle_2026-09-29/competitor_rules/gate.json"
N = {
    # the organizers' real recordings [real]: six recordings and the 20-minute ride (13.0 km)
    "frames_six": 2488, "frames_ride": 11271, "ride_km": 13,
    # doubleT_obstacle: the person crossing (STOP frames, frames inside the envelope), the first alarm's
    # delay after the person enters the envelope (first_alarm_frame against the label's first frame
    # inside, 8, at 10 Hz; 0 = on the first frame inside), the largest distance error; the object on the
    # rail after the person leaves (frame 75 on; BASELINE, 1 cm cache: 126 of 126, 125 on 27.09), and
    # v0.6.1's own hits on it before the object was clustered whole (history)
    "person": (61, 61), "person_delay_s": 0.0, "person_err_m": 0.23,
    "rail_object": (126, 126), "rail_object_v061": 2,
    # the whole recording: STOP frames of all frames, and the first STOP frame. From frame 8 to the end
    # with no gap, offline on the original recording and through the ROS node in Docker (CI run
    # 36547463949, cold and warm; docs/evidence/frame111_2026-09-29), and on the 1 cm cache (BASELINE
    # alarm_frames 193). The 27.09 detector gave 190 of 201 with a GO at frame 111 and CAUTION at 117 and
    # 197; tracking.stop_keep_low_s 0.3 (PR #27, tuned on this recording) closed it
    "obstacle_stop": (193, 201), "obstacle_first_frame": 8,
    # the person with the envelope from the rails alone (gauge.reference 0; quality-cycle screens of 27.09,
    # docs/organizers/answers.md §9): the gain to 61 is entirely the sensor-axis addition (the union, at
    # most 0.2 m wider within 60 m on straight track). The organizers measure the envelope from the rail
    # heads (their answer of 29.09); the union never narrows it
    "person_rails_only": 58,
    # false alarm events (ride / five empty recordings), in-sample: the rules and the track opinion's
    # negatives come from these recordings; the per-km figures are derived (/ ride_km). BASELINE (the
    # current detector) and, before the three rules of 29.09, the 27.09 baseline; STOP episodes on the
    # ride (BASELINE ride.stop_episodes; the independent judgement counts episodes)
    "ride_events": 26, "empty_events": 8, "ride_events_before": 32, "empty_events_before": 11,
    "ride_episodes": 28,
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
    # inside the envelope in the chart's order: gate key -> (chart name, first STOP m, STOP frames,
    # visible frames, held: a STOP on every frame from the first STOP on (pink) or not (violet)).
    "fake_frames": 1510,
    "set_o": {
        "big_above": ("ящик 2 × 2 м, верх габарита", 111.4, 56, 124, True),
        "big_center": ("ящик 2 × 2 м в центре", 98.0, 208, 213, True),
        "long_low_on_rails": ("доска поперёк рельсов", 87.2, 52, 86, True),
        "small_on_rail": ("куб 0,3 м на рельсе", 42.7, 23, 49, True),
        "small_center": ("куб 0,3 м в воздухе", 55.8, 32, 79, True),
        "small_edge_inside": ("куб 0,3 м у края", 35.0, 18, 83, True),
        "big_edge_inside": ("ящик 2 × 2 м у края", 18.3, 7, 125, False),
        "thin_hanging": ("висящий предмет 5 см", 30.1, 15, 42, True),
    },
    # STOP on the 2 x 2 m box outside the envelope (big_outside): frames 563-571, 126-142 m, of the
    # original recording, identical offline and through the node (the 28.09 re-judgement's set O runs of
    # the sealed detector, docs/evidence/judge_outputs_2026-09-28 offline/seto_offline and node_set_o,
    # counted per frame by P2): frames whose decision is STOP with a detection on the
    # box's inner edge. scripts/score_fake_objects.py credits 7 of them on those runs (in frames 569-570
    # the detection is 2-3 cm beyond its 1 m lateral tolerance), and 6 on the gate's quantised cache. In
    # frames 563-568 that box is the decision's nearest distance while the edge box at 30-40 m has no
    # STOP yet
    "fake_outside_false": 9, "fake_outside_scored": (7, 6), "fake_outside_m": (126, 142),
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
    # of 6 approaches: person, trolley, crate and cable from the gate run of 29.09 (BASELINE
    # set_F_straight, legacy placement; identical to 27.09); the 30 cm box on the rail head and the object across the rail
    # from round 3 (24.09, not in the gate); the anchored person: round 4, 5 pairs, 150 m in the same
    # pairs with the legacy placement [synthetic in real frames, EXPERIMENTS §2d, P4_AUDIT]
    "set_f": {
        "person_anchored": ("человек 1,7 м · от рельсов", 154), "person": ("человек 1,7 м", 151),
        "trolley": ("тележка", 151), "crate": ("ящик 1 м", 124), "cable": ("висящий кабель 3 см", 99),
        "rail_box": ("ящик 30 см на рельсе", 49), "across_rail": ("предмет поперёк рельса", 46),
    },
    # the 0.5 m box on the bed between the rails: approaches with a detection (BASELINE set_F_straight
    # box0.5 detected; 1 of 6 on 27.09, 2 since thin_far 4 -> 3 of 29.09)
    "bed_box_found": (2, 6),
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
    # sandbox (docs/evidence/judgement_2026-09-28). The three rules of 29.09 add +2.4 ms p95 on 360°
    # frames and +1.6 ms on 120° (CHANGELOG, latency_ab.json). The organizers' i7-9700E stand was not
    # available. "hw": the machine of the detector-alone timings below
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
    # `python3 -m pytest -q` passes 1 280 on 29.09 evening (CHANGELOG, the three rules' entry), besides the
    # web/demo checks; the deck test (web/demo/test_web.py) asks >= 667
    "tests": "1 280",
}


def num(x):
    """13759 -> '13 759', 0.23 -> '0,23' (runs_of glues the thousands with a no-break space)."""
    if isinstance(x, int):
        return f"{x:,}".replace(",", " ")
    return f"{x:g}".replace(".", ",")


def of(pair):
    return f"{pair[0]} из {pair[1]}"


def metres(x):
    """A distance on a slide: whole metres, half up (52.5 -> 53)."""
    return int(x + 0.5)


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
    objs = N["set_o"].values()
    return of((sum(1 for o in objs if o[2] > 0), len(objs)))


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


def obstacle_run():
    """'STOP на 193 из 201 кадра — с кадра 8 до конца, без пропусков': doubleT_obstacle as a whole"""
    return (f"STOP на {of(N['obstacle_stop'])} {plural(N['obstacle_stop'][1], 'кадра', 'кадров', 'кадров')} — "
            f"с кадра {N['obstacle_first_frame']} до конца, без пропусков")


def e2e():
    """'p95 от публикации кадра до решения через ROS в Docker: 81–82 мс при 360° (4 ядра) и 49–78 мс при 120°
    (4 vCPU), 28.09; три правила 29.09 — ещё ~2 мс'"""
    return (f"p95 от публикации кадра до решения через ROS в Docker: {N['e2e_360']} при 360° (ВМ, 4 ядра; "
            f"с холодного диска {N['e2e_360_cold']}) и {N['e2e_120']} при 120° (4 vCPU), замер 28.09; три "
            f"правила 29.09 добавляют ~{N['rules_ms']} мс")


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

# ---- the team (slides 7-10): the team is «Молоток», ReSense is the solution. Personal data (names,
# photos; nicknames, place of study, city when given) are only in the named build from --team (not in
# git; team rule of 25.09); without it the team slides show the four roles P1-P4 as README "Team"
# states them, so the deck in the repository has no unfilled fields. The pitch is the captain's since
# 29.09 (P2 made the deck and the video and declined the pitch) -----------------------------------
TEAM_NAME = "Молоток"
TEAM = {
    "captain": None, "captain_specialty": None, "members": "4 человека",
    "formed": None, "study": None, "study_short": None, "city": None, "team_photo": None,
    "cards": [{"name": None, "nick": None, "photo": None} for _ in range(4)],
}
# the public cards (README "Team"): (name line, role, what the member owns)
PUBLIC_CARDS = [
    ("P1 · капитан", "Системный аналитик, ROS 2", "требования, архитектура, узел ROS 2 и Docker, питч, сдача"),
    ("P2 · фронтенд", "Разработчик ПО (Python / JS)", "RViz, Foxglove, веб-дашборд, разметка, презентация, видео"),
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
                etree.SubElement(sf, qa("srgbClr")).set("val", col)
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
    if not path.lower().endswith(".png") or os.path.getsize(path) < 400_000:
        return path
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


def textbox(slide, left, top, width, height, paras, size=12, color="FFFFFF", bold=False, anchor=None):
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
    fill(d, ["ROS 2-модуль: по потоку 3D-лидара строит модель «нормального тоннеля» — "
             "полотно, рельсы, ось пути с кривизной по стенам, — проверяет габарит поезда 2,1 × 3,0 м и "
             "отвечает GO / CAUTION / STOP / FAULT с расстоянием до препятствия. Решает геометрия; обученное "
             f"«мнение» о треке лишь откладывает сомнительный STOP — не больше {N['opinion_budget']} "
             f"обработанных кадров (~{num(N['opinion_budget'] / 10)} с при 10 Гц). Без GPU, в Docker."], size=12)
    u = shape(sl, 8)
    u.height = Emu(1350000)
    fill(u, ["Описываем среду, а не объекты: крепление лидара и ось пути калибруются по рельсам в каждом "
             "кадре, кривизна — по стенам и рядам колонн, поэтому коридор осмыслен и там, где рельсов уже "
             "не видно. Публикуем оценку дальности контроля; возможны пропуски объектов. Настройка и оценка — на "
             "препятствиях, вставленных трассировкой лучей в реальные кадры."], size=12)
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
        # the name under the photo, surname over first name, above the P1-P4 line (as P2 laid it out)
        top = frame.top + frame.height + 50000
        tb = textbox(sl, Emu(label.left), Emu(top), Emu(frame.width + frame.left - label.left),
                     Emu(max(label.top - top - 10000, 300000)), who["name"].split(" ", 1),
                     size=14, color="4B0E73", bold=True)
        tf = tb.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        for p in tf.paragraphs:
            p.line_spacing = 0.9
        if team_photo(who.get("photo")):
            photo_into_frame(sl, photo, team_photo(who["photo"]))


def s10_history(sl):
    fill(shape(sl, 7), ["ИСТОРИЯ КОМАНДЫ"])
    fill(shape(sl, 37), ["Четыре инженерных направления — ROS 2 и интеграция, визуализация, компьютерное зрение, "
                         "данные и тесты — собраны вокруг задачи контроля габарита тоннеля по 3D-лидару."], size=12)
    fill(shape(sl, 43), ["В записях почти нет реальных препятствий, а станции и стрелки похожи на объекты. "
                         "Поэтому система оценивает геометрию тоннеля и ищет препятствия в габарите; "
                         "пропуски возможны и в пределах расчётной дальности контроля."],
         size=12)
    fill(shape(sl, 40), ["Препятствий в записях почти нет — «ставили» людей и ящики в реальные кадры трассировкой "
                         "лучей лидара; эти примеры оцениваются отдельно от реальных записей. Станции и стрелки давали "
                         "ложные остановки — помогли ось по стенам, зона доверия, подтверждение 0,5 с и три правила из "
                         "открытых решений других команд. Записи разные (два топика, 120° и 360°, наклон крепления 3°) — "
                         "узел сам находит вход и калибруется по рельсам."],
         size=12)


def s11_short(sl):
    fill(shape(sl, 3), [
        "ROS 2 Humble-узел на Python (numpy / scipy / scikit-learn) и необязательные ядра на C++",
        "PointCloud2 → модель пути → габарит 2,1 × 3,0 м → кластеры → решение; оба набора топик, "
        "автокалибровка крепления",
        "Результат: GO / CAUTION / STOP / FAULT, расстояние и /resense/status; подтверждение 0,5 с, "
        "«мнение» о сомнительных треках",
        f"Кадр → решение через ROS, p95: {N['e2e_360']} (360°) и {N['e2e_120']} (120°) на 4-ядерной "
        f"машине, 28.09; правила 29.09 — ещё ~{N['rules_ms']} мс; ядра на C++ сокращают время детектора на "
        f"{native_cut()}",
        f"{num(frames_total())} реальных кадров; человек — {of_frames(N['person'])}, STOP без пропусков; "
        f"{per_km()} ложных события на км в выборке (правила подбирались на этих записях)",
        "Без GPU: CPU-образ запускается без дополнительного ПО",
    ], size=12, space_before=4)
    fill(shape(sl, 7), [
        "**Применение:** контроль габарита на беспилотном и хозяйственном поезде",
        "**Дальше:** скорость от одометрии, работа с мелкими объектами вдали, обучение на реальных препятствиях",
        "**Внедрение:** docker run → ros2 bag play; адаптер торможения и его проверки — отдельный этап",
    ], size=12, space_before=6)


def s_problem(sl):          # template slide 24: problem / alternatives / solution
    title_chip(sl, 2, shape(sl, 9), "ПРОБЛЕМА И ПОДХОД")
    cols = {
        26: ("Проблема", "Поезд без машиниста должен видеть путь: 100 м — хорошо, 200 — очень хорошо, 300 — "
                         "отлично. При 80 км/ч и замедлении 1–1,3 м/с²: 190–250 м без задержек. Тоннель почти всегда пуст: "
                         "классов объектов для обучения нет."),
        31: ("Альтернативы", "Обученный 3D-детектор требует размеченных препятствий; качество таких "
                             "моделей на наших тоннелях не измерялось. Сравнение с картой требует "
                             "локализации и повторного проезда."),
        32: ("Наше решение", "Описать нормальный тоннель и искать препятствия в габарите поезда "
                             "2,1 × 3,0 м. Ось строится по рельсам, полотну и стенам без карты; "
                             "обученное «мнение» может отложить сомнительный STOP. Есть пропуски и ложные тревоги."),
    }
    for idx, (head, text) in cols.items():
        fill(placeholder(sl, idx), [(head, {"bold": True, "size": 16, "color": PINK}),
                                    (text, {"space_before": 8})], size=13, bullet=False)


def s_data(sl):             # template slide 12: text left, picture right
    fill(placeholder(sl, 0), ["ДАННЫЕ И СЕНСОР"])
    fill(placeholder(sl, 1), [
        f"**{num(frames_total())} кадров** — 6 записей ({num(N['frames_six'])}) и 20-минутная поездка "
        f"({num(N['frames_ride'])} кадр, {N['ride_km']} км, "
        "7 остановок, кривые до R ≈ 350 м)",
        "**Hesai Pandar128**, 10 Гц, ~190 тыс. точек в кадре: стены видны на 150–200 м, полотно — до ~100 м",
        "**~210 м — предел отражений в тоннеле:** каждая запись обрывается на 209–210 м, дальше нет ни "
        "одной точки (паспорт: 200 м при 10 % отражения)",
        "Объект 0,5 м даёт ~7 точек на 100 м и 1–2 точки на 200 м",
        "Реальные препятствия: человек и предмет на рельсе в записи doubleT_obstacle; всё остальное — "
        "синтетика в реальных кадрах, каждое число помечено",
    ], size=13, space_before=8)
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
        (26, 27): ("Автокалибровка", "вертикальная ось вращения; ориентация и наклон — по рельсам и полотну"),
        (32, 33): ("Модель пути", "полотно, головки рельсов, ось; кривизна по стенам и колоннам до 150–200 м"),
        (28, 29): ("Габарит", "коридор 2,1 × 3,0 м вдоль оси и ступень низких объектов на рельсах"),
        (34, 35): ("Кластеры", "радиус растёт с дальностью; фильтры инфраструктуры и обделки; дальнее правило"),
        (30, 31): ("Решение", "подтверждение 0,5 с, «мнение» о треке, запрет эго-движения → GO / CAUTION / STOP / "
                              "FAULT и дальность контроля"),
    }
    for (ti, di), (t, d) in steps.items():
        fill(placeholder(sl, ti), [t], size=15, bullet=False)
        fill(placeholder(sl, di), [d], size=11, bullet=False)


def s_hero(sl):             # template slide 13: big white card
    fill(placeholder(sl, 0), ["ГЛАВНЫЙ КАДР"])
    remove(placeholder(sl, 1))
    card = shape(sl, 4)
    m = 170000
    h = card.height - 2 * m
    w = int(h * 16 / 9)
    picture_cover(sl, os.path.join(ROOT, IMG["hero_person"]), Emu(card.left + m), Emu(card.top + m), Emu(w), Emu(h))
    x = card.left + m + w + 200000
    textbox(sl, Emu(x), Emu(card.top + m), Emu(card.left + card.width - x - m), Emu(h), [
        ("Реальная запись организаторов", {"bold": True, "size": 14, "color": DEEP}),
        ("Человек переходит путь на 55–57 м", {"space_before": 10}),
        (f"Найден в **{of(N['person'])}** {of_frames(N['person']).split()[-1]} внутри габарита "
         f"({person_rails()})", {"space_before": 8}),
        (f"Тревога {person_alarm()} после входа в габарит" if N["person_delay_s"] > 0
         else f"Тревога {person_alarm()}", {"space_before": 8}),
        (f"Ошибка дальности ≤ {num(N['person_err_m'])} м", {"space_before": 8}),
        (f"Вся запись: STOP на **{of(N['obstacle_stop'])}** кадра — с кадра {N['obstacle_first_frame']} до "
         f"конца без пропусков, офлайн и через узел ROS; предмет на рельсе — {of(N['rail_object'])}",
         {"space_before": 8}),
    ], size=12, color="1C1D22", anchor="ctr")
    notes(sl, "Вот тоннель — двухпутный, поезд стоит, лидар на кабине. Вот облако одного кадра — сотни тысяч "
              "точек за 0,1 с. Зелёным — габарит поезда, который алгоритм сам протянул вдоль оси пути по рельсам "
              "и стенам. Жёлтым — всё, что попало в коридор. И вот человек, который переходит путь: красная "
              "рамка, 55,8 метра, решение STOP. Справа — его точки крупно. Когда человек уходит, на рельсе "
              "остаётся предмет 45 × 60 × 30 см — алгоритм держит и его: STOP с кадра "
              f"{N['obstacle_first_frame']} до конца записи, {of(N['obstacle_stop'])} кадра, офлайн и через узел "
              "ROS в Docker одинаково. До 29.09 в кадре 111 был один GO: верх предмета на 4–7 мм ниже порога "
              "высоты. Исправили правилом удержания уже подтверждённого низкого STOP на 0,3 с — подобрано на "
              "этой же записи, и мы это говорим.")


def s_demo(sl):             # template slide 27: two browser frames
    title_chip(sl, 2, shape(sl, 55), "ДЕМОНСТРАЦИЯ")
    picture_in_placeholder(placeholder(sl, 14), os.path.join(ROOT, IMG["dashboard"]))
    picture_in_placeholder(placeholder(sl, 18), os.path.join(ROOT, IMG["chain"]))
    fill(shape(sl, 10), ["localhost:8080"])
    fill(shape(sl, 33), ["docker run resense"])
    fill(placeholder(sl, 15), ["Веб-дашборд «Контроль свободного габарита»: вид из кабины по статусу узла из "
                               "Docker-прогона на doubleT_obstacle — STOP 56,1 м, оценка дальности контроля 56 м; "
                               "живой узел — через rosbridge"], size=12)
    fill(placeholder(sl, 16), ["Цепочка жюри в Docker: узел с RViz, bag play от обычного пользователя из "
                               "другого контейнера, /resense/decision — STOP 56 м (видео 69 с)"], size=12)
    textbox(sl, Emu(1210643), Emu(5640000), Emu(9770000), Emu(640000),
            [("docker load → docker run → ros2 bag play → /resense/decision", {"align": "ctr"}),
             ("или одной командой: scripts/play_bag.sh путь_к_бэгу [--archive resense-image-версия.tar.gz]",
              {"align": "ctr", "size": 12, "bold": False, "space_before": 4})], size=16,
            color=DEEP, bold=True, anchor="ctr")


def s_results(sl):          # template slide 20: left card + five rows
    title_chip(sl, 2, shape(sl, 14), "РЕЗУЛЬТАТЫ")
    fill(placeholder(sl, 14), [
        (num(frames_total()), {"size": 36, "bold": True, "color": PINK}),
        ("реальных кадров прогнаны целиком", {"size": 13}),
        (of(N["person"]), {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        (f"кадров с человеком на пути — тревога с первого кадра ({person_rails()}: до 0,2 м по оси лидара "
         "ближе 60 м мы добавляем к габариту)", {"size": 13}),
        (f"{per_km()} на км", {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        (f"ложных событий в поездке ({N['ride_events']} за {N['ride_km']} км), в выборке — на ней же "
         f"подбирались правила; вне выборки мерили только «мнение» (детектор 27.09): {unseen_km()} на км",
         {"size": 13}),
    ], bullet=False, color="1C1D22")
    rows = [
        f"**Реальная запись:** человек — {of_frames(N['person'])}, ошибка ≤ {num(N['person_err_m'])} м; "
        f"{obstacle_run()}; предмет на рельсе — {of(N['rail_object'])}",
        f"**Ложные остановки** (реальные, в выборке): поездка {N['ride_km']} км — {events(N['ride_events'])}, "
        f"{N['ride_episodes']} эпизодов STOP; пять пустых записей — {events(N['empty_events'])}; до трёх правил "
        f"29.09 из решений других команд — {N['ride_events_before']} и {N['empty_events_before']}",
        f"**Объекты организаторов** [их синтетика]: STOP у {set_o_stopped()} в габарите; ящик 2 × 2 м — с "
        f"{set_o_first('big_center')} м, доска — с {set_o_first('long_low_on_rails')} м, кубы 0,3 м — с "
        f"{cubes()} м, у края — с {edge_from()} м",
        f"**Человек на подходе** [наша синтетика в реальной поездке]: первое подтверждение — "
        f"{set_f('person')} м, медиана 6 подходов; ящик 1 м — {set_f('crate')} м, висящий кабель 3 см — "
        f"{set_f('cable')} м; дальше ~210 м отражений нет",
        f"**Задержка** (p95, публикация кадра → решение, ROS в Docker): 360° — {N['e2e_360']}, 120° — "
        f"{N['e2e_120']} на 4-ядерной машине (28.09); правила 29.09 — ещё ~{N['rules_ms']} мс; без GPU; "
        "стенд i7-9700E не измерен",
    ]
    for idx, text in zip(range(15, 20), rows):
        fill(placeholder(sl, idx), [text], size=12, bullet=False)


def s_range(sl):            # template slide 22: horizontal bar chart + four notes
    title_chip(sl, 2, shape(sl, 15), "ДАЛЬНОСТЬ")
    gf = shape(sl, 12)
    cd = CategoryChartData()
    data = list(reversed(list(N["set_f"].values())))    # a bar chart draws the first category at the bottom
    cd.categories = [c for c, _ in data]
    cd.add_series("первое подтверждение, м", [v for _, v in data])
    ch = gf.chart
    ch.replace_data(cd)
    all_category_labels(ch)
    plot = ch.plots[0]
    bar_labels(plot, [None] * len(data), size=12)
    cols = [PINK, "FC3777", "310F53", DEEP, VIOLET, LIGHT, "FC3777"][:len(data)][::-1]
    for i, pt in enumerate(plot.series[0].points):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = RGBColor.from_string(cols[i % len(cols)])
    ch.value_axis.maximum_scale = 200
    ch.value_axis.minimum_scale = 0
    ch.value_axis.major_unit = 50
    ch.category_axis.tick_labels.font.size = Pt(11)
    ch.value_axis.tick_labels.font.size = Pt(10)
    pairs = [
        (21, 18, "~210 м — предел отражений в тоннеле",
         f"дальше 210 м во всех {num(frames_total())} кадрах нет ни одной точки"),
        (22, 23, "Со скоростью поезда", f"накопление 5 кадров: человек {N['speed_person']} м (24.09); своя "
                                        f"скорость по лидару (ошибка {N['speed_err']}) раньше STOP не даёт"),
        (24, 25, "Устойчиво", f"человек в ≥ 90 % кадров каждой полосы 10 м — со {N['band_person']} м (24.09)"),
        (26, 27, "В кривых", f"{N['curves'][0]} подходов, с {N['curves'][1]} м — предел видимости за стеной "
                             "(R ≈ 350 м; 24.09)"),
    ]
    for ti, di, t, d in pairs:
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=12, bullet=False)
    textbox(sl, Emu(346075), Emu(5820000), Emu(5800000), Emu(520000),
            [f"первое подтверждение на прямой, медиана 6 подходов (гейт 29.09, как и 27.09; ящик 30 см и "
             f"предмет поперёк рельса — 24.09); «от рельсов» — объект поставлен по ближним "
             f"рельсам, а не по дальней оси детектора (5 пар, прежняя постановка — {N['anchored_legacy']} м); "
             "поезд 17–21 м/с без датчика скорости · синтетика в реальных кадрах поездки"],
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
    gf.height = Emu(gf.height - 300000)
    textbox(sl, Emu(346075), Emu(gf.top + gf.height + 40000), Emu(5749925), Emu(560000),
            [f"первый STOP, м; сиреневым — без устойчивого STOP · cloud_with_fake_obj: 10 объектов, "
             f"{num(N['fake_frames'])} кадров, поезд едет к ним 1,4–20 м/с, скорость узлу не дана · синтетика "
             "организаторов"],
            size=10, color="E6E1F5")
    top = set_o("big_above")
    cards = [
        (21, 18, f"STOP у {set_o_stopped()}, у края — с {edge_first()} м",
         f"ящик 2 × 2 м в центре — с {set_o_first('big_center')} м, с первого появления; доска поперёк рельсов — с "
         f"{set_o_first('long_low_on_rails')} м; кубы 0,3 м — с {cubes()} м. На новых местах ({N['novel_cases'][1]} "
         f"{plural(N['novel_cases'][1], 'случай', 'случая', 'случаев')}, проверка заявлена заранее, детектор 27.09) — "
         f"{novel()}; на том же фоне без объекта — {N['novel_controls']}"),
        (22, 23, "Мелкое вдали — поздно",
         f"на 60–115 м от куба 0,3 м 2–4 точки в кадре: дальше {N['far_weak'][0]} м трек начинаем и с "
         f"{N['far_weak'][1]}, но STOP — только если объект приближается, иначе CAUTION; ящик у верха габарита — STOP в {of(top[2:4])} кадров — непрерывно с "
         f"{metres(top[1])} м, дальше CAUTION или ничего"),
        (24, 25, "Ограничения — говорим честно",
         f"габарит — от головки рельсов (ответ организаторов 29.09); ближе {N['axis_near_m']} м на прямой мы "
         f"расширяем его до {num(N['axis_shift_m'])} м по оси лидара, но нигде не сужаем. Ложный STOP: "
         f"{N['fake_outside_false']} кадров у ящика снаружи ({N['fake_outside_m'][0]}–{N['fake_outside_m'][1]} м), "
         f"{N['fake_background']} вне объектов; синтетика расставлена приблизительно — организаторы это учтут"),
    ]
    for ti, di, t, d in cards:
        fill(placeholder(sl, ti), [t], size=15, bold_all=True)
        fill(placeholder(sl, di), [d], size=11, bullet=False)


def s_reliability(sl):      # template slide 16: four cards
    title_chip(sl, 10, shape(sl, 14), "НАДЁЖНОСТЬ")
    cards = [
        (49, 37, 38, "Калибровка", "8 проверенных ориентаций вокруг вертикальной оси; крен и тангаж "
                                     "по рельсам и полотну; не любое крепление"),
        (50, 39, 40, "Свежесть данных", "нет актуального статуса → FAULT или удержание STOP; "
                                      "потребитель проверяет /resense/status своим таймером"),
        (51, 41, 42, "Любой вход", "оба набора топик / frame_id, поиск топика, перезапуск на новой записи"),
        (52, 43, 44, "Воспроизводимо", f"{N['tests']} тестов на путях numpy и C++ (выход совпадает бит в бит); "
                                       "CI собирает образ и проигрывает бэги через узел; цепочка организаторов "
                                       "прогнана в Docker на реальных записях"),
    ]
    for k, (ni, ti, di, t, d) in enumerate(cards):
        fill(placeholder(sl, ni), [f"0{k + 1}"])
        fill(placeholder(sl, ti), [t], size=15)
        fill(placeholder(sl, di), [d], size=12)


def s_hard(sl):             # template slide 15: five lined rows
    fill(placeholder(sl, 0), ["СЛОЖНЫЕ СЛУЧАИ"])
    rows = [
        "**Предметы на полотне.** Наивный порог — 1 482 ложных события за 20 мин; после настройки остаётся "
        f"слепое пятно: ящик 0,5 м найден в {of(N['bed_box_found'])} подходов",
        f"**Предмет на рельсе.** Кластеризуем целиком: {N['rail_object_v061']} → {of(N['rail_object'])} кадров; "
        "один GO в кадре 111 закрыт 29.09 удержанием низкого STOP на 0,3 с — подобрано на этой же записи",
        "**Станции и стрелки.** Ложные STOP у платформ; три правила 29.09 (эго-движение, обделка, «чистая "
        f"серия») — {N['ride_events_before']} → {N['ride_events']} событий в поездке; «мнение» откладывает "
        f"сомнительный STOP не более чем на {N['opinion_budget']} обработанных кадров (~1 с при 10 Гц)",
        "**Мелкие объекты вдали.** На 60–115 м всего 2–4 точки от куба; STOP для кубов 0,3 м — "
        f"только с {cubes()} м",
        f"**У края габарита.** STOP лишь с {edge_from()} м; висящий предмет 5 см — с "
        f"{set_o_first('thin_hanging')} м (синтетика организаторов)",
    ]
    for idx, text in zip(range(15, 20), rows):
        ph = placeholder(sl, idx)
        ph.width = Emu(11200000)
        fill(ph, [text], size=13, bullet=False)


def s_next(sl):             # template slide 17: three cards
    fill(placeholder(sl, 0), ["ИТОГИ И ПЛАНЫ"])
    cards = [
        (49, 37, 38, "Что получилось", f"ROS 2-модуль в Docker; все {num(frames_total())} реальных кадров: человек и "
                                       f"предмет на рельсе — STOP без пропусков, {per_km()} ложных события на км (на данных, "
                                       f"где подбирались правила); ящик организаторов — с {set_o_first('big_center')} м; "
                                       f"{N['tests']} тестов и CI"),
        (50, 39, 40, "Что дальше", "мелкие объекты раньше: короткие сигнатуры инфраструктуры, опора высоты "
                                   "по своду тоннеля; скорость от одометрии (своя по лидару — опция); "
                                   "«мнение» о треке — переобучить на реальных препятствиях"),
        (51, 41, 42, "Внедрение", "docker load → run → ros2 bag play или одной командой: scripts/play_bag.sh "
                                  "путь_к_бэгу [--archive resense-image-версия.tar.gz] — образ, узел, запись и "
                                  "каждая смена решения с дистанцией; один файл параметров; стандартные "
                                   "сообщения ROS 2; адаптер к торможению ещё нужно разработать и проверить"),
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
        "сократились, но остались; три правила против них мы взяли из открытых решений других команд "
        "кейса 5 и проверили на всех записях. Проверка на новых данных нужна.",
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
        f"было бы {N['person_rails_only']}. Вся запись — {obstacle_run()}, офлайн и через узел ROS в Docker; "
        f"предмет на рельсе — {of(N['rail_object'])}. Одиночный GO в кадре 111 закрыт 29.09 правилом, "
        "подобранным на этой же записи. "
        f"Задержка — {e2e()}. "
        f"Ложных событий в 20-минутной поездке — {per_km()} на км ({N['ride_events']} за {N['ride_km']} км, "
        f"было {N['ride_events_before']} до трёх правил 29.09), но это на тех же данных, где мы подбирали "
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
        f"Ложный STOP у ящика снаружи габарита — {N['fake_outside_false']} кадров подряд на "
        f"{N['fake_outside_m'][0]}–{N['fake_outside_m'][1]} м на исходной записи (детектор 27.09; на кэше гейта — "
        f"{N['fake_outside_scored'][1]}, и 29.09 так же): обнаружение на его внутреннем крае.",
    16: "Калибруем поддерживаемое крепление и находим вход. При потере свежести — FAULT либо "
        "удержание STOP с последней дистанцией; потребителю нужен свой таймер статуса. "
        "Ложный STOP на пустой сцене больше не зависит от того, как узел получал кадры: в записанных историях "
        f"узла — {N['history_captured'][1]} (было {N['history_captured'][0]}), в стресс-тесте с пропусками и "
        f"догонялками — {events(N['history_stress'][1])} (было {N['history_stress'][0]}; 28.09).",
    15: "Что не сработало и почему: полотно полно железа, станции — главный источник ложных остановок, "
        "мелкие объекты организаторов видим поздно, тонкие — только вблизи. Три правила 29.09 взяты из "
        "открытых решений других команд (TunnelGuard, Tactical-Inventor) и проверены полным гейтом: ни одна "
        "метрика не хуже; независимую проверку безопасности этих правил ещё не делали. «Мнение» о треке обучено на "
        "синтетике: непохожий реальный объект — мусор, лежащий человек — оно может задержать, но "
        f"{opinion_bounds()}; предел {N['opinion_near_m']} м действует и по предсказанной дистанции, пока трек "
        "не виден; STOP оно никогда не отменяет. "
        "Порог — половина наибольшего, который не задерживает ни одного отложенного синтетического объекта; "
        f"без этого запаса на детекторе 27.09 было бы {N['ride_zero_margin'][0]} событий в поездке и "
        f"{N['ride_zero_margin'][1]} на невиданных кусках — запас оставили ради безопасности.",
    17: "Итог: работающий модуль, честные цифры, понятные следующие шаги — мелкие объекты раньше, скорость "
        "от одометрии, независимая проверка трёх новых правил и замер на стенде организаторов.",
}

# template slide number -> filler, in the order of the deck
PLAN = [(7, None), (8, s08_team), (9, s09_cards), (10, s10_history), (11, s11_short),
        (24, s_problem), (12, s_data), (25, s_algorithm), (13, s_hero), (27, s_demo), (20, s_results),
        (22, s_range), (21, s_fake), (16, s_reliability), (15, s_hard), (17, s_next)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--template", required=True, help="the organizers' template exported as .pptx")
    ap.add_argument("--out", required=True)
    ap.add_argument("--team", default=None, help="JSON with the team's personal data and photos (kept out of git; "
                                                 "keys as TEAM, photo paths relative to the file)")
    a = ap.parse_args()
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
    # no unfilled "<...>" field on any slide, public or private (the judges read them as unfinished)
    placeholders = []
    for slide_number, slide in enumerate(prs.slides, 1):
        for sh in _walk(slide.shapes):
            if sh.has_text_frame and re.search(r"<[^<>\n]+>", sh.text):
                placeholders.append(slide_number)
    if placeholders:
        raise ValueError(f"deck still has placeholders on slides {sorted(set(placeholders))}")
    prs.save(a.out)
    os.remove(logo_path)
    print(f"{a.out}: {len(keep)} slides")


if __name__ == "__main__":
    main()
