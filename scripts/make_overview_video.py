#!/usr/bin/env python3
"""Build the 3-minute overview video ``docs/video/resense_overview.mp4`` (+ ``.ru.srt``).

The cut follows the organizers' pitch arc (ТЗ §8.8: проблема → идея → алгоритм → демонстрация →
результаты → что получилось) and ends on their sentence «Вот поезд … А вот препятствие, которое наш
алгоритм увидел за X метров»: the real person at ~56 m and the organizers' 2 × 2 m box at its first
STOP. It is made only from the repository's own material: the clips in ``docs/video/``, the renders
in ``docs/img/``, and boards drawn here (``BOARDS``). Nothing is fetched from the network.
Shot list, narration and how to record a human voice: docs/video/README.md.

On screen: the picture on the left; on the right the block's name and cards with its key numbers
(marked **реальные данные**, **наша синтетика** or **синтетика организаторов**), with the source of
the picture under them; the narration as burned-in Russian subtitles (at most two lines), also
written to ``docs/video/resense_overview.ru.srt`` with the same timings.

Every number that the team regression gate measures is in ONE place, ``GATE`` below (one line per
number, with the baseline field it comes from); ``FIXED`` holds the rest. tests/test_overview_video.py
compares ``GATE`` with the newest gate baseline, so a new baseline fails there until the block is
updated and the video re-rendered.

Voice-over (optional): ``--voice`` takes a Piper TTS model (offline neural speech synthesis) and
mixes a narration of the subtitles (``spoken`` texts: numbers in words); without it the MP4 is silent.

    python scripts/make_overview_video.py --voice ru_RU-ruslan-medium.onnx   # 1920x1080 + voice
    python scripts/make_overview_video.py                     # silent, 1920x1080 -> docs/video/
    python scripts/make_overview_video.py --check             # validate the table and exit
    python scripts/make_overview_video.py --frames 3,60,100 --frames-dir /tmp/f   # PNGs only
    python scripts/make_overview_video.py --size 1280x720 --out /tmp/o.mp4 --srt /tmp/o.srt
    python scripts/make_overview_video.py --span 93,111 --out /tmp/part.mp4 --srt /tmp/part.srt

Everything that decides the cut (sources and in-points, timings, card texts, subtitles) is the
``BLOCKS`` table plus ``OPENING`` / ``FINAL`` / ``BOARDS``; change it there and re-run. Needs Pillow,
numpy and an ffmpeg with libx264 (``--ffmpeg``, else the binary of ``imageio-ffmpeg``, else ``ffmpeg``
on PATH); PyMuPDF only for ``deck:N`` shots; ``piper-tts`` and a voice only for ``--voice``:

    pip install Pillow numpy imageio-ffmpeg piper-tts
    python -m piper.download_voices ru_RU-ruslan-medium       # from huggingface.co/rhasspy/piper-voices

Not part of the runtime image. The fonts are the dashboard's Moscow Sans (web/assets/fonts/) and
DejaVu Sans Mono for the terminal board.
"""
from __future__ import annotations

import argparse
import bisect
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DOCS = os.path.join(ROOT, "docs")
DECK_PDF = "presentation/ReSense_LCT2026.pdf"          # "deck:N" below = page N of this PDF
OUT_MP4 = "docs/video/resense_overview.mp4"
OUT_SRT = "docs/video/resense_overview.ru.srt"
DURATION = 180.0                                        # 3:00, the organizers' "short video"
FPS = 25
XFADE = 0.4                                             # cross-fade between shots, s
STILL_HZ = 10                                           # a zooming still changes this often (as the clips)
CRF = 23                                                # x264 quality (shots with ``bits`` scale it)
REPO_LINE = "github.com/pmixay/ReSense · исходный код"

REAL, OURS, ORG = "real", "ours", "org"                 # how a number was measured (the script's marks)
DEMO = "демо-данные интерфейса"                         # badge on the web-UI captures of the built-in demo
TAGS = {
    REAL: ("реальные данные", "#E2F3E8", "#07703A"),
    OURS: ("наша синтетика", "#FFF0D0", "#8A5200"),
    ORG: ("синтетика организаторов", "#EFE3FA", "#5A2787"),
}


def shot(t0, t1, src, at=0.0, zoom=(1.0, 1.0), focus=(0.5, 0.5), note="", badge=None, bits=None):
    """A picture on the left from ``t0`` to ``t1`` (s): a clip from its second ``at``, a still
    (``zoom`` from/to about ``focus``, fractions of the picture), ``board:NAME`` (drawn here from
    ``BOARDS``) or ``deck:N`` (a page of the deck PDF). ``note`` is the
    source line under the cards (paths relative to docs/); ``badge`` a label on the picture;
    ``bits`` an x264 bitrate factor for the shot (zone ``b=``; < 1 = coarser): point clouds are noise
    to the encoder and the cab clips are CRF 31 already, so re-encoding them finer only costs
    megabytes."""
    return {"t0": t0, "t1": t1, "src": src, "at": at, "zoom": zoom, "focus": focus, "note": note,
            "badge": badge, "bits": bits}


def num(t, big, label, tag=None):
    """A card from ``t`` to the end of its block: a big number and what it is."""
    return {"t": t, "kind": "num", "big": big, "label": label, "tag": tag}


def text(t, head, tag=None):
    """A card from ``t`` to the end of its block: one statement."""
    return {"t": t, "kind": "text", "head": head, "tag": tag}


def steps(t, items, active):
    """A card listing ``items``; ``active`` = [(from_time, index of the highlighted item), ...]."""
    return {"t": t, "kind": "steps", "items": items, "active": active, "tag": None}


# ---- gate-dependent numbers: the ONE place to update ------------------------------------------
# Every number below comes from ONE team regression gate baseline (the 1 cm frame cache, all
# organizers' recordings). PROVISIONAL: run r_1e2ed82 = docs/evidence/results/
# regression_baseline_2026-09-29_competitor_rules.json (detector 1e2ed82, 29.09 evening, with the
# shell rule still ON). For the final detector (shell rule OFF since a5455b3) replace each value by
# the baseline field named on its line, set "run", re-render (mp4 + srt) and run
# tests/test_overview_video.py, which compares this block with the newest baseline.
GATE = {
    "run": "r_1e2ed82",           # the gate run the numbers come from (shown in the source lines)
    "ride_events": 26,            # ride.alarm_events            (new_data: 13.0 km, 11 271 frames)
    "ride_stop_episodes": 28,     # ride.stop_episodes
    "empty_events": 8,            # five_empty.alarm_events      (five empty recordings, 2 287 frames)
    "empty_stop_episodes": 12,    # five_empty.stop_episodes
    "o_inside_stop": 8,           # set_O.inside_objects_with_stop
    "o_inside": 8,                # set_O.inside_objects
    "o_outside_false": 6,         # set_O.outside_false_stop_frames
    "o_big_center_m": 98,         # set_O.objects.big_center.first_stop_m          (98.0, rounded)
    "o_big_above_m": 111,         # set_O.objects.big_above.first_stop_m           (111.4)
    "o_long_low_m": 87,           # set_O.objects.long_low_on_rails.first_stop_m   (87.2)
    "o_small_center_m": 56,       # set_O.objects.small_center.first_stop_m        (55.8)
    "o_small_on_rail_m": 43,      # set_O.objects.small_on_rail.first_stop_m       (42.7)
    "o_small_edge_m": 35,         # set_O.objects.small_edge_inside.first_stop_m   (35.0)
    "o_thin_hanging_m": 30,       # set_O.objects.thin_hanging.first_stop_m        (30.1)
    "o_big_edge_m": 18,           # set_O.objects.big_edge_inside.first_stop_m     (18.3)
    "f_person_m": 151,            # set_F_straight.kinds.person.first_detection_median_m  (151.0)
    "f_trolley_m": 151,           # set_F_straight.kinds.trolley.first_detection_median_m (151.4)
    "f_box1_m": 124,              # set_F_straight.kinds["box1.0"].first_detection_median_m (123.9)
    "f_cable_m": 99,              # set_F_straight.kinds.cable.first_detection_median_m   (98.9)
    "f_box05_m": 64,              # set_F_straight.kinds["box0.5"].first_detection_median_m (64.4)
    "dt_stop_frames": 193,        # recordings.doubleT_obstacle.alarm_frames
    "dt_first_stop_frame": 8,     # recordings.doubleT_obstacle.first_alarm_frame
    "dt_near_m": 55.5,            # recordings.doubleT_obstacle.alarm_dist[0]
    "dt_far_m": 56.6,             # recordings.doubleT_obstacle.alarm_dist[1]
    "dt_person": 61,              # recordings.doubleT_obstacle.labelled.per_label.person_crossing.hits
    "dt_rail": 126,               # ...labelled.per_label.object_on_rail_from_frame_75.hits
}
# Fixed facts (not re-measured by the gate): sizes of the data, history, the latency judgement.
FIXED = {
    "ride_km": 13,                # new_data, 13.0 km (docs/DATASET.md)
    "dt_frames": 201,             # doubleT_obstacle frames (= recordings.doubleT_obstacle.frames)
    "dt_person_frames": 61,       # labelled frames with the person (labels/doubleT_obstacle.json)
    "dt_rail_frames": 126,        # labelled frames with the object on the rail from frame 75
    "real_frames": 13759,         # 11 271 ride + 2 287 five empty + 201 doubleT_obstacle
    "ride_events_before": 32,     # the sealed 27.09 detector (f_base 3eeb106), gate_table.md 29.09
    "lat_p95": "81–82",           # ms, 360°, ROS in Docker, 4-core VM: independent judgement 28.09,
    "lat_p95_120": "49–78",       #   previous detector 464f5bc (docs/evidence/judgement_2026-09-28)
    "rules_ms": 2,                # +2.1 / +2.4 ms mean / p95 of the ego veto (gate_table.md 29.09)
    "shell_cable_on": 21,         # cable_low first STOP 21.0 m with the shell rule, 73.8 m without,
    "shell_cable_off": 74,        #   22 m/s ray-cast tunnel (commit a5455b3)
    "echo_max_m": 210,            # no return beyond ~210 m in all 13 759 frames (EXPERIMENTS)
}
G, F = GATE, FIXED


def pl(n, one, few, many):
    """The Russian noun form for the count ``n`` (1 кадр, 2 кадра, 5 кадров)."""
    n = abs(int(n))
    if 11 <= n % 100 <= 14:
        return many
    return one if n % 10 == 1 else few if 2 <= n % 10 <= 4 else many


def dec(x, digits=1):
    """A number with a decimal comma: 2.0 -> "2,0"."""
    return f"{x:.{digits}f}".replace(".", ",")


def thousands(n):
    return f"{n:,}".replace(",", " ")


_ONES = ["ноль", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"]
_TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
          "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"]
_TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят",
         "восемьдесят", "девяносто"]
