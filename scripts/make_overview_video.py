#!/usr/bin/env python3
"""Build the silent, captioned 2:50 overview video ``docs/video/resense_overview.mp4``.

The cut follows the shot list and the narration of docs/PRESENTATION.md «Сценарий видео (2–3 мин)»:
seven blocks (проблема → идея → алгоритм → демонстрация → объекты организаторов → цифры → что
дальше) made only from the repository's own material: the silent clips in ``docs/video/``, the
renders in ``docs/img/``, the web-UI captures in ``docs/images/`` and pages of the deck
``docs/presentation/ReSense_LCT2026.pdf``. Nothing is fetched from the network.

On screen: the picture on the left; on the right the block's name and cards with its key numbers
(every number from the script or docs/EXPERIMENTS.md "Current results", marked **реальные данные**,
**наша синтетика** or **синтетика организаторов** as the script does), with the source file of the
picture under them; the narration as burned-in Russian subtitles at the bottom (at most two lines).
The same subtitles, with the same timings and line breaks, are written to
``docs/video/resense_overview.ru.srt``: a voice-over can be recorded against them and players can
show them as soft subtitles. The MP4 has no audio track (H.264 yuv420p, 25 fps, faststart, chapter
marks per block).

    python scripts/make_overview_video.py                     # 1920x1080 -> docs/video/ (mp4 + srt)
    python scripts/make_overview_video.py --check             # validate the table and exit
    python scripts/make_overview_video.py --frames 3,60,100 --frames-dir /tmp/f   # PNGs only
    python scripts/make_overview_video.py --size 1280x720 --out /tmp/o.mp4 --srt /tmp/o.srt
    python scripts/make_overview_video.py --span 93,111 --out /tmp/part.mp4 --srt /tmp/part.srt

Everything that decides the cut (sources and in-points, timings, card texts, subtitles) is the
``BLOCKS`` table below plus ``OPENING`` / ``FINAL``; change it there and re-run. Needs Pillow,
PyMuPDF (``pymupdf``; or ``pdftoppm`` on PATH) for the deck pages and an ffmpeg with libx264
(``--ffmpeg``, else the binary of ``imageio-ffmpeg``, else ``ffmpeg`` on PATH):

    pip install Pillow pymupdf imageio-ffmpeg

Not part of the runtime image. The fonts are the dashboard's Moscow Sans (web/assets/fonts/).
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
DURATION = 170.0                                        # 2:50, as the script
FPS = 25
XFADE = 0.4                                             # cross-fade between shots, s
STILL_HZ = 10                                           # a zooming still changes this often (as the clips)
CRF = 23                                                # x264 quality (shots with ``bits`` scale it)
REPO_LINE = "github.com/pmixay/ReSense · релиз v1.0.0"   # the final release tag (docs/CAPTAIN.md §5, release.yml)

REAL, OURS, ORG = "real", "ours", "org"                 # how a number was measured (the script's marks)
DEMO = "демо-данные интерфейса"                         # badge on the web-UI captures of the built-in demo
TAGS = {
    REAL: ("реальные данные", "#E2F3E8", "#07703A"),
    OURS: ("наша синтетика", "#FFF0D0", "#8A5200"),
    ORG: ("синтетика организаторов", "#EFE3FA", "#5A2787"),
}


def shot(t0, t1, src, at=0.0, zoom=(1.0, 1.0), focus=(0.5, 0.5), note="", badge=None, bits=None):
    """A picture on the left from ``t0`` to ``t1`` (s): a clip from its second ``at``, a still
    (``zoom`` from/to about ``focus``, fractions of the picture) or ``deck:N``. ``note`` is the
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