_HUNDREDS = ["", "сто", "двести", "триста", "четыреста", "пятьсот", "шестьсот", "семьсот",
             "восемьсот", "девятьсот"]
_GENITIVE = {
    "ноль": "ноля", "один": "одного", "одна": "одной", "одно": "одного", "два": "двух", "две": "двух",
    "три": "трёх", "четыре": "четырёх", "пять": "пяти", "шесть": "шести", "семь": "семи",
    "восемь": "восьми", "девять": "девяти", "десять": "десяти", "одиннадцать": "одиннадцати",
    "двенадцать": "двенадцати", "тринадцать": "тринадцати", "четырнадцать": "четырнадцати",
    "пятнадцать": "пятнадцати", "шестнадцать": "шестнадцати", "семнадцать": "семнадцати",
    "восемнадцать": "восемнадцати", "девятнадцать": "девятнадцати", "двадцать": "двадцати",
    "тридцать": "тридцати", "сорок": "сорока", "пятьдесят": "пятидесяти", "шестьдесят": "шестидесяти",
    "семьдесят": "семидесяти", "восемьдесят": "восьмидесяти", "девяносто": "девяноста", "сто": "ста",
    "двести": "двухсот", "триста": "трёхсот", "четыреста": "четырёхсот", "пятьсот": "пятисот",
    "шестьсот": "шестисот", "семьсот": "семисот", "восемьсот": "восьмисот", "девятьсот": "девятисот",
    "тысяча": "тысячи", "тысячи": "тысяч", "тысяч": "тысяч"}


def _below_1000(n, gender):
    words = []
    h, r = divmod(n, 100)
    if h:
        words.append(_HUNDREDS[h])
    if 10 <= r < 20:
        words.append(_TEENS[r - 10])
    else:
        t, u = divmod(r, 10)
        if t:
            words.append(_TENS[t])
        if u:
            words.append({"f": {1: "одна", 2: "две"}, "n": {1: "одно"}}.get(gender, {}).get(u, _ONES[u]))
    return words


def words(n, case="nom", gender="m"):
    """``n`` (0 <= n < 10**6) in Russian words, nominative or genitive (for the narration)."""
    n = int(n)
    th, rest = divmod(n, 1000)
    out = []
    if th:
        out += _below_1000(th, "f") + [pl(th, "тысяча", "тысячи", "тысяч")]
    if rest or not out:
        out += _below_1000(rest, gender) or ["ноль"]
    if case == "gen":
        out = [_GENITIVE.get(w, w) for w in out]
    return " ".join(out)


def words_dec(x):
    """A one-decimal number in words: 2.0 -> "два", 2.2 -> "две целых две десятых"."""
    i, d = divmod(int(round(x * 10)), 10)
    if d == 0:
        return words(i)
    return (f"{words(i, gender='f')} {pl(i, 'целая', 'целых', 'целых')} "
            f"{words(d, gender='f')} {pl(d, 'десятая', 'десятых', 'десятых')}")


# derived from the block (never typed twice)
DT_SAY_M = int(round((G["dt_near_m"] + G["dt_far_m"]) / 2))            # the person's distance, m
DT_GAPLESS = G["dt_stop_frames"] == F["dt_frames"] - G["dt_first_stop_frame"]
RIDE_PER_KM = G["ride_events"] / F["ride_km"]
M = lambda n: pl(n, "метр", "метра", "метров")                           # noqa: E731
FR = lambda n: pl(n, "кадр", "кадра", "кадров")                          # noqa: E731
EV = lambda n: pl(n, "событие", "события", "событий")                    # noqa: E731
OBJ = lambda n: pl(n, "объект", "объекта", "объектов")                   # noqa: E731
GATE_NOTE = f"гейт {G['run']}"


def _all_or_some(hits, total, noun):
    """(subtitle, spoken) for "STOP in every frame" or "STOP in N of M frames"."""
    if hits == total:
        return (f"{hits} {noun(hits)}, и STOP в каждом", f"{words(hits)} {noun(hits)}, и стоп в каждом")
    return (f"STOP в {hits} {noun(hits)} из {total}",
            f"стоп — {words(hits)} {noun(hits)} из {words(total, 'gen')}")


_PERSON = _all_or_some(G["dt_person"], F["dt_person_frames"], FR)
_RAIL = _all_or_some(G["dt_rail"], F["dt_rail_frames"], FR)
_O_ALL = G["o_inside_stop"] == G["o_inside"]
_O_SUB = (f"STOP получают все {G['o_inside']} {OBJ(G['o_inside'])} в габарите"
          if _O_ALL else f"STOP получают {G['o_inside_stop']} из {G['o_inside']} объектов в габарите")
_O_SAY = (f"Стоп получают все {words(G['o_inside'])} {OBJ(G['o_inside'])} в габарите"
          if _O_ALL else f"Стоп получают {words(G['o_inside_stop'])} из "
                         f"{words(G['o_inside'], 'gen')} объектов в габарите")

# ---- the cut: problem -> idea -> algorithm -> demonstration -> results -> what we got -----------
# (the organizers' pitch arc, ТЗ §8.8). A subtitle is (t0, t1, text) or (t0, t1, text, spoken): the
# text is burned in and written to the .srt with the numbers in digits; ``spoken`` is what the voice
# reads (numbers in words, Latin names as said), by default the text itself (see ``spoken()``).
BLOCKS = [
    {"name": "Проблема", "t0": 0.0, "t1": 18.0,
     "shots": [
         shot(0.0, 18.0, "img/hero_ride_clean.png", zoom=(1.0, 1.15), focus=(0.505, 0.45), bits=0.35,
              note="img/hero_ride_clean.png · поездка организаторов, реальные данные"),
     ],
     "cards": [
         num(8.6, "≈ 200 м", "тормозной путь с 80 км/ч при замедлении 1,2 м/с² (v² / 2a)"),
         num(13.2, "13 км", "20-минутная поездка организаторов; препятствий для обучения нейросети "
                            "в данных почти нет", REAL),
     ],
     "subs": [
         (0.6, 5.0, "Поезд метро без машиниста должен сам понять, свободен ли путь впереди."),
         (5.2, 9.8, "С 80 км/ч ему нужно около 200 метров, чтобы остановиться.",
          "С восьмидесяти километров в час ему нужно около двухсот метров, чтобы остановиться."),
         (10.0, 13.0, "А тоннель однообразен и почти всегда пуст:"),
         (13.2, 17.6, "препятствий, на которых можно учить нейросеть, в данных почти нет."),
     ]},
    {"name": "Идея", "t0": 18.0, "t1": 35.0,
     "shots": [
         shot(18.0, 26.0, "video/doubleT_obstacle_offline.mp4", at=0.0, bits=0.5,
              note="video/doubleT_obstacle_offline.mp4 · архивный рендер v0.6.2 · вид сверху и сбоку, "
                   "ось пути зелёным"),
         shot(26.0, 35.0, "img/hero_ride_clean.png",
              note="img/hero_ride_clean.png · поездка 13 км, кадр 220, реальные данные"),
     ],
     "cards": [
         text(18.4, "описываем нормальный тоннель, а не объекты"),
         text(22.2, "ось пути — по рельсам, дальше — по стенам и колоннам"),
         num(30.2, "2,1 × 3,0 м", "габарит поезда вдоль оси пути"),
     ],
     "subs": [
         (18.4, 22.0, "Поэтому мы описываем не препятствия, а нормальный тоннель."),
         (22.2, 26.0, "Каждый кадр лидар калибруется по рельсам и строит ось пути,"),
         (26.2, 30.0, "а изгиб продлевает по стенам — туда, где рельсов уже не видно."),
         (30.2, 34.8, "Вдоль оси — габарит поезда. Всё, что в нём не путь, — кандидат в препятствия."),
     ]},
    {"name": "Алгоритм", "t0": 35.0, "t1": 52.0,
     "shots": [
         shot(35.0, 52.0, "board:algo", note="схема алгоритма · docs/ALGORITHM.md"),
     ],
     "cards": [
         text(35.4, "5 шагов на кадр, без обучения на объектах"),
         text(40.4, "выход: GO · CAUTION · STOP · FAULT и дальность контроля"),
         num(45.8, f"{F['lat_p95']} мс", f"p95 от кадра до решения через ROS, 360°, 4 ядра, без GPU · "
                                         f"оценка 28.09, прежний детектор; правила 29.09 — ещё "
                                         f"~{F['rules_ms']} мс", REAL),
     ],
     "subs": [
         (35.4, 40.2, "Пять шагов на кадр: калибровка, модель пути, габарит, кластеры, подтверждение."),
         (40.4, 45.6, "На выходе — GO, CAUTION, STOP или FAULT и честная оценка дальности контроля.",
          "На выходе — гоу, кошн, стоп или фолт, и честная оценка дальности контроля."),
         (45.8, 51.6, "От кадра до решения — меньше 100 мс на четырёх ядрах, без видеокарты.",
          "От кадра до решения — меньше ста миллисекунд на четырёх ядрах, без видеокарты."),
     ]},
    {"name": "Демонстрация", "t0": 52.0, "t1": 101.0,
     "shots": [
         shot(52.0, 58.0, "board:chain", note="команды жюри из README.md, шаги 1–4"),
         shot(58.0, 64.0, "video/docker_chain_rviz.mp4", at=0.0,
              note="архивная запись цепочки v0.6.2 · docker run, до входа FAULT"),
         shot(64.0, 70.0, "video/docker_chain_rviz.mp4", at=12.0,
              note="архивная запись цепочки v0.6.2 · ros2 bag play из другого контейнера"),
         shot(70.0, 76.0, "video/docker_chain_rviz.mp4", at=24.0,
              note="архивная запись цепочки v0.6.2 · /resense/decision: STOP"),
         shot(76.0, 86.0, "video/doubleT_obstacle_cab.mp4", at=0.0, bits=0.35,
              note=f"архивное видео v0.6.2 · doubleT_obstacle, поезд стоит; числа — {GATE_NOTE}"),
         shot(86.0, 95.0, "video/doubleT_obstacle_cab.mp4", at=9.0, bits=0.35,
              note=f"архивное видео v0.6.2 · предмет на рельсе; числа — {GATE_NOTE}"),
         shot(95.0, 101.0, "video/dashboard_current.mp4", at=0.0,
              note="video/dashboard_current.mp4 · веб-интерфейс на архивных статусах узла, 2×"),
     ],
     "cards": [
         steps(52.4, ["docker load", "docker run", "ros2 bag play", "/resense/decision"],
               [(52.4, 0), (58.0, 1), (64.0, 2), (70.0, 3)]),
         num(70.0, "STOP", f"человек на пути: {dec(G['dt_near_m'])}–{dec(G['dt_far_m'])} м · "
                           f"doubleT_obstacle", REAL),
         num(80.8, f"кадр {G['dt_first_stop_frame']}",
             f"первый STOP; всего {G['dt_stop_frames']} из {F['dt_frames']} кадров"
             + (", без пропусков" if DT_GAPLESS else ""), REAL),
         num(86.2, f"{G['dt_person']} из {F['dt_person_frames']}", "кадров с человеком — тревога", REAL),
         num(91.0, f"{G['dt_rail']} из {F['dt_rail_frames']}",
             "кадров с предметом на рельсе (с кадра 75) — STOP", REAL),
     ],
     "subs": [
         (52.4, 57.8, "Цепочка жюри как есть: docker load ставит образ без интернета,",
          "Цепочка жюри как есть: докер лоуд ставит образ без интернета,"),
         (58.0, 63.8, "docker run запускает узел — пока данных нет, он честно говорит FAULT.",
          "докер ран запускает узел — пока данных нет, он честно говорит фолт."),
         (64.0, 69.8, "Из другого контейнера — ros2 bag play с записью организаторов.",
          "Из другого контейнера — рос два бэг плэй с записью организаторов."),
         (70.0, 75.8, f"На выходе узла — STOP: человек на пути, {DT_SAY_M} {M(DT_SAY_M)}.",
          f"На выходе узла — стоп: человек на пути, {words(DT_SAY_M)} {M(DT_SAY_M)}."),
         (76.2, 80.6, "Вот поезд в тоннеле. Вот лидар. А вот человек на пути:"),
         (80.8, 86.0, f"алгоритм увидел его за {DT_SAY_M} {M(DT_SAY_M)}"
                      + (", и STOP держится до конца записи." if DT_GAPLESS else "."),
          f"алгоритм увидел его за {words(DT_SAY_M)} {M(DT_SAY_M)}"
          + (", и стоп держится до конца записи." if DT_GAPLESS else ".")),
         (86.2, 90.8, f"Кадров с человеком — {_PERSON[0]}.", f"Кадров с человеком — {_PERSON[1]}."),
         (91.0, 95.8, f"Он уходит, на рельсе остаётся предмет: {_RAIL[0]}.",
          f"Он уходит, на рельсе остаётся предмет: {_RAIL[1]}."),
         (96.0, 100.6, "Тот же STOP оператор видит в веб-интерфейсе.",
          "Тот же стоп оператор видит в веб-интерфейсе."),
     ]},
    {"name": "Результаты", "t0": 101.0, "t1": 150.0,
     "shots": [
         shot(101.0, 115.0, "board:set_o",
              note=f"набор O: cloud_with_fake_obj, синтетика организаторов · {GATE_NOTE}"),
         shot(115.0, 127.0, "board:false", note=f"поездка new_data и пять пустых записей · {GATE_NOTE}"),
         shot(127.0, 139.0, "board:rules", note="правила 29.09 · docs/DECISIONS.md № 30; коммит a5455b3"),
         shot(139.0, 150.0, "board:set_f", note=f"набор F: наша синтетика в реальных кадрах · {GATE_NOTE}"),
     ],
     "cards": [
         num(101.4, f"{G['o_inside_stop']} из {G['o_inside']}",
             f"объектов в габарите — STOP; вне габарита ложный STOP — {G['o_outside_false']} "
             f"{FR(G['o_outside_false'])}", ORG),
         num(106.2, f"{G['o_big_center_m']} м", "ящик 2 × 2 м: первый STOP, поезд едет к нему", ORG),
         num(115.4, f"{dec(RIDE_PER_KM)} на км",
             f"ложного события на поездке, где подбирались правила ({G['ride_events']} за "
             f"{F['ride_km']} км); пять пустых записей — {G['empty_events']}", REAL),
         text(127.4, "из трёх правил других команд два включены, одно выключено ради безопасности"),
         num(139.4, f"{G['f_person_m']} м", "человек на подходе по прямой: медиана первого "
                                           "обнаружения", OURS),
     ],
     "subs": [
         (101.4, 106.0, "Объекты организаторов — их синтетика в реальной поездке."),
         (106.2, 111.0, f"{_O_SUB}; ящик 2 × 2 метра — за {G['o_big_center_m']} "
                        f"{M(G['o_big_center_m'])}.",
          f"{_O_SAY}; ящик два на два метра — за {words(G['o_big_center_m'])} "
          f"{M(G['o_big_center_m'])}."),
         (111.2, 114.8, f"Кубы по 30 см — лишь с {G['o_small_on_rail_m']}–{G['o_small_center_m']} м.",
          f"Кубы по тридцать сантиметров — лишь с {words(G['o_small_on_rail_m'], 'gen')} — "
          f"{words(G['o_small_center_m'], 'gen')} метров."),
         (115.4, 121.0, f"Ложные тревоги: на поездке {F['ride_km']} км — {G['ride_events']} "
                        f"{EV(G['ride_events'])}, {dec(RIDE_PER_KM)} на километр.",
          f"Ложные тревоги: на поездке {words(F['ride_km'])} километров — {words(G['ride_events'], gender='n')} "
          f"{EV(G['ride_events'])}, {words_dec(RIDE_PER_KM)} на километр."),
         (121.2, 126.6, "Это та же поездка, на которой подбирались правила, — оценка в выборке."),
         (127.4, 132.4, f"Правила других команд против ложных тревог: было {F['ride_events_before']} "
                        f"{EV(F['ride_events_before'])}, стало {G['ride_events']}.",
          f"Правила других команд против ложных тревог: было {words(F['ride_events_before'], gender='n')} "
          f"{EV(F['ride_events_before'])}, стало {words(G['ride_events'], gender='n')}."),
         (132.6, 138.6, f"Одно правило выключили: висящий кабель оно пропускало до {F['shell_cable_on']} м.",
          f"Одно правило мы выключили: висящий кабель оно пропускало до "
          f"{words(F['shell_cable_on'], 'gen')} метров."),
         (139.4, 144.4, f"На нашей синтетике человека на подходе видно за {G['f_person_m']} "
                        f"{M(G['f_person_m'])}.",
          f"На нашей синтетике человека на подходе видно за {words(G['f_person_m'])} "
          f"{M(G['f_person_m'])}."),
         (144.6, 149.4, f"Дальше {F['echo_max_m']} метров отражений в тоннеле нет.",
          f"Дальше {words(F['echo_max_m'], 'gen')} метров отражений в тоннеле нет."),
     ]},
    {"name": "Что получилось", "t0": 150.0, "t1": 180.0,
     "shots": [
         shot(150.0, 156.0, "video/dashboard_current.mp4", at=1.2,
              note="video/dashboard_current.mp4 · веб-интерфейс на архивных статусах узла, 2×"),
         shot(156.0, 164.0, "video/doubleT_obstacle_cab.mp4", at=0.0, bits=0.35,
              note=f"архивное видео v0.6.2 · doubleT_obstacle: реальные данные, поезд стоит · {GATE_NOTE}"),
         shot(164.0, 172.0, "video/fake_objects_cab.mp4", at=0.0, bits=0.25,
              note=f"архивное видео · cloud_with_fake_obj: синтетика организаторов, поезд едет · "
                   f"{GATE_NOTE}"),
     ],
     "cards": [
         text(150.4, "узел ROS 2 в Docker: без интернета, без видеокарты, с интерфейсом оператора"),
         num(156.4, f"{DT_SAY_M} м", "реальный человек на пути — STOP · doubleT_obstacle", REAL),
         num(164.4, f"{G['o_big_center_m']} м", "ящик 2 × 2 м — первый STOP, поезд едет", ORG),
     ],
     "subs": [
         (150.4, 155.8, "Что получилось: узел ROS 2 в Docker — без интернета и без видеокарты.",
          "Что получилось: узел рос два в докере — без интернета и без видеокарты."),
         (156.2, 163.8, f"Вот поезд в тоннеле. Вот лидар. А вот человек, которого наш алгоритм увидел "
                        f"за {DT_SAY_M} {M(DT_SAY_M)}.",
          f"Вот поезд в тоннеле. Вот лидар. А вот человек, которого наш алгоритм увидел "
          f"за {words(DT_SAY_M)} {M(DT_SAY_M)}."),
         (164.2, 171.8, f"А вот поезд едет по тоннелю — и препятствие, которое алгоритм увидел "
                        f"за {G['o_big_center_m']} {M(G['o_big_center_m'])}.",
          f"А вот поезд едет по тоннелю — и препятствие, которое алгоритм увидел "
          f"за {words(G['o_big_center_m'])} {M(G['o_big_center_m'])}."),
         (172.4, 179.2, "ReSense, команда «Молоток». Docker load, docker run, ros2 bag play — "
                        "и система ищет препятствия.",
          "Ри-сенс, команда «Молоток». Докер лоуд, докер ран, рос два бэг плэй — "
          "и система ищет препятствия."),
     ]},
]
# the title over the first shot (full frame), then the picture shrinks into the layout
OPENING = {"until": 7.4, "shrink": (7.4, 8.4),
           "title": "ReSense",
           "line1": "команда «Молоток» · кейс 05, ЛЦТ 2026",
           "line2": "обнаружение посторонних объектов в тоннеле метро по данным 3D-лидара"}
# the closing card (full frame) over the blurred ride render, from t0 to the end
FINAL = {"t0": 172.0, "src": "img/hero_ride_clean.png",
         "title": "ReSense",
         "line1": "команда «Молоток» · кейс 05, ЛЦТ 2026",
         "chain": "docker load → docker run → ros2 bag play → /resense/decision",
         "repo": REPO_LINE}