# ---- the cut: docs/PRESENTATION.md «Раскадровка» and «Текст за кадром» ------------------------
# Numbers: docs/EXPERIMENTS.md "Current results" (24.09) and docs/P4_AUDIT.md, as in the script.
# Subtitles are the narration with the numbers in digits (the voice reads them as words).
BLOCKS = [
    {"name": "Проблема", "t0": 0.0, "t1": 18.0,
     "shots": [
         shot(0.0, 18.0, "img/hero_ride_clean.png", zoom=(1.0, 1.15), focus=(0.505, 0.45), bits=0.35,
              note="img/hero_ride_clean.png · поездка организаторов, реальные данные"),
     ],
     "cards": [
         num(8.4, "13 км", "20-минутная поездка организаторов", REAL),
         text(12.4, "препятствий для обучения нейросети в данных почти нет"),
     ],
     "subs": [
         (0.6, 4.6, "Поезд без машиниста должен сам понять, свободен ли путь впереди."),
         (4.8, 8.4, "Тормозной путь на 80 км/ч — около 200 метров."),
         (8.6, 12.4, "А тоннель метро однообразен и почти всегда пуст:"),
         (12.4, 17.6, "реальных препятствий, на которых можно научить нейросеть, в данных почти нет."),
     ]},
    {"name": "Идея", "t0": 18.0, "t1": 38.0,
     "shots": [
         shot(18.0, 26.0, "video/doubleT_obstacle_offline.mp4", at=0.0, bits=0.5,
              note="video/doubleT_obstacle_offline.mp4 · 0:00–0:08 · вид сверху и сбоку, "
                   "ось пути зелёным"),
         shot(26.0, 38.0, "img/hero_ride.png",
              note="img/hero_ride.png · поездка 13 км, кадр 220, реальные данные"),
     ],
     "cards": [
         text(18.4, "описываем нормальный тоннель, а не объекты"),
         text(22.0, "ось пути — по рельсам, дальше — по стенам и колоннам"),
         num(30.6, "2,1 × 3,0 м", "габарит поезда вдоль оси пути"),
     ],
     "subs": [
         (18.4, 21.8, "Поэтому мы описываем не объекты, а нормальный тоннель."),
         (22.0, 25.8, "В каждом кадре лидар калибруется по рельсам и строит ось пути,"),
         (25.8, 30.4, "а изгиб продлевает по стенам и колоннам — туда, где рельсов уже не видно."),
         (30.6, 33.0, "Вдоль оси — габарит поезда."),
         (33.2, 37.6, "Всё, что в него попало и не является путём, — препятствие."),
     ]},
    {"name": "Алгоритм", "t0": 38.0, "t1": 56.0,
     "shots": [
         shot(38.0, 48.0, "deck:8", note="презентация, слайд 8 · пять шагов на кадр"),
         shot(48.0, 56.0, "img/doubleT_obstacle_0024_v062.png",
              note="img/doubleT_obstacle_0024_v062.png · doubleT_obstacle, кадр 24, реальные данные"),
     ],
     "cards": [
         text(38.4, "5 шагов на кадр: калибровка, модель пути, габарит, кластеры, подтверждение 0,5 с"),
         text(44.6, "выход: GO · CAUTION · STOP · FAULT и свободная дистанция"),
         num(50.4, "42–64 мс", "на кадр · одно ядро CPU · без GPU", REAL),
     ],
     "subs": [
         (38.4, 44.4, "Пять шагов на кадр: калибровка крепления, модель пути, габарит, кластеры, "
                      "подтверждение за полсекунды."),
         (44.6, 50.2, "На выходе — GO, CAUTION, STOP или FAULT и расстояние, до которого путь "
                      "проверенно свободен."),
         (50.4, 55.6, "42–64 миллисекунды на кадр на одном ядре, без видеокарты."),
     ]},
    {"name": "Демонстрация", "t0": 56.0, "t1": 93.0,
     "shots": [
         shot(56.0, 62.0, "video/docker_chain_rviz.mp4", at=0.0,
              note="video/docker_chain_rviz.mp4 · 0:00–0:06 · docker run, до входа FAULT"),
         shot(62.0, 68.0, "video/docker_chain_rviz.mp4", at=12.0,
              note="video/docker_chain_rviz.mp4 · 0:12–0:18 · bag play из другого контейнера"),
         shot(68.0, 74.0, "video/docker_chain_rviz.mp4", at=24.0,
              note="video/docker_chain_rviz.mp4 · 0:24–0:30 · /resense/decision: STOP"),
         shot(74.0, 81.0, "video/doubleT_obstacle_cab.mp4", at=0.0, bits=0.35,
              note="video/doubleT_obstacle_cab.mp4 · 0:00–0:07 · человек, реальные данные"),
         shot(81.0, 87.0, "video/doubleT_obstacle_cab.mp4", at=8.0, bits=0.35,
              note="video/doubleT_obstacle_cab.mp4 · 0:08–0:14 · предмет на рельсе"),
         shot(87.0, 93.0, "images/dashboard-cab-real.png",
              note="images/dashboard-cab-real.png · веб-интерфейс по статусу узла из Docker"),
     ],
     "cards": [
         steps(56.4, ["docker build", "docker run", "ros2 bag play", "/resense/decision"],
               [(56.4, 1), (62.9, 2), (68.0, 3)]),
         num(68.0, "STOP", "человек на пути: 55,5–56,6 м по кадрам, doubleT_obstacle", REAL),
         num(74.0, "58 из 61", "кадров с человеком — тревога через 0,3 с", REAL),
         num(81.2, "124 из 126", "кадров с предметом на рельсе", REAL),
     ],
     "subs": [
         (56.4, 58.4, "Вот цепочка жюри как есть."),
         (58.6, 62.8, "Docker run — узел запущен и, пока данных нет, честно говорит FAULT."),
         (62.9, 67.9, "Из другого контейнера, от обычного пользователя, — ros2 bag play с записью "
                      "организаторов."),
         (68.0, 73.8, "Вот поезд, вот лидар, а вот человек, который переходит путь: STOP, 55,8 метра."),
         (74.0, 77.6, "Тревога — через 0,3 секунды после входа в габарит;"),
         (77.6, 81.0, "человек найден в 58 кадрах из 61."),
         (81.2, 86.8, "Он уходит — на рельсе остаётся предмет, и его алгоритм тоже держит:"),
         (86.8, 90.6, "124 кадра из 126."),
     ]},
    {"name": "Объекты организаторов", "t0": 93.0, "t1": 123.0,
     "shots": [
         shot(93.0, 111.0, "video/fake_objects_cab.mp4", at=0.0, bits=0.25,
              note="video/fake_objects_cab.mp4 · 0:00–0:18 · ящик 2 × 2 м, 98 → 43 м"),
         shot(111.0, 123.0, "deck:13", note="презентация, слайд 13 · объекты организаторов"),
     ],
     "cards": [
         text(93.4, "cloud_with_fake_obj: объекты вставили сами организаторы", ORG),
         num(98.4, "1,5 → 7,7 м/с", "поезд разгоняется на этом отрезке"),
         num(101.4, "98 м", "ящик 2 × 2 м: STOP с первого появления", ORG),
         num(111.0, "5 из 8", "объектов в габарите — STOP", ORG),
     ],
     "subs": [
         (93.4, 98.4, "Главная внешняя проверка — препятствия, которые вставили в запись сами "
                      "организаторы;"),
         (98.4, 101.2, "поезд едет к ним до 20 метров в секунду."),
         (101.4, 106.2, "Ящик 2 × 2 метра — STOP с первого появления, с 98 метров;"),
         (106.2, 109.4, "доска поперёк рельсов — с 82."),
         (109.8, 115.6, "Кубы по 30 сантиметров — только с 34–43 метров: вдали от них 2–4 точки."),
         (115.8, 122.4, "Висящий предмет в 5 сантиметров и ящик у края габарита мы пропускаем — "
                        "и говорим об этом прямо."),
     ]},
    {"name": "Цифры", "t0": 123.0, "t1": 145.0,
     "shots": [
         shot(123.0, 134.0, "deck:11", note="презентация, слайд 11 · результаты"),
         shot(134.0, 145.0, "deck:12", note="презентация, слайд 12 · дальность"),
     ],
     "cards": [
         num(123.4, "13 759", "реальных кадров прогнаны целиком", REAL),
         num(127.4, "3,5 на км", "ложного события в 20-минутной поездке (46 за 13 км)", REAL),
         num(131.4, "148 м", "человек на подходе по прямой; в 5 парах 150 → 154 м, если ставить "
                            "по рельсам", OURS),
         num(141.2, "~210 м", "предел отражений в тоннеле", REAL),
     ],
     "subs": [
         (123.4, 127.4, "Все 13 759 реальных кадров прогнаны целиком:"),
         (127.4, 131.0, "3,5 ложного события на километр."),
         (131.4, 136.0, "Человек на подходе по прямой подтверждён на 148 метрах;"),
         (136.0, 141.0, "в парных подходах — на 150, а если ставить его по рельсам — на 154."),
         (141.2, 144.8, "Дальше 210 метров в тоннеле отражений нет."),
     ]},
    {"name": "Что дальше", "t0": 145.0, "t1": 170.0,
     "shots": [
         shot(145.0, 153.0, "images/dashboard-stop.png",
              note="images/dashboard-stop.png · веб-интерфейс, встроенное демо (не измерение)",
              badge=DEMO),
         shot(153.0, 162.0, "images/dashboard-clear.png",
              note="images/dashboard-clear.png · веб-интерфейс, встроенное демо (не измерение)",
              badge=DEMO),
     ],
     "cards": [
         text(145.4, "дальше: мелкие объекты — раньше, скорость — от одометрии"),
         num(149.2, "0,07 м/с", "ошибка своей скорости по лидару; раннего STOP не дала — это опция"),
         num(156.6, "−38…−57 %", "времени детектора с ядрами на C++, выход тот же"),
     ],
     "subs": [
         (145.4, 149.0, "Дальше — мелкие объекты раньше и скорость от одометрии."),
         (149.2, 153.2, "Свою скорость по лидару мы уже меряем с ошибкой 0,07 м/с,"),
         (153.2, 156.4, "но раннего STOP она не дала, поэтому это опция."),
         (156.6, 161.4, "Ядра на C++ ускорили детектор на 38–57 % с тем же результатом."),
         (161.8, 166.2, "Docker build, docker run, ros2 bag play — и поезд видит путь."),
         (166.4, 169.4, "ReSense, команда «Молоток»."),
     ]},
]
# the title over the first shot (full frame), then the picture shrinks into the layout
OPENING = {"until": 7.4, "shrink": (7.4, 8.4),
           "title": "ReSense",
           "line1": "команда «Молоток» · кейс 05, ЛЦТ 2026",
           "line2": "обнаружение посторонних объектов в тоннеле метро по данным 3D-лидара"}
# the closing card (full frame) over the blurred deck page 10, from t0 to the end
FINAL = {"t0": 162.0, "src": "deck:10",
         "title": "ReSense",
         "line1": "команда «Молоток» · кейс 05, ЛЦТ 2026",
         "chain": "docker build → docker run → ros2 bag play → /resense/decision",
         "repo": REPO_LINE}

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
        for t0, t1, line in b["subs"]:
            if not (b["t0"] <= t0 < t1 <= b["t1"]):
                bad.append(f"subtitle at {t0} outside block {b['name']}")
            if t0 < prev_end - 1e-9:
                bad.append(f"subtitle at {t0} overlaps the previous one")
            if t1 - t0 < 1.0:
                bad.append(f"subtitle at {t0} shorter than 1 s")
            if len(line) / (t1 - t0) > 21.0:
                bad.append(f"subtitle at {t0}: {len(line) / (t1 - t0):.1f} characters/s (> 21)")
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
            if src.startswith("deck:"):
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
        for t0, t1, line in all_subs():
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
        bgimg = render_deck_page(int(FINAL["src"][5:]), 1920).resize((self.W, self.H))
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


# ================================================================ outputs

def write_srt(path, renderer):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for n, (t0, t1, lines, _, _) in enumerate(renderer.cues, 1):
            f.write(f"{n}\n{fmt_srt_time(t0)} --> {fmt_srt_time(t1)}\n" + "\n".join(lines) + "\n\n")