# the pictures drawn here (``board:NAME`` shots): big type, every number from GATE / FIXED
BOARDS = {
    "algo": {"title": "Алгоритм: пять шагов на каждый кадр", "kind": "steps",
             "rows": [("Автокалибровка", "ось вращения, крен и тангаж — по рельсам и полотну"),
                      ("Модель пути", "головки рельсов и ось; изгиб — по стенам и колоннам до 150–200 м"),
                      ("Габарит", "коридор 2,1 × 3,0 м вдоль оси и ступень низких объектов на рельсах"),
                      ("Кластеры", "радиус растёт с дальностью; фильтры инфраструктуры"),
                      ("Решение", "подтверждение 0,5 с → GO / CAUTION / STOP / FAULT и дальность "
                                  "контроля")],
             "foot": "без обучения на объектах · без GPU · параметры — configs/default.yaml"},
    "chain": {"title": "Цепочка жюри — README, шаги 1–4", "kind": "terminal",
              "rows": [("# 1 · один раз, без интернета", None),
                       ("$ docker load -i resense-image-<версия>.tar.gz", None),
                       ("# 2 · консоль 1: узел", None),
                       ("$ docker run --rm -it --net=host --ipc=host resense", None),
                       ("# 3 · консоль 2: запись организаторов", None),
                       ("$ ros2 bag play <бэг> --delay 3 --read-ahead-queue-size 10", None),
                       ("# 4 · консоль 3: GO | CAUTION | STOP | FAULT", None),
                       ("$ ros2 topic echo /resense/decision --field data", None),
                       ("STOP", None)],
              "foot": "архив образа — из релиза; без него шаг 1 заменяет docker build"},
    "set_o": {"title": "Объекты организаторов: первый STOP, м", "kind": "bars", "tag": ORG,
              "rows": [("ящик 2 × 2 м у верха габарита", G["o_big_above_m"]),
                       ("ящик 2 × 2 м в центре", G["o_big_center_m"]),
                       ("доска поперёк рельсов", G["o_long_low_m"]),
                       ("куб 0,3 м в центре", G["o_small_center_m"]),
                       ("куб 0,3 м на рельсе", G["o_small_on_rail_m"]),
                       ("куб 0,3 м у края", G["o_small_edge_m"]),
                       ("висящий предмет", G["o_thin_hanging_m"]),
                       ("ящик 2 × 2 м у края", G["o_big_edge_m"])],
              "max": 150,
              "foot": f"cloud_with_fake_obj, поезд едет к объектам до 20 м/с · STOP у "
                      f"{G['o_inside_stop']} из {G['o_inside']} · {GATE_NOTE}"},
    "false": {"title": "Ложные тревоги на реальных записях", "kind": "stats", "tag": REAL,
              "rows": [(f"{G['ride_events']}", f"{EV(G['ride_events'])} на поездке {F['ride_km']} км, "
                                             f"{dec(RIDE_PER_KM)} на км\nэпизодов STOP: "
                                             f"{G['ride_stop_episodes']}"),
                       (f"{G['empty_events']}", f"{EV(G['empty_events'])} на пяти пустых записях\n"
                                              f"эпизодов STOP: {G['empty_stop_episodes']}"),
                       (thousands(F["real_frames"]), "реальных кадров прогнаны целиком")],
              "foot": f"в выборке: на этой поездке подбирались правила · {GATE_NOTE}"},
    "rules": {"title": "Правила 29.09 из открытых решений кейса 05", "kind": "checks",
              "rows": [(True, "объяснённый пробег: пропуск, если трек объяснён инфраструктурой"),
                       (True, "запрет эго-движения: трек, который не приближается при движении поезда, "
                              "не даёт STOP"),
                       (False, f"«оболочка» — выключена: висящий кабель получал STOP лишь с "
                               f"{F['shell_cable_on']} м вместо {F['shell_cable_off']} м")],
              "foot": f"поездка: было {F['ride_events_before']} {EV(F['ride_events_before'])}, стало "
                      f"{G['ride_events']} · {GATE_NOTE}"},
    "set_f": {"title": "Человек и предметы на подходе: первое обнаружение, м", "kind": "bars",
              "tag": OURS,
              "rows": [("человек 1,7 м", G["f_person_m"]),
                       ("тележка", G["f_trolley_m"]),
                       ("ящик 1 м", G["f_box1_m"]),
                       ("висящий кабель 3 см", G["f_cable_m"]),
                       ("ящик 0,5 м", G["f_box05_m"])],
              "max": 200,
              "foot": f"медиана 6 подходов по прямой · дальше ~{F['echo_max_m']} м отражений нет · "
                      f"{GATE_NOTE}"},
}

# the voice: Latin names as a Russian speaker says them (numbers are spelled in ``spoken`` above)
SAY = [(r"\bSTOP\b", "стоп"), (r"\bGO\b", "гоу"), (r"\bCAUTION\b", "кошн"), (r"\bFAULT\b", "фолт"),
       (r"\bROS 2\b", "рос два"), (r"\bROS\b", "рос"), (r"\bDocker\b", "докер"), (r"\bReSense\b", "Ри-сенс")]


def spoken(cue):
    """What the voice reads for a subtitle cue."""
    s = cue[3] if len(cue) > 3 else cue[2]
    for pat, rep in SAY:
        s = re.sub(pat, rep, s)
    if re.search(r"\d", s):
        raise ValueError(f"digits left for the voice: {s!r}")
    return s


# ---- layout in 1920x1080 units (scaled for other sizes) ----------------------------------------
BG = (19, 10, 26)                  # the renders' dark violet
RED = (228, 0, 13)                 # #E4000D, the dashboard's red
WHITE = (255, 255, 255)
INK = (27, 24, 31)
MUTED = (150, 141, 160)
VISUAL = (32, 32, 1440, 810)       # picture: x, y, w, h (16:9)
SIDE = (1504, 32, 384, 810)        # sidebar: x, y, w, h
SUB_BOTTOM = 1034                  # subtitles: bottom of the last line
SUB_SIZE, SUB_LINE = 50, 62        # subtitle font size, line height
SUB_ONE_LINE = 1150                # a cue this wide or less stays on one line
SUB_MAX = 1700                     # the widest subtitle line
PROGRESS = (32, 1066, 1856, 4)     # the thin progress bar at the bottom
SOURCE_H = 80                      # room for the source line (3 lines) at the bottom of the sidebar
CARD_GAP = 14


# ================================================================ table checks (no Pillow needed)

def all_shots():
    return [s for b in BLOCKS for s in b["shots"]]


def all_subs():
    return [c for b in BLOCKS for c in b["subs"]]


def check_table(files=True):
    """Timing (and with ``files`` source) checks of the table; returns the problems (empty = fine)."""
    bad = []
    if BLOCKS[0]["t0"] != 0.0 or BLOCKS[-1]["t1"] != DURATION:
        bad.append("blocks must span 0 .. DURATION")
    for a, b in zip(BLOCKS, BLOCKS[1:]):
        if a["t1"] != b["t0"]:
            bad.append(f"gap between blocks {a['name']} and {b['name']}")
    shots = all_shots()
    if shots[0]["t0"] != 0.0 or shots[-1]["t1"] != FINAL["t0"]:
        bad.append("shots must span 0 .. FINAL t0")
    for a, b in zip(shots, shots[1:]):
        if a["t1"] != b["t0"]:
            bad.append(f"shots not contiguous at {a['t1']} / {b['t0']}")
    for s in shots + [FINAL]:
        if s["src"].startswith("board:"):
            if s["src"][6:] not in BOARDS:
                bad.append(f"no board {s['src']}")
            continue
        if s["src"].startswith("deck:"):
            path = os.path.join(DOCS, DECK_PDF)
        else:
            path = os.path.join(DOCS, s["src"])
        if files and not os.path.isfile(path):
            bad.append(f"missing source {path}")
        if s is not FINAL and s["t1"] - s["t0"] < 2 * XFADE:
            bad.append(f"shot {s['src']} at {s['t0']} shorter than two cross-fades")
    for b in BLOCKS:
        for s in b["shots"]:
            if not b["t0"] <= s["t0"] < s["t1"] <= b["t1"]:
                bad.append(f"shot at {s['t0']} outside block {b['name']}")
        prev_end = b["t0"]
        for cue in b["subs"]:
            t0, t1, line = cue[:3]
            try:
                spoken(cue)
            except ValueError as e:
                bad.append(str(e))
            if not (b["t0"] <= t0 < t1 <= b["t1"]):
                bad.append(f"subtitle at {t0} outside block {b['name']}")
            if t0 < prev_end - 1e-9:
                bad.append(f"subtitle at {t0} overlaps the previous one")
            if t1 - t0 < 1.0:
                bad.append(f"subtitle at {t0} shorter than 1 s")
            if len(line) / (t1 - t0) > 17.0:                 # a voice reads ~15 characters/s
                bad.append(f"subtitle at {t0}: {len(line) / (t1 - t0):.1f} characters/s (> 17)")
            prev_end = t1
        times = [c["t"] for c in b["cards"]]
        if times != sorted(times) or any(not b["t0"] <= t < b["t1"] for t in times):
            bad.append(f"cards of {b['name']} out of order or outside the block")
    return bad


def fmt_srt_time(t):
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def parse_srt(path):
    """[(t0, t1, text with line breaks)] of an .srt file."""
    with open(path, encoding="utf-8") as f:
        chunks = [c for c in re.split(r"\n\s*\n", f.read().strip()) if c.strip()]
    out = []
    for c in chunks:
        lines = c.splitlines()
        a, b = lines[1].split(" --> ")

        def sec(x):
            h, m, rest = x.strip().split(":")
            s, ms = rest.split(",")
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

        out.append((sec(a), sec(b), "\n".join(lines[2:])))
    return out


# ================================================================ text layout

GLUE_BEFORE = {"—", "–", "→", "×", "%", "·"}          # never start a line with these


def units(textline):
    """Words glued so that a line never breaks after a number or a one/two-letter word, nor before
    a dash / arrow / sign."""
    words = textline.split()
    out = []
    glue = False
    for w in words:
        if out and (glue or w in GLUE_BEFORE):
            out[-1] = out[-1] + " " + w
        else:
            out.append(w)
        bare = w.strip("«»()[],.;:")
        glue = (bool(re.fullmatch(r"[~−–\-+]?[\d.,…–−]*\d[\d.,…–−]*", bare))
                or (len(bare) <= 2 and bare.isalpha()) or w in {"×", "→"})
    return out


class Fonts:
    def __init__(self, scale):
        from PIL import ImageFont

        self.scale = scale
        self._cache = {}
        d = os.path.join(ROOT, "web", "assets", "fonts")
        candidates = {
            "regular": [os.path.join(d, "MoscowSansRegular.otf"),
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"],
            "bold": [os.path.join(d, "MoscowSansExtraBold.otf"),
                     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
            "mono": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
                     "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
                     "/Library/Fonts/Courier New.ttf", "C:/Windows/Fonts/consola.ttf"],
            "monobold": ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
                         "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
                         "/Library/Fonts/Courier New Bold.ttf", "C:/Windows/Fonts/consolab.ttf"],
        }
        self.paths = {}
        for k, paths in candidates.items():
            self.paths[k] = next((p for p in paths if os.path.isfile(p)), None)
            if self.paths[k] is None:
                sys.exit(f"no font with Cyrillic for {k}: tried {paths}")
        self._ImageFont = ImageFont

    def get(self, kind, size):
        px = max(8, int(round(size * self.scale)))
        key = (kind, px)
        if key not in self._cache:
            self._cache[key] = self._ImageFont.truetype(self.paths[kind], px)
        return self._cache[key]


def text_w(font, s):
    return font.getlength(s)


def wrap(textline, font, width, balance=False):
    """Greedy wrap on glued units; ``balance``: the narrowest width with as few lines (no widows)."""
    if balance:
        n = len(wrap(textline, font, width))
        w = width
        while w > width * 0.55 and len(wrap(textline, font, w - 4)) == n:
            w -= 4
        width = w
    lines, cur = [], ""
    for u in units(textline):
        cand = u if not cur else cur + " " + u
        if text_w(font, cand) <= width or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = u
    if cur:
        lines.append(cur)
    return lines