def write_chapters(path):
    esc = re.compile(r"([=;#\\\n])")
    with open(path, "w", encoding="utf-8") as f:
        f.write(";FFMETADATA1\n")
        f.write("title=" + esc.sub(r"\\\1", "ReSense — обзор решения (кейс 05, ЛЦТ 2026)") + "\n")
        f.write("comment=" + esc.sub(r"\\\1", "без звука; субтитры: resense_overview.ru.srt") + "\n")
        for b in BLOCKS:
            f.write("[CHAPTER]\nTIMEBASE=1/1000\n")
            f.write(f"START={int(b['t0'] * 1000)}\nEND={int(b['t1'] * 1000)}\n")
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


def encode(renderer, out, ffmpeg, crf, preset, span=None):
    W, H = renderer.W, renderer.H
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        meta = os.path.join(tmp, "chapters.txt")
        write_chapters(meta)
        cmd = [ffmpeg, "-v", "error", "-y",
               "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
               "-f", "ffmetadata", "-i", meta,
               "-map", "0:v", "-map_metadata", "1", "-map_chapters", "1",
               "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
               "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-g", str(FPS * 5),
               "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
               "-color_range", "tv", "-movflags", "+faststart", "-an", out]
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
    args = ap.parse_args(argv)

    bad = check_table()
    if bad:
        sys.exit("table problems:\n  " + "\n  ".join(bad))
    W, H = (int(v) for v in args.size.lower().split("x"))
    if abs(W / H - 16 / 9) > 0.01:
        sys.exit("--size must be 16:9")
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
    write_srt(args.srt, r)
    span = tuple(float(v) for v in args.span.split(",")) if args.span else None
    encode(r, args.out, ffmpeg, args.crf, args.preset, span)
    print(f"wrote {args.out} ({os.path.getsize(args.out) / 1e6:.1f} MB) and {args.srt}")


if __name__ == "__main__":
    main()