def split_subtitle(textline, font, one_line, max_w):
    """One line if it is short, else the most balanced two lines (a break after punctuation is
    preferred). Raises if two lines are not enough."""
    if text_w(font, textline) <= one_line:
        return [textline]
    us = units(textline)
    best = None
    for i in range(1, len(us)):
        a, b = " ".join(us[:i]), " ".join(us[i:])
        wa, wb = text_w(font, a), text_w(font, b)
        if wa > max_w or wb > max_w:
            continue
        score = max(wa, wb) - (0.12 * max_w if a[-1] in ",;:—" else 0.0)
        if best is None or score < best[0]:
            best = (score, [a, b])
    if best is None:
        raise ValueError(f"subtitle does not fit two lines: {textline!r}")
    return best[1]


# ================================================================ drawing helpers

def S(v, scale):
    return int(round(v * scale))


def rounded_mask(size, radius):
    from PIL import Image, ImageDraw

    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return m


def with_alpha(img, alpha):
    """An RGBA copy with its alpha multiplied by ``alpha``."""
    if alpha >= 0.999:
        return img
    out = img.copy()
    out.putalpha(img.getchannel("A").point(lambda v: int(v * alpha + 0.5)))
    return out


def paste_rgba(canvas, img, xy, alpha=1.0):
    if alpha <= 0.001:
        return
    im = with_alpha(img, alpha)
    canvas.paste(im, (int(xy[0]), int(xy[1])), im)


def dip(w):
    """Opacity of a text layer whose shot has cross-fade weight ``w``: the old text is gone before
    the new one appears (no overlapping lines)."""
    return max(0.0, 2.0 * w - 1.0)


def ease(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def logo(fonts, scale, size):
    """The dashboard's mark: a red square with a white R."""
    from PIL import Image, ImageDraw

    px = S(size, scale)
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, px - 1, px - 1), radius=max(2, px // 7), fill=RED)
    f = fonts.get("bold", size * 0.68)
    d.text((px / 2, px / 2 + px * 0.02), "R", font=f, fill=WHITE, anchor="mm")
    return im


def tag_pill(fonts, scale, tag):
    from PIL import Image, ImageDraw

    label, bg, fg = TAGS[tag]
    f = fonts.get("bold", 17)
    s = label.upper()
    w = int(text_w(f, s)) + S(26, scale)
    h = S(30, scale)
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=bg)
    d.text((w / 2, h / 2 + S(1, scale)), s, font=f, fill=fg, anchor="mm")
    return im


def render_card(card, fonts, scale, active=None):
    """A white card with a red bar on the left; returns RGBA."""
    from PIL import Image, ImageDraw

    W = S(SIDE[2], scale)
    pad, bar = S(22, scale), S(6, scale)
    inner = W - 2 * pad - bar
    parts = []                      # (kind, payload, height)
    if card["kind"] == "num":
        size = 58
        fb = fonts.get("bold", size)
        while text_w(fb, card["big"]) > inner and size > 30:
            size -= 2
            fb = fonts.get("bold", size)
        parts.append(("big", (card["big"], fb), S(size * 1.08, scale)))
        parts.append(("gap", None, S(6, scale)))
        f = fonts.get("regular", 25)
        for ln in wrap(card["label"], f, inner, balance=True):
            parts.append(("line", (ln, f, INK), S(31, scale)))
    elif card["kind"] == "text":
        f = fonts.get("bold", 29)
        for ln in wrap(card["head"], f, inner, balance=True):
            parts.append(("line", (ln, f, INK), S(36, scale)))
    elif card["kind"] == "steps":
        f = fonts.get("bold", 26)
        for i, item in enumerate(card["items"]):
            parts.append(("step", (item, f, i, active), S(46, scale)))
    if card.get("tag"):
        parts.append(("gap", None, S(12, scale)))
        pill = tag_pill(fonts, scale, card["tag"])
        parts.append(("pill", pill, pill.size[1]))
    H = pad * 2 + sum(p[2] for p in parts)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = S(12, scale)
    d.rounded_rectangle((0, 0, W - 1, H - 1), radius=r, fill=WHITE)
    d.rounded_rectangle((0, 0, bar + r, H - 1), radius=r, fill=RED)
    d.rectangle((bar, 0, bar + r, H - 1), fill=WHITE)
    x, y = bar + pad, pad
    for kind, payload, h in parts:
        if kind == "big":
            s, fb = payload
            d.text((x, y + h * 0.82), s, font=fb, fill=RED, anchor="ls")
        elif kind == "line":
            s, f, color = payload
            d.text((x, y + h * 0.78), s, font=f, fill=color, anchor="ls")
        elif kind == "step":
            s, f, i, act = payload
            cx, cy, rr = x + S(9, scale), y + h / 2, S(7, scale)
            if i < len(card["items"]) - 1:            # the line to the next step
                d.line((cx, cy, cx, cy + h), fill=(205, 200, 210), width=max(1, S(2, scale)))
            if act is not None and i == act:
                d.rounded_rectangle((x + S(24, scale), y + S(4, scale), x + inner, y + h - S(4, scale)),
                                    radius=S(8, scale), fill=RED)
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=RED)
                d.text((x + S(36, scale), cy + S(1, scale)), s, font=f, fill=WHITE, anchor="lm")
            elif act is not None and i < act:
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=INK)
                d.text((x + S(36, scale), cy + S(1, scale)), s, font=f, fill=INK, anchor="lm")
            else:
                d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=WHITE,
                          outline=(170, 164, 176), width=max(1, S(2, scale)))
                d.text((x + S(36, scale), cy + S(1, scale)), s, font=f, fill=(160, 154, 166),
                       anchor="lm")
        elif kind == "pill":
            im.alpha_composite(payload, (x, y))
        y += h
    return im


# ================================================================ boards (pictures drawn here)

BOARD_BG = (30, 18, 40)
SOFT = (222, 214, 230)
GREEN = (40, 180, 99)


def render_board(board, fonts, scale, w, h):
    """A ``BOARDS`` entry as an RGB picture ``w`` x ``h``: big type in 1920-wide units."""
    from PIL import Image, ImageDraw

    im = Image.new("RGBA", (w, h), BOARD_BG + (255,))
    d = ImageDraw.Draw(im)
    x0, right = S(64, scale), w - S(64, scale)
    d.text((x0, S(92, scale)), board["title"], font=fonts.get("bold", 46), fill=WHITE, anchor="ls")
    d.rectangle((x0, S(112, scale), x0 + S(72, scale), S(118, scale)), fill=RED)
    if board.get("tag"):
        pill = tag_pill(fonts, scale, board["tag"])
        im.alpha_composite(pill, (right - pill.size[0], S(64, scale)))
    top, bottom = S(160, scale), h - S(84, scale)
    rows = board["rows"]
    kind = board["kind"]
    if kind == "steps":
        rh = (bottom - top) / len(rows)
        fn, ft, fd = fonts.get("bold", 30), fonts.get("bold", 36), fonts.get("regular", 29)
        for i, (head, desc) in enumerate(rows):
            cy = top + rh * (i + 0.5)
            r = S(30, scale)
            cx = x0 + r
            if i < len(rows) - 1:
                d.line((cx, cy + r, cx, cy + rh - r), fill=(90, 70, 104), width=max(1, S(3, scale)))
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=RED)
            d.text((cx, cy + S(1, scale)), str(i + 1), font=fn, fill=WHITE, anchor="mm")
            tx = cx + r + S(30, scale)
            d.text((tx, cy - S(6, scale)), head, font=ft, fill=WHITE, anchor="ls")
            d.text((tx, cy + S(34, scale)), desc, font=fd, fill=SOFT, anchor="ls")
    elif kind == "terminal":
        pad = S(36, scale)
        d.rounded_rectangle((x0, top - S(8, scale), right, bottom), radius=S(14, scale), fill=(10, 6, 14),
                            outline=(70, 56, 84), width=max(1, S(2, scale)))
        lh = (bottom - top - 2 * pad) / len(rows)
        fm, fb = fonts.get("mono", 29), fonts.get("monobold", 29)
        for i, (line, _) in enumerate(rows):
            y = top + pad + lh * (i + 0.72)
            if line.startswith("#"):
                d.text((x0 + pad, y), line, font=fm, fill=MUTED, anchor="ls")
            elif line.startswith("$"):
                d.text((x0 + pad, y), "$", font=fb, fill=RED, anchor="ls")
                d.text((x0 + pad + text_w(fb, "$ "), y), line[2:], font=fb, fill=WHITE, anchor="ls")
            else:
                d.text((x0 + pad, y), line, font=fonts.get("monobold", 34), fill=RED, anchor="ls")
    elif kind == "bars":
        fl, fv, fa = fonts.get("regular", 30), fonts.get("bold", 32), fonts.get("regular", 22)
        label_w = max(text_w(fl, lab) for lab, _ in rows)
        bx0 = x0 + label_w + S(28, scale)
        bx1 = right - S(90, scale)
        axis_y = bottom - S(10, scale)
        rh = (axis_y - top - S(16, scale)) / len(rows)
        vmax = board["max"]
        for tick in range(0, vmax + 1, 50):
            tx = bx0 + (bx1 - bx0) * tick / vmax
            d.line((tx, top - S(6, scale), tx, axis_y), fill=(62, 48, 74), width=max(1, S(2, scale)))
            d.text((tx, axis_y + S(28, scale)), str(tick), font=fa, fill=MUTED, anchor="ms")
        bh = min(S(46, scale), rh * 0.62)
        for i, (lab, v) in enumerate(rows):
            cy = top + rh * (i + 0.5)
            d.text((bx0 - S(28, scale), cy + S(10, scale)), lab, font=fl, fill=SOFT, anchor="rs")
            x1 = bx0 + (bx1 - bx0) * min(v, vmax) / vmax
            d.rounded_rectangle((bx0, cy - bh / 2, max(bx0 + S(8, scale), x1), cy + bh / 2),
                                radius=S(4, scale), fill=RED)
            d.text((x1 + S(14, scale), cy + S(11, scale)), f"{v} м", font=fv, fill=WHITE, anchor="ls")
    elif kind == "stats":
        rh = (bottom - top) / len(rows)
        fbig, flab = fonts.get("bold", 104), fonts.get("regular", 36)
        big_w = max(text_w(fbig, b) for b, _ in rows)
        for i, (big, lab) in enumerate(rows):
            cy = top + rh * (i + 0.5)
            d.text((x0 + big_w, cy + S(36, scale)), big, font=fbig, fill=RED if i < 2 else WHITE, anchor="rs")
            lines = [ln for part in lab.split("\n") for ln in wrap(part, flab, right - (x0 + big_w + S(44, scale)))]
            ly = cy - (len(lines) - 1) * S(24, scale) + S(12, scale)
            for ln in lines:
                d.text((x0 + big_w + S(44, scale), ly), ln, font=flab, fill=WHITE, anchor="ls")
                ly += S(48, scale)
    elif kind == "checks":
        rh = (bottom - top) / len(rows)
        ft = fonts.get("bold", 36)
        for i, (ok, line) in enumerate(rows):
            cy = top + rh * (i + 0.5)
            r = S(30, scale)
            cx = x0 + r
            d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=GREEN if ok else RED)
            k = r * 0.45
            if ok:
                d.line((cx - k, cy, cx - k * 0.2, cy + k * 0.8, cx + k, cy - k * 0.7), fill=WHITE,
                       width=max(2, S(6, scale)), joint="curve")
            else:
                for sx in (-1, 1):
                    d.line((cx - k, cy - k * sx, cx + k, cy + k * sx), fill=WHITE, width=max(2, S(6, scale)))
            lines = wrap(line, ft, right - (cx + r + S(30, scale)))
            ly = cy - (len(lines) - 1) * S(23, scale) + S(12, scale)
            for ln in lines:
                d.text((cx + r + S(30, scale), ly), ln, font=ft, fill=WHITE, anchor="ls")
                ly += S(46, scale)
    if board.get("foot"):
        d.text((x0, h - S(32, scale)), board["foot"], font=fonts.get("regular", 24), fill=MUTED, anchor="ls")
    return im.convert("RGB")


# ================================================================ sources

def find_ffmpeg(explicit=None):
    if explicit:
        return explicit
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001 - any failure falls back to PATH
        pass
    path = shutil.which("ffmpeg")
    if not path:
        sys.exit("ffmpeg not found: pass --ffmpeg, pip install imageio-ffmpeg, or install ffmpeg")
    return path


def render_deck_page(page, width):
    """Page ``page`` (1-based) of the deck as an RGB image ``width`` pixels wide."""
    from PIL import Image

    pdf = os.path.join(DOCS, DECK_PDF)
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(pdf)
        p = doc[page - 1]
        zoom = width / p.rect.width
        pix = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except ImportError:
        tool = shutil.which("pdftoppm")
        if not tool:
            sys.exit("deck pages need PyMuPDF (pip install pymupdf) or pdftoppm")
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "page")
            subprocess.run([tool, "-png", "-f", str(page), "-l", str(page), "-scale-to-x", str(width),
                            "-scale-to-y", "-1", "-singlefile", pdf, out], check=True)
            return Image.open(out + ".png").convert("RGB")


class Still:
    def __init__(self, img):
        self.img = img
        self._last = None

    def frame(self, w, h, zoom, focus):
        """The picture cropped to 16:9 (cover), zoomed about ``focus`` and resized to w x h."""
        from PIL import Image

        key = (w, h, round(zoom, 5))
        if self._last and self._last[0] == key:
            return self._last[1]
        iw, ih = self.img.size
        target = w / h
        if iw / ih > target:
            bw, bh = ih * target, ih
        else:
            bw, bh = iw, iw / target
        bx, by = (iw - bw) * focus[0], (ih - bh) * focus[1]
        cw, ch = bw / zoom, bh / zoom
        x0 = bx + (bw - cw) * focus[0]
        y0 = by + (bh - ch) * focus[1]
        out = self.img.resize((w, h), Image.Resampling.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
        self._last = (key, out)
        return out


class Clip:
    """Sequential frames of a clip from ``start`` s, scaled to w x h, read from an ffmpeg pipe."""

    def __init__(self, ffmpeg, path, start, w, h):
        self.w, self.h = w, h
        info = subprocess.run([ffmpeg, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
        m = re.search(r"(\d+(?:\.\d+)?) fps", info)
        self.fps = float(m.group(1)) if m else 10.0
        self.first = math.ceil(start * self.fps - 1e-6) / self.fps
        self.proc = subprocess.Popen(
            [ffmpeg, "-v", "error", "-ss", f"{start:.3f}", "-i", path,
             "-vf", f"scale={w}:{h}:flags=lanczos", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            stdout=subprocess.PIPE)
        self.index = -1
        self.cur = None

    def get(self, t):
        from PIL import Image

        k = max(0, int(math.floor((t - self.first) * self.fps + 1e-6)))
        while self.index < k:
            buf = self.proc.stdout.read(self.w * self.h * 3)
            if len(buf) < self.w * self.h * 3:
                break                               # past the end: hold the last frame
            self.cur = Image.frombytes("RGB", (self.w, self.h), buf)
            self.index += 1
        if self.cur is None:
            raise RuntimeError("clip gave no frames")
        return self.cur

    def close(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait()
        if self.proc.stdout:
            self.proc.stdout.close()


# ================================================================ the renderer

class Renderer:
    def __init__(self, size, ffmpeg):
        from PIL import Image, ImageDraw, ImageFilter

        self.Image, self.ImageDraw, self.ImageFilter = Image, ImageDraw, ImageFilter
        self.W, self.H = size
        self.scale = self.W / 1920.0
        self.ffmpeg = ffmpeg
        sc = self.scale
        self.fonts = Fonts(sc)
        self.vis = tuple(S(v, sc) for v in VISUAL)
        self.side = tuple(S(v, sc) for v in SIDE)
        self.shots = all_shots()
        self.shot_t0 = [s["t0"] for s in self.shots]
        self.stills = {}
        self.clips = {}
        self.vis_mask = rounded_mask(self.vis[2:], S(12, sc))
        self._build_blocks()
        self._build_subtitles()
        self._build_opening()
        self._build_final()
        self._build_progress()
        self.notes = [self._note_img(s["note"]) for s in self.shots]
        self.badges = [self._badge_img(s["badge"]) if s["badge"] else None for s in self.shots]
        self.logo = logo(self.fonts, sc, 44)

    # -- static pieces ---------------------------------------------------------------------------
    def _still(self, src):
        if src not in self.stills:
            if src.startswith("board:"):
                img = render_board(BOARDS[src[6:]], self.fonts, self.scale, self.vis[2], self.vis[3])
            elif src.startswith("deck:"):
                img = render_deck_page(int(src[5:]), 1920)
            else:
                img = self.Image.open(os.path.join(DOCS, src)).convert("RGB")
            self.stills[src] = Still(img)
        return self.stills[src]

    def _note_img(self, note):
        f = self.fonts.get("regular", 18)
        lines = wrap("кадр: " + note, f, self.side[2])
        if len(lines) > 3:
            raise ValueError(f"source line longer than 3 lines: {note!r}")
        im = self.Image.new("RGBA", (self.side[2], S(SOURCE_H, self.scale)), (0, 0, 0, 0))
        d = self.ImageDraw.Draw(im)
        lh = S(24, self.scale)
        y = im.size[1] - lh * len(lines)
        for ln in lines:
            d.text((0, y + lh * 0.8), ln, font=f, fill=MUTED, anchor="ls")
            y += lh
        return im

    def _badge_img(self, label):
        """A dark pill on the picture's lower right corner (e.g. demo data in a UI capture)."""
        sc = self.scale
        f = self.fonts.get("bold", 22)
        s = label.upper()
        w, h = int(text_w(f, s)) + S(40, sc), S(44, sc)
        im = self.Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = self.ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=h // 2, fill=(20, 12, 28, 235),
                            outline=(245, 196, 0), width=max(1, S(2, sc)))
        d.text((w / 2, h / 2 + S(1, sc)), s, font=f, fill=(245, 196, 0), anchor="mm")
        return im

    def _build_blocks(self):
        sc = self.scale
        for n, b in enumerate(BLOCKS):
            im = self.Image.new("RGBA", (self.side[2], S(260, sc)), (0, 0, 0, 0))
            d = self.ImageDraw.Draw(im)
            d.text((0, S(88, sc)), f"{n + 1:02d} / {len(BLOCKS):02d}", font=self.fonts.get("regular", 21),
                   fill=MUTED, anchor="ls")
            f = self.fonts.get("bold", 40)
            y = S(100, sc)
            for ln in wrap(b["name"], f, self.side[2]):
                d.text((0, y + S(40, sc)), ln, font=f, fill=WHITE, anchor="ls")
                y += S(48, sc)
            y += S(14, sc)
            d.rectangle((0, y, S(56, sc), y + S(6, sc)), fill=RED)
            b["_header"] = im
            b["_cards_top"] = y + S(6 + 26, sc)
            area = self.side[3] - b["_cards_top"] - S(SOURCE_H + 16, sc)
            b["_area"] = area
            for c in b["cards"]:
                if c["kind"] == "steps":
                    c["_imgs"] = [(t, render_card(c, self.fonts, sc, a)) for t, a in c["active"]]
                    c["_h"] = c["_imgs"][0][1].size[1]
                else:
                    c["_img"] = render_card(c, self.fonts, sc)
                    c["_h"] = c["_img"].size[1]
                if c["_h"] > area:
                    raise ValueError(f"card at {c['t']} taller than the sidebar")
            # states: after each card enters, the stack from the top; the oldest scroll out
            gap = S(CARD_GAP, sc)
            events, visible = [], []
            for i, c in enumerate(b["cards"]):
                visible = visible + [i]
                while sum(b["cards"][j]["_h"] for j in visible) + gap * (len(visible) - 1) > area:
                    visible = visible[1:]
                pos, y = {}, 0
                for j in visible:
                    pos[j] = y
                    y += b["cards"][j]["_h"] + gap
                events.append((c["t"], pos))
            b["_events"] = events

    def _build_subtitles(self):
        sc = self.scale
        f = self.fonts.get("regular", SUB_SIZE)
        self.cues = []
        for cue in all_subs():
            t0, t1, line = cue[:3]
            lines = split_subtitle(line, f, S(SUB_ONE_LINE, sc), S(SUB_MAX, sc))
            lh = S(SUB_LINE, sc)
            h = lh * len(lines) + S(24, sc)
            txt = self.Image.new("RGBA", (self.W, h), (0, 0, 0, 0))
            sh = self.Image.new("RGBA", (self.W, h), (0, 0, 0, 0))
            dt, ds = self.ImageDraw.Draw(txt), self.ImageDraw.Draw(sh)
            for i, ln in enumerate(lines):
                y = S(12, sc) + lh * (i + 0.78)
                ds.text((self.W / 2, y + S(2, sc)), ln, font=f, fill=(0, 0, 0, 200), anchor="ms")
                dt.text((self.W / 2, y), ln, font=f, fill=WHITE, anchor="ms")
            sh = sh.filter(self.ImageFilter.GaussianBlur(S(3, sc)))
            sh.alpha_composite(txt)
            y = S(SUB_BOTTOM, sc) - lh * len(lines) - S(12, sc)
            self.cues.append((t0, t1, lines, sh, y))
        self.cue_t0 = [c[0] for c in self.cues]

    def _gradient(self, top, alpha_max):
        """A dark gradient over the lower part of the frame (for subtitles over a full picture)."""
        h = self.H - top
        g = self.Image.new("L", (1, h))
        for y in range(h):
            g.putpixel((0, y), int(alpha_max * 255 * ease(y / max(1, h * 0.55))))
        a = g.resize((self.W, h))
        im = self.Image.new("RGBA", (self.W, h), BG + (0,))
        im.putalpha(a)
        return im

    def _build_opening(self):
        sc = self.scale
        im = self.Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        g = self.Image.new("L", (self.W, 1))
        for x in range(self.W):
            g.putpixel((x, 0), int(255 * 0.82 * (1 - ease(x / (self.W * 0.72)))))
        shade = self.Image.new("RGBA", (self.W, self.H), BG + (0,))
        shade.putalpha(g.resize((self.W, self.H)))
        im.alpha_composite(shade)
        d = self.ImageDraw.Draw(im)
        x = S(120, sc)
        im.alpha_composite(logo(self.fonts, sc, 96), (x, S(250, sc)))
        d.text((x - S(6, sc), S(500, sc)), OPENING["title"], font=self.fonts.get("bold", 150),
               fill=WHITE, anchor="ls")
        d.rectangle((x, S(532, sc), x + S(96, sc), S(540, sc)), fill=RED)
        d.text((x, S(610, sc)), OPENING["line1"], font=self.fonts.get("bold", 44), fill=WHITE,
               anchor="ls")
        d.text((x, S(664, sc)), OPENING["line2"], font=self.fonts.get("regular", 32),
               fill=(222, 214, 230), anchor="ls")
        self.opening = im
        self.sub_grad = self._gradient(S(760, sc), 0.88)

    def _build_final(self):
        sc = self.scale
        if FINAL["src"].startswith("deck:"):
            bgimg = render_deck_page(int(FINAL["src"][5:]), 1920)
        else:
            bgimg = self.Image.open(os.path.join(DOCS, FINAL["src"])).convert("RGB")
        bgimg = bgimg.resize((self.W, self.H))
        bgimg = bgimg.filter(self.ImageFilter.GaussianBlur(S(14, sc)))
        im = self.Image.blend(bgimg, self.Image.new("RGB", (self.W, self.H), BG), 0.86).convert("RGBA")
        d = self.ImageDraw.Draw(im)
        cx = self.W / 2
        ft = self.fonts.get("bold", 150)
        tw = text_w(ft, FINAL["title"])
        lg = logo(self.fonts, sc, 118)
        total = lg.size[0] + S(36, sc) + tw
        x0 = cx - total / 2
        im.alpha_composite(lg, (int(x0), S(170, sc)))
        d.text((x0 + lg.size[0] + S(36, sc), S(282, sc)), FINAL["title"], font=ft, fill=WHITE, anchor="ls")
        d.text((cx, S(380, sc)), FINAL["line1"], font=self.fonts.get("bold", 46), fill=WHITE, anchor="ms")
        fc = self.fonts.get("bold", 34)
        cw = text_w(fc, FINAL["chain"]) + S(64, sc)
        d.rounded_rectangle((cx - cw / 2, S(440, sc), cx + cw / 2, S(510, sc)), radius=S(35, sc),
                            fill=(38, 26, 48), outline=RED, width=max(1, S(3, sc)))
        d.text((cx, S(487, sc)), FINAL["chain"], font=fc, fill=WHITE, anchor="ms")
        fr = self.fonts.get("bold", 40)
        d.text((cx, S(610, sc)), FINAL["repo"], font=fr, fill=WHITE, anchor="ms")
        rw = text_w(fr, FINAL["repo"])
        d.rectangle((cx - rw / 2, S(626, sc), cx + rw / 2, S(631, sc)), fill=RED)
        self.final = im.convert("RGB")

    def _build_progress(self):
        sc = self.scale
        x, y, w, h = (S(v, sc) for v in PROGRESS)
        h = max(2, h)
        self.prog = (x, y, w, h)
        track = self.Image.new("RGBA", (w, h), (58, 46, 68, 255))
        fill = self.Image.new("RGBA", (w, h), RED + (255,))
        cut = self.ImageDraw.Draw(track), self.ImageDraw.Draw(fill)
        for b in BLOCKS[1:]:
            bx = int(w * b["t0"] / DURATION)
            for dd in cut:
                dd.rectangle((bx - S(3, sc), 0, bx + S(3, sc), h), fill=(0, 0, 0, 0))
        self.prog_track, self.prog_fill = track, fill

    # -- per frame -------------------------------------------------------------------------------
    def _shot_frame(self, i, t, w, h):
        s = self.shots[i]
        if s["src"].endswith(".mp4"):
            if i not in self.clips:
                start = max(0.0, s["at"] - (XFADE / 2 + 0.1))
                self.clips[i] = Clip(self.ffmpeg, os.path.join(DOCS, s["src"]), start, w, h)
            return self.clips[i].get(max(0.0, s["at"] + (t - s["t0"])))
        dur = s["t1"] - s["t0"]
        tq = math.floor((t - s["t0"]) * STILL_HZ + 1e-6) / STILL_HZ    # zoom steps at the clips' rate
        u = min(1.0, max(0.0, tq / dur))
        z = s["zoom"][0] + (s["zoom"][1] - s["zoom"][0]) * u
        return self._still(s["src"]).frame(w, h, z, s["focus"])

    def _close_clips(self, t):
        for i in list(self.clips):
            if self.shots[i]["t1"] + XFADE < t:
                self.clips.pop(i).close()

    def _weights(self, t):
        """[(shot index, weight)] of the picture at t (two shots during a cross-fade)."""
        i = max(0, bisect.bisect_right(self.shot_t0, t) - 1)
        s = self.shots[i]
        if i > 0 and t < s["t0"] + XFADE / 2:
            w = 0.5 + (t - s["t0"]) / XFADE
            return [(i - 1, 1 - w), (i, w)]
        if i < len(self.shots) - 1 and t > s["t1"] - XFADE / 2:
            w = 0.5 - (s["t1"] - t) / XFADE
            return [(i, 1 - w), (i + 1, w)]
        return [(i, 1.0)]

    def _picture(self, t, w, h):
        parts = self._weights(t)
        img = self._shot_frame(parts[0][0], t, w, h)
        if len(parts) == 2:
            img = self.Image.blend(img, self._shot_frame(parts[1][0], t, w, h), parts[1][1])
        return img, parts

    def _cards_layer(self, b, t):
        events = b["_events"]
        j = bisect.bisect_right([e[0] for e in events], t) - 1
        if j < 0:
            return None
        te, cur = events[j]
        prev = events[j - 1][1] if j > 0 else {}
        moves = any(k in prev and prev[k] != cur[k] for k in cur) or any(k not in cur for k in prev)
        u = ease((t - te) / 0.35)                              # the stack moves up ...
        v = ease((t - te - (0.3 if moves else 0.0)) / 0.4)    # ... then the new card comes in
        sc = self.scale
        top = b["_cards_top"]
        area_h = b["_area"]
        layer = self.Image.new("RGBA", (self.side[2], area_h), (0, 0, 0, 0))
        shift = 0
        for k in cur:
            if k in prev:
                shift = prev[k] - cur[k]
                break
        for k in sorted(set(prev) | set(cur)):
            c = b["cards"][k]
            if k in cur and k in prev:
                y, a = prev[k] + (cur[k] - prev[k]) * u, 1.0
            elif k in cur:
                y, a = cur[k] + S(30, sc) * (1 - v), v
            else:
                y, a = prev[k] - shift * u, 1 - u
            if a <= 0.001:
                continue
            img = c.get("_img")
            if img is None:
                img = [im for tt, im in c["_imgs"] if tt <= t + 1e-9][-1:] or [c["_imgs"][0][1]]
                img = img[-1]
            img = with_alpha(img, a)
            y = int(round(y))
            y0, y1 = max(0, y), min(area_h, y + img.size[1])
            if y1 <= y0:
                continue
            layer.alpha_composite(img.crop((0, y0 - y, img.size[0], y1 - y)), (0, y0))
        return layer, top

    def frame(self, t):
        Image = self.Image
        W, H = self.W, self.H
        canvas = Image.new("RGB", (W, H), BG)
        # layout: full-frame picture at the start, then shrinking into the left panel
        s0, s1 = OPENING["shrink"]
        m = ease((t - s0) / (s1 - s0))
        vx, vy, vw, vh = self.vis
        rx, ry = int(round(vx * m)), int(round(vy * m))
        rw, rh = int(round(W + (vw - W) * m)), int(round(H + (vh - H) * m))
        pic, parts = self._picture(t, rw, rh)
        if m >= 1.0:
            canvas.paste(pic, (rx, ry), self.vis_mask)
        elif m > 0.0:
            canvas.paste(pic, (rx, ry), rounded_mask((rw, rh), max(1, int(S(12, self.scale) * m))))
        else:
            canvas.paste(pic, (0, 0))
        same = len(parts) == 2 and self.shots[parts[0][0]]["badge"] == self.shots[parts[1][0]]["badge"]
        for i, w in parts[-1:] if same else parts:
            badge = self.badges[i]
            if badge is not None:
                pad = S(20, self.scale)
                paste_rgba(canvas, badge, (rx + rw - badge.size[0] - pad, ry + rh - badge.size[1] - pad),
                           1.0 if same else dip(w))
        if m > 0:
            self._chrome(canvas, t, m, parts)
        # the opening title
        ta = 1.0 - min(1.0, max(0.0, (t - (OPENING["until"] - 0.8)) / 0.8))
        if ta > 0:
            paste_rgba(canvas, self.opening, (0, 0), ta)
        # the closing card
        fw = min(1.0, max(0.0, (t - (FINAL["t0"] - 0.4)) / 0.8))
        if fw > 0:
            canvas = Image.blend(canvas, self.final, fw) if fw < 1 else self.final.copy()
        # subtitles
        g = max(1.0 - m, fw)
        if g > 0:
            paste_rgba(canvas, self.sub_grad, (0, H - self.sub_grad.size[1]), g)
        k = bisect.bisect_right(self.cue_t0, t) - 1
        if k >= 0 and t < self.cues[k][1]:
            _, _, _, img, y = self.cues[k]
            paste_rgba(canvas, img, (0, y))
        # fade in from / out to black
        fade = min(1.0, t / 0.5, (DURATION - t) / 0.7)
        if fade < 1.0:
            canvas = Image.blend(Image.new("RGB", (W, H), (0, 0, 0)), canvas, max(0.0, fade))
        self._close_clips(t)
        return canvas

    def _chrome(self, canvas, t, m, parts):
        sc = self.scale
        sx, sy, sw, sh = self.side
        fw = min(1.0, max(0.0, (t - (FINAL["t0"] - 0.4)) / 0.8))
        paste_rgba(canvas, self.logo, (sx, sy), m)
        d = self.ImageDraw.Draw(canvas)
        d.text((sx + self.logo.size[0] + S(14, sc), sy + self.logo.size[1] / 2 + S(1, sc)), "ReSense",
               font=self.fonts.get("bold", 30), fill=tuple(int(BG[i] + (WHITE[i] - BG[i]) * m) for i in range(3)),
               anchor="lm")
        n = max(0, bisect.bisect_right([b["t0"] for b in BLOCKS], t) - 1)
        b = BLOCKS[n]
        ba = m * min(1.0, (t - b["t0"]) / 0.35 if n > 0 else 1.0, (b["t1"] - t) / 0.35 if n < len(BLOCKS) - 1 else 1.0)
        ba = max(0.0, ba)
        paste_rgba(canvas, b["_header"], (sx, sy), ba)
        got = self._cards_layer(b, t)
        if got:
            layer, top = got
            paste_rgba(canvas, layer, (sx, sy + top), ba)
        # source line of the picture
        for i, w in parts:
            paste_rgba(canvas, self.notes[i], (sx, sy + sh - self.notes[i].size[1]), m * dip(w))
        # progress
        x, y, w, h = self.prog
        pa = m * (1 - fw)
        if pa > 0:
            bar = self.prog_track.copy()
            fill_w = int(w * min(1.0, t / DURATION))
            if fill_w > 0:
                bar.paste(self.prog_fill.crop((0, 0, fill_w, h)), (0, 0), self.prog_track.crop((0, 0, fill_w, h)))
            paste_rgba(canvas, bar, (x, y), pa)

    def close(self):
        for c in self.clips.values():
            c.close()
        self.clips.clear()


# ================================================================ narration (optional TTS)

VOICE_MAX_TEMPO = 1.18                                  # at most this much faster than the voice's pace


def cue_slots():
    """[(t0, room, spoken text)]: the voice may run from the cue start until the next cue starts
    (or a little past its block's end), minus a breath."""
    subs = [(c[0], c[1], spoken(c)) for c in all_subs()]
    ends = sorted(b["t1"] for b in BLOCKS)
    out = []
    for i, (t0, t1, say) in enumerate(subs):
        nxt = subs[i + 1][0] if i + 1 < len(subs) else DURATION
        block_end = min(e for e in ends if e >= t1)
        out.append((t0, min(nxt, block_end + 0.6, DURATION - 0.3) - t0 - 0.15, say))
    return out


def synthesize(voice_path, out_wav, length_scale=1.0, log=sys.stderr):
    """Read every cue with a Piper voice into one mono WAV of DURATION seconds; a line longer than
    its slot is re-read faster (up to VOICE_MAX_TEMPO). Returns [(t0, seconds, room)]."""
    import wave

    import numpy as np
    from piper import PiperVoice
    from piper.config import SynthesisConfig

    voice = PiperVoice.load(voice_path)
    rate = voice.config.sample_rate

    def read(say, scale):
        chunks = list(voice.synthesize(say, syn_config=SynthesisConfig(length_scale=scale)))
        return np.concatenate([c.audio_float_array for c in chunks]).astype(np.float32)

    track = np.zeros(int(DURATION * rate) + rate, dtype=np.float32)
    report = []
    for t0, room, say in cue_slots():
        audio = read(say, length_scale)
        dur = len(audio) / rate
        if dur > room:
            tempo = min(VOICE_MAX_TEMPO, dur / room * 1.02)
            audio = read(say, length_scale / tempo)
            dur = len(audio) / rate
        if dur > room + 0.05:
            print(f"  voice at {t0:.1f} s: {dur:.2f} s > room {room:.2f} s", file=log)
        a = int(round((t0 + 0.05) * rate))
        seg = audio[: max(0, len(track) - a)]
        track[a:a + len(seg)] += seg
        report.append((t0, dur, room))
    track = track[: int(DURATION * rate)]
    peak = float(np.max(np.abs(track))) or 1.0
    track = np.clip(track / peak * 0.89, -1.0, 1.0)                  # -1 dBFS peak
    with wave.open(out_wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((track * 32767).astype("<i2").tobytes())
    return report


# ================================================================ outputs

def write_srt(path, renderer, span=None):
    start, end = span or (0.0, DURATION)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        n = 0
        for t0, t1, lines, _, _ in renderer.cues:
            if t1 <= start or t0 >= end:
                continue
            n += 1
            f.write(f"{n}\n{fmt_srt_time(max(t0, start) - start)} --> {fmt_srt_time(min(t1, end) - start)}\n"
                    + "\n".join(lines) + "\n\n")


def write_chapters(path, span=None, voice=None):
    start, end = span or (0.0, DURATION)
    esc = re.compile(r"([=;#\\\n])")
    with open(path, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")
        f.write("title=" + esc.sub(r"\\\1", "ReSense — обзор решения (кейс 05, ЛЦТ 2026)") + "\n")
        comment = (f"голос — синтез речи Piper ({voice}); субтитры: resense_overview.ru.srt" if voice
                   else "без звука; субтитры: resense_overview.ru.srt")
        f.write("comment=" + esc.sub(r"\\\1", comment) + "\n")
        for b in BLOCKS:
            if b["t1"] <= start or b["t0"] >= end:
                continue
            f.write("[CHAPTER]\nTIMEBASE=1/1000\n")
            f.write(f"START={round((max(b['t0'], start) - start) * 1000)}\n"
                    f"END={round((min(b['t1'], end) - start) * 1000)}\n")
            f.write("title=" + esc.sub(r"\\\1", b["name"]) + "\n")


def x264_zones(first, last):
    """x264 ``zones`` of the shots with a bitrate factor, in frames of the encoded part."""
    zones = []
    for s in all_shots():
        if s["bits"] is None:
            continue
        f0 = max(first, int(round(s["t0"] * FPS))) - first
        f1 = min(last, int(round(s["t1"] * FPS))) - 1 - first
        if f1 >= f0:
            zones.append(f"{f0},{f1},b={s['bits']:g}")
    return "/".join(zones)


def encode(renderer, out, ffmpeg, crf, preset, span=None, audio=None, voice_name=None):
    W, H = renderer.W, renderer.H
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        meta = os.path.join(tmp, "chapters.txt")
        write_chapters(meta, span, voice_name if audio else None)
        t_start, t_end = span or (0.0, DURATION)
        audio_in = (["-ss", f"{t_start:.3f}", "-t", f"{t_end - t_start:.3f}", "-i", audio] if audio else [])
        audio_out = (["-map", "2:a", "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "1",
                      "-af", "loudnorm=I=-16:TP=-1.5:LRA=11"] if audio else ["-an"])
        cmd = [ffmpeg, "-v", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-f", "ffmetadata", "-i", meta, *audio_in,
               "-map", "0:v", "-map_metadata", "1", "-map_chapters", "1", *audio_out,
               "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
               "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-g", str(FPS * 5),
               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
               "-color_range", "tv", "-movflags", "+faststart", out]
        first, last = (int(round(v * FPS)) for v in (span or (0.0, DURATION)))
        zones = x264_zones(first, last)
        if zones:
            cmd[cmd.index("-movflags"):cmd.index("-movflags")] = ["-x264-params", "zones=" + zones]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for i in range(first, last):
                proc.stdin.write(renderer.frame(i / FPS).tobytes())
                if i % (FPS * 10) == 0:
                    print(f"  {i / FPS:6.1f} s / {DURATION:.0f} s", file=sys.stderr, flush=True)
        finally:
            proc.stdin.close()
            renderer.close()
        if proc.wait() != 0:
            sys.exit("ffmpeg failed")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, OUT_MP4))
    ap.add_argument("--srt", default=os.path.join(ROOT, OUT_SRT))
    ap.add_argument("--size", default="1920x1080", help="WxH, 16:9 (default 1920x1080)")
    ap.add_argument("--crf", type=int, default=CRF)
    ap.add_argument("--preset", default="slow")
    ap.add_argument("--ffmpeg", help="ffmpeg binary (default: imageio-ffmpeg's, then PATH)")
    ap.add_argument("--check", action="store_true", help="validate the table (and layout) and exit")
    ap.add_argument("--frames", help="comma-separated times (s): write these frames as PNG, no video")
    ap.add_argument("--frames-dir", default="overview_frames")
    ap.add_argument("--span", help="T0,T1: encode only this part (s), for trying settings")
    ap.add_argument("--voice", help="Piper voice model (.onnx) for a synthetic narration; none = silent")
    ap.add_argument("--voice-scale", type=float, default=1.0, help="Piper length_scale (< 1 = faster)")
    ap.add_argument("--voice-wav", help="also keep the narration WAV here")
    ap.add_argument("--voice-only", action="store_true", help="only synthesize the narration and report")
    args = ap.parse_args(argv)

    bad = check_table()
    if bad:
        sys.exit("table problems:\n  " + "\n  ".join(bad))
    W, H = (int(v) for v in args.size.lower().split("x"))
    if min(W, H) <= 0 or W % 2 or H % 2 or abs(W / H - 16 / 9) > 0.01:
        sys.exit("--size must be 16:9")
    span = tuple(float(v) for v in args.span.split(",")) if args.span else None
    if span and (len(span) != 2 or not 0 <= span[0] < span[1] <= DURATION):
        ap.error(f"--span must satisfy 0 <= T0 < T1 <= {DURATION:g}")
    if span:
        span = tuple(round(v * FPS) / FPS for v in span)
        if span[0] == span[1]:
            ap.error("--span must contain at least one video frame")
    ffmpeg = None if args.check else find_ffmpeg(args.ffmpeg)
    r = Renderer((W, H), ffmpeg)            # also lays out every card and subtitle (raises if one overflows)
    if args.check:
        print(f"ok: {len(BLOCKS)} blocks, {len(all_shots())} shots, {len(r.cues)} subtitles, "
              f"{sum(len(b['cards']) for b in BLOCKS)} cards, {DURATION:.0f} s")
        return
    if args.frames:
        os.makedirs(args.frames_dir, exist_ok=True)
        for t in sorted(float(v) for v in args.frames.split(",")):
            path = os.path.join(args.frames_dir, f"frame_{t:07.2f}.png")
            r.frame(t).save(path)
            print(path)
        r.close()
        return
    audio = None
    if args.voice:
        wav = args.voice_wav or os.path.join(tempfile.mkdtemp(prefix="resense_voice_"), "narration.wav")
        report = synthesize(args.voice, wav, args.voice_scale)
        long = [(t0, d, room) for t0, d, room in report if d > room + 0.05]
        print(f"narration: {len(report)} cues, {sum(d for _, d, _ in report):.1f} s of speech, "
              f"{len(long)} longer than their slot -> {wav}")
        if args.voice_only:
            for t0, d, room in report:
                print(f"  {t0:6.1f} s  voice {d:5.2f} s  room {room:5.2f} s"
                      + ("  LONG" if d > room + 0.05 else ""))
            r.close()
            return
        audio = wav
    write_srt(args.srt, r, span)
    encode(r, args.out, ffmpeg, args.crf, args.preset, span, audio,
           os.path.basename(args.voice).replace(".onnx", "") if args.voice else None)
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB) and {args.srt}")


if __name__ == "__main__":
    main()
