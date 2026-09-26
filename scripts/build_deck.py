#!/usr/bin/env python3
"""Fill the organizers' presentation template with the ReSense deck.

The template (37 slides, Montserrat, "Лидеры цифровой трансформации 2026") is exported from
Google Slides:

    curl -L -o template.pptx \\
      https://docs.google.com/presentation/d/17ciElVAWgeuPLiFHw7y5HMaAXmTo7g16/export/pptx
    python scripts/build_deck.py --template template.pptx --out docs/presentation/ReSense_LCT2026.pptx

Slides 7-11 (title, team, team cards, history, solution in short) keep their design and
structure as the organizers require; the solution slides use the template's own layouts
(12-29). Every number is taken from ``N`` below, which is copied from docs/EXPERIMENTS.md
"Current results" and docs/P4_AUDIT.md; the pictures are made by ``scripts/hero_view.py`` and
``resense run --render`` (``docs/img/``) and by the web UI's gallery (``docs/images/``; paths in ``IMG``).

The PDF next to the deck is LibreOffice's export (Impress and the Montserrat fonts installed):

    soffice --headless --convert-to pdf --outdir docs/presentation docs/presentation/ReSense_LCT2026.pptx

The team's personal data (names, Telegram nicknames, place of study, city, photos) are not in the
public repository: without ``--team`` they stay ``<...>`` placeholders. The captain keeps them in a
git-ignored folder and builds the full deck with

    python scripts/build_deck.py --template template.pptx --team docs/presentation/private/team.json \
      --out docs/presentation/private/ReSense_LCT2026.pptx

``team.json`` holds the keys of ``TEAM`` below; photo paths are relative to the JSON file. A
private build requires all four card photos and rejects placeholder text.

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

# ---- every number on the slides (docs/EXPERIMENTS.md "Current results", §0, §2d, §2e, §3, §9;
# docs/P4_AUDIT.md; docs/ARCHITECTURE.md "Native kernels", "GPU: evaluated, not used") ---------
N = {
    "frames": "13 759",
    "person_hits": "58 из 61", "person_first": "0,3 с", "person_err": "0,23 м",
    "object_hits": "125 из 126", "object_before": "2",
    "ride_events": "45", "ride_per_km": "3,5", "ride_km": "13",
    "empty_events": "13",
    "first_person": "148", "sustained_person": "149", "band_person": "115", "speed_person": "167",
    # the same straight approaches with the person anchored on the near rails (set F round 4, 5 pairs;
    # 150 m in the same pairs with the legacy placement) [synthetic, P4_AUDIT "Paired straight-track"]
    "anchored_person": "154", "anchored_legacy": "150",
    # detector per frame on one core with the C++ kernels (the re-judgement of 26.09, idle 4-core machine: 22.7–30.7 ms
    # mean, p95 32.8–42.1 ms on set O and the 120° / 360° recordings; the numpy path of 23.09 was 42–64 / 78 ms)
    "latency": "23–31 мс", "p95": "42 мс",
    "ros_p95": "58–81 мс",                   # decode + detect through ROS in Docker, 120° / 360°, 10 fps (26.09)
    "native_cut": "38–57 %",                 # optional C++ kernels: detector time, identical output
    "gpu_gain": "30–45 мс",                  # the GPU study's upper bound per 360° frame against numpy
    "speed_err": "0,07 м/с",                 # the opt-in LiDAR-only train speed, median error (0.06–0.08)
    "tests": "587",
    # the organizers' own synthetic obstacles, set O (cloud_with_fake_obj: 10 objects, 1 510 frames,
    # the train drives up to them at 1.4–20 m/s, no speed given) [organizers' synthetic, P4_AUDIT]
    "fake_frames": "1 510", "fake_stop": "8 из 8", "fake_box": "98", "fake_plank": "82", "fake_cubes": "43–53",
    "fake_top_frames": "51 из 124", "fake_outside_false": "6", "fake_background": "3",
    # first confirmed detection, straight track, median over the approaches [synthetic in real frames,
    # set F round 3 = the current code, EXPERIMENTS.md §2d; the anchored person: round 4]
    "range_chart": [("человек 1,7 м · от рельсов", 154), ("человек 1,7 м", 148), ("тележка", 144),
                    ("ящик 1 м", 111), ("висящий кабель 3 см", 95), ("ящик 30 см на рельсе", 49),
                    ("предмет поперёк рельса", 46)],
    # the organizers' in-envelope objects: (name, first STOP in m, label replacing the value or None,
    # STOP held); the box at the envelope top is a STOP on every frame from 101.3 m (51 of 124, the STOP keep
    # of 26.09); the two edge objects get only 2 and 6 STOP frames at 5-10 m
    "fake_chart": [("ящик 2 × 2 м, верх габарита", 101, None, True), ("ящик 2 × 2 м в центре", 98, None, True),
                   ("доска поперёк рельсов", 82, None, True), ("куб 0,3 м на рельсе", 43, None, True),
                   ("куб 0,3 м в воздухе", 53, None, True), ("куб 0,3 м у края", 5, None, False),
                   ("ящик 2 × 2 м у края", 10, None, False), ("висящий предмет 5 см", 30, None, True)],
}

# ---- the team (slides 7-10): the team is «Молоток», ReSense is the solution; personal data below are
# placeholders here, the real values come from --team (not in git) -------------------------------
TEAM_NAME = "Молоток"
TEAM = {
    "captain": "<ФИО>", "captain_specialty": "<специальность>", "members": "4 человека",
    "formed": "<как образовалась команда>", "study": "<место учёбы / работы>",
    "study_short": "<место учёбы / работы>", "city": "<город>", "team_photo": None,
    "cards": [{"name": "<Имя Фамилия>", "nick": "<@ник>", "photo": None} for _ in range(4)],
}
ROLES = ["Капитан · ROS 2, Docker, интеграция", "Визуализация, демо, презентация",
         "Компьютерное зрение: модель пути, трекинг", "Данные, синтетика, метрики, тесты"]

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

    missing = []
    for key in ("captain", "captain_specialty", "formed", "study", "study_short", "city"):
        value = data.get(key)
        if not isinstance(value, str) or not value.strip() or "<" in value or ">" in value:
            missing.append(key)
    cards = data.get("cards")
    if not isinstance(cards, list) or len(cards) != 4:
        missing.append("cards (exactly four members)")
    else:
        for index, card in enumerate(cards, 1):
            if not isinstance(card, dict):
                missing.append(f"cards[{index}]")
                continue
            for key in ("name", "nick", "photo"):
                value = card.get(key)
                if not isinstance(value, str) or not value.strip() or "<" in value or ">" in value:
                    missing.append(f"cards[{index}].{key}")
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
    fill(shape(sl, 14), [
        f"**Капитан:** {TEAM['captain']}, {TEAM['captain_specialty']}",
        f"**Кол-во участников:** {TEAM['members']}",
        "**Краткое описание:**",
        (TEAM["formed"], {"italic": False}),
        (f"место учёбы: {TEAM['study']}", {}),
        f"**Город и регион:** {TEAM['city']}",
    ])
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
    fill(d, ["ROS 2-модуль: по потоку 3D-лидара 10 раз в секунду строит модель «нормального тоннеля» — "
             "полотно, рельсы, ось пути с кривизной по стенам, — проверяет габарит поезда 2,1 × 3,0 м и "
             "отвечает GO / CAUTION / STOP / FAULT с расстоянием до препятствия. Без обучения на объектах, "
             "без GPU, в Docker."], size=12)
    u = shape(sl, 8)
    u.height = Emu(1350000)
    fill(u, ["Описываем среду, а не объекты: крепление лидара и ось пути калибруются по рельсам в каждом "
             "кадре, кривизна — по стенам и рядам колонн, поэтому коридор осмыслен и там, где рельсов уже "
             "не видно. Вместо молчания — «проверенно свободная» дистанция. Настройка и оценка — на "
             "препятствиях, вставленных трассировкой лучей в реальные кадры."], size=12)
    if team_photo(TEAM.get("team_photo")):
        photo_into_frame(sl, 2, team_photo(TEAM["team_photo"]))


def s09_cards(sl):
    fill(shape(sl, 7), [f"КОМАНДА «{TEAM_NAME}»"])
    cards = [  # (card, photo, name, details) shape ids, left to right
        (17, 2, 15, 9), (56, 3, 58, 57), (59, 4, 61, 60), (62, 5, 64, 63), (65, 6, 67, 66)]
    for (card, photo, name, det), role, who in zip(cards, ROLES, TEAM["cards"]):
        fill(shape(sl, name), [who["name"]])
        fill(shape(sl, det), [role, who["nick"], TEAM["study_short"]], size=11)
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
        if team_photo(who.get("photo")):
            photo_into_frame(sl, photo, team_photo(who["photo"]))


def s10_history(sl):
    fill(shape(sl, 7), ["ИСТОРИЯ КОМАНДЫ"])
    fill(shape(sl, 37), ["Мы друзья и на конкурсы всегда выходим вчетвером: ROS 2 и интеграция, визуализация, "
                         "компьютерное зрение, данные и тесты. Каждый день ездим на учёбу на метро — захотелось, "
                         "чтобы поезд однажды сам видел, что у него впереди."], size=12)
    fill(shape(sl, 43), ["Метро — наша ежедневная дорога, а беспилотный поезд — задача, где ошибка стоит дорого. "
                         "Препятствий в данных почти нет, поэтому описываем «нормальный тоннель» и ловим всё, "
                         "что в него не вписывается."], size=12)
    fill(shape(sl, 40), ["Препятствий в записях почти нет — «ставили» людей и ящики в реальные кадры трассировкой "
                         "лучей лидара. Станции и стрелки давали ложные остановки — помогли ось по стенам, зона "
                         "доверия и подтверждение 0,5 с. Записи разные (два топика, 120° и 360°, наклон крепления 3°) — "
                         "узел сам находит вход и калибруется по рельсам. И всё это — параллельно с учёбой."],
         size=12)


def s11_short(sl):
    fill(shape(sl, 3), [
        "ROS 2 Humble-узел на Python (numpy / scipy / scikit-learn) и необязательные ядра на C++",
        "Вход — PointCloud2 любого из двух наборов топик / frame_id; выход — решение GO / CAUTION / STOP / "
        "FAULT, дистанция до препятствия и «проверенно свободная» дистанция, Detection3DArray, маркеры RViz, "
        "JSON-статус",
        "В каждом кадре: автокалибровка крепления → модель пути (полотно, рельсы, ось, кривизна по стенам) → "
        "габарит 2,1 × 3,0 м + низкие объекты на рельсах → кластеры → фильтры инфраструктуры → "
        "подтверждение 0,5 с",
        f"{N['latency']} на кадр (p95 ≤ {N['p95']}) на одном ядре с ядрами на C++ (они сокращают время "
        f"детектора на {N['native_cut']}, выход тот же)",
        f"Все {N['frames']} реальных кадров: человек на пути найден в {N['person_hits']} кадров, "
        f"{N['ride_per_km']} ложных события на км поездки (правила решались на ней же)",
        f"Только CPU: GPU оценили и не берём — выигрыш ≤ {N['gpu_gain']} на кадр, а контейнер с GPU не "
        "стартует без nvidia-container-toolkit",
    ], size=12, space_before=4)
    fill(shape(sl, 7), [
        "**Применение:** «взгляд вперёд» для беспилотного поезда (GoA3/4) и хозяйственных поездов; контроль "
        "габарита при обкатке линий",
        "**Развитие:** скорость поезда от одометрии — узел её уже принимает (своя оценка по лидару: ошибка "
        f"{N['speed_err']}, пока опция); опора высоты по своду тоннеля — мелкие объекты дальше 100 м; "
        "«второе мнение» на реальных препятствиях",
        "**Внедрение:** docker load → docker run → ros2 bag play; один файл параметров; стандартные "
        "сообщения ROS 2 — стыкуется с системой торможения без переделки",
    ], size=12, space_before=6)


def s_problem(sl):          # template slide 24: problem / alternatives / solution
    title_chip(sl, 2, shape(sl, 9), "ПРОБЛЕМА И ПОДХОД")
    cols = {
        26: ("Проблема", "Поезд без машиниста должен видеть путь: 100 м — хорошо, 200 — очень хорошо, 300 — "
                         "отлично. Тормозной путь на 80 км/ч — 190–250 м. Тоннель однороден и почти всегда пуст: "
                         "классов объектов для обучения нет."),
        31: ("Альтернативы", "Обученный 3D-детектор (PointPillars, CenterPoint) — нужны тысячи размеченных "
                             "препятствий, дальше 100 м — единицы процентов AP. Сравнение с картой — нужна "
                             "сантиметровая локализация и повторный проезд."),
        32: ("Наше решение", "Описать нормальный тоннель и сообщать всё, что попадает в габарит поезда "
                             "2,1 × 3,0 м. Модель пути строится заново в каждом кадре по рельсам, полотну и "
                             "стенам — без карты и без классов объектов."),
    }
    for idx, (head, text) in cols.items():
        fill(placeholder(sl, idx), [(head, {"bold": True, "size": 16, "color": PINK}),
                                    (text, {"space_before": 8})], size=13, bullet=False)


def s_data(sl):             # template slide 12: text left, picture right
    fill(placeholder(sl, 0), ["ДАННЫЕ И СЕНСОР"])
    fill(placeholder(sl, 1), [
        f"**{N['frames']} кадров** — 6 записей (2 488) и 20-минутная поездка (11 271 кадр, {N['ride_km']} км, "
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
        (26, 27): ("Автокалибровка", "ориентация, крен и тангаж лидара — по рельсам и полотну: любое крепление"),
        (32, 33): ("Модель пути", "полотно, головки рельсов, ось; кривизна по стенам и колоннам до 150–200 м"),
        (28, 29): ("Габарит", "коридор 2,1 × 3,0 м вдоль оси и ступень низких объектов на рельсах"),
        (34, 35): ("Кластеры", "радиус растёт с дальностью; фильтры инфраструктуры; дальнее правило"),
        (30, 31): ("Решение", "подтверждение 0,5 с → GO / CAUTION / STOP / FAULT и свободная дистанция"),
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
        (f"Найден в **{N['person_hits']}** кадров внутри габарита", {"space_before": 8}),
        (f"Тревога через {N['person_first']} после входа в габарит", {"space_before": 8}),
        (f"Ошибка дальности ≤ {N['person_err']}", {"space_before": 8}),
        (f"Предмет на рельсе — в **{N['object_hits']}** кадров после ухода человека", {"space_before": 8}),
    ], size=12, color="1C1D22", anchor="ctr")
    notes(sl, "Вот тоннель — двухпутный, поезд стоит, лидар на кабине. Вот облако: 350 тысяч точек за 0,1 с. "
              "Зелёным — габарит поезда, который алгоритм сам протянул вдоль оси пути по рельсам и стенам. "
              "Жёлтым — всё, что попало в коридор. И вот человек, который переходит путь: красная рамка, "
              "55,8 метра, решение STOP. Справа — его точки крупно. Когда человек уходит, на рельсе остаётся "
              "предмет 45 × 60 × 30 см — его алгоритм тоже держит.")


def s_demo(sl):             # template slide 27: two browser frames
    title_chip(sl, 2, shape(sl, 55), "ДЕМОНСТРАЦИЯ")
    picture_in_placeholder(placeholder(sl, 14), os.path.join(ROOT, IMG["dashboard"]))
    picture_in_placeholder(placeholder(sl, 18), os.path.join(ROOT, IMG["chain"]))
    fill(shape(sl, 10), ["localhost:8080"])
    fill(shape(sl, 33), ["docker run resense"])
    fill(placeholder(sl, 15), ["Веб-дашборд «Контроль свободного габарита»: вид из кабины по статусу узла из "
                               "Docker-прогона на doubleT_obstacle — STOP 56,1 м, путь свободен до 56 м; "
                               "живой узел — через rosbridge"], size=12)
    fill(placeholder(sl, 16), ["Цепочка жюри в Docker: узел с RViz, bag play от обычного пользователя из "
                               "другого контейнера, /resense/decision — STOP 56 м (видео 69 с)"], size=12)
    textbox(sl, Emu(1210643), Emu(5700000), Emu(9770000), Emu(480000),
            [("docker load → docker run → ros2 bag play → /resense/decision", {"align": "ctr"})], size=16,
            color=DEEP, bold=True, anchor="ctr")


def s_results(sl):          # template slide 20: left card + five rows
    title_chip(sl, 2, shape(sl, 14), "РЕЗУЛЬТАТЫ")
    fill(placeholder(sl, 14), [
        (N["frames"], {"size": 36, "bold": True, "color": PINK}),
        ("реальных кадров прогнаны целиком", {"size": 13}),
        (N["person_hits"], {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        ("кадров с человеком на пути — тревога", {"size": 13}),
        (f"{N['ride_per_km']} на км", {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        (f"ложных событий в поездке ({N['ride_events']} за {N['ride_km']} км; правила решались на ней же)", {"size": 13}),
    ], bullet=False, color="1C1D22")
    rows = [
        f"**Реальная запись:** человек на пути — {N['person_hits']} кадров, тревога через {N['person_first']}, "
        f"ошибка ≤ {N['person_err']}; предмет на рельсе — {N['object_hits']} кадров",
        f"**Ложные остановки** (реальные; правила решались на этих же записях): поездка {N['ride_km']} км — "
        f"{N['ride_events']} событий, пять пустых записей — {N['empty_events']}",
        f"**Объекты организаторов** [их синтетика]: ящик 2 × 2 м — с {N['fake_box']} м, доска — с "
        f"{N['fake_plank']} м, кубы 0,3 м — с {N['fake_cubes']} м; висящий 5 см — с 30 м; у края — лишь 2 и 6 кадров STOP",
        f"**Человек на подходе** [наша синтетика]: первое подтверждение {N['first_person']} м "
        f"(в 5 парах: {N['anchored_legacy']} → {N['anchored_person']} м от ближних рельсов), "
        f"в каждой полосе 10 м — со {N['band_person']} м; "
        f"{N['speed_person']} м со скоростью поезда",
        f"**Задержка** {N['latency']} на кадр (p95 ≤ {N['p95']}) на одном ядре с ядрами на C++; через ROS в "
        f"Docker на 4 ядрах — p95 {N['ros_p95']} при 10 кадрах/с; без GPU",
    ]
    for idx, text in zip(range(15, 20), rows):
        fill(placeholder(sl, idx), [text], size=12, bullet=False)


def s_range(sl):            # template slide 22: horizontal bar chart + four notes
    title_chip(sl, 2, shape(sl, 15), "ДАЛЬНОСТЬ")
    gf = shape(sl, 12)
    cd = CategoryChartData()
    data = list(reversed(N["range_chart"]))             # a bar chart draws the first category at the bottom
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
        (21, 18, "~210 м — предел отражений в тоннеле", "дальше 210 м во всех 13 759 кадрах нет ни одной точки"),
        (22, 23, "Со скоростью поезда", f"накопление 5 кадров: человек {N['speed_person']} м; своя скорость по "
                                        f"лидару (ошибка {N['speed_err']}) STOP раньше не даёт — опция"),
        (24, 25, "Устойчиво", f"человек в ≥ 90 % кадров каждой полосы 10 м — со {N['band_person']} м"),
        (26, 27, "В кривых", "6 из 7 подходов, с 58–86 м — предел видимости за стеной (R ≈ 350 м)"),
    ]
    for ti, di, t, d in pairs:
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=12, bullet=False)
    textbox(sl, Emu(346075), Emu(5820000), Emu(5800000), Emu(520000),
            [f"первое подтверждение на прямой, медиана 6 подходов; «от рельсов» — объект поставлен по ближним "
             f"рельсам, а не по дальней оси детектора (5 пар, прежняя постановка — {N['anchored_legacy']} м); "
             "поезд 17–21 м/с без датчика скорости · синтетика в реальных кадрах поездки"],
            size=10, color="6B6B6B")


def s_fake(sl):             # template slide 21: column chart (turned into bars) + three cards
    """The organizers' own synthetic obstacles (set O): the only check built by the organizers."""
    title_chip(sl, 2, shape(sl, 13), "ОБЪЕКТЫ ОРГАНИЗАТОРОВ")
    shape(sl, 13).width = Emu(shape(sl, 2).width - 2 * (shape(sl, 13).left - shape(sl, 2).left))
    gf = shape(sl, 10)
    data = list(reversed(N["fake_chart"]))              # the first category is drawn at the bottom
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
             f"{N['fake_frames']} кадров, поезд едет к ним 1,4–20 м/с, скорость узлу не дана · синтетика "
             "организаторов"],
            size=10, color="E6E1F5")
    cards = [
        (21, 18, f"STOP у {N['fake_stop']}, у края — лишь вблизи",
         f"ящик 2 × 2 м в центре — с {N['fake_box']} м, с первого появления; доска поперёк рельсов — с "
         f"{N['fake_plank']} м; кубы 0,3 м — с {N['fake_cubes']} м"),
        (22, 23, "Мелкое вдали — поздно",
         "на 60–115 м от куба 0,3 м 2–4 точки в кадре, кластеру нужно 5; ящик у верха габарита — "
         f"STOP в {N['fake_top_frames']} кадров — непрерывно с 101 м, дальше CAUTION или ничего"),
        (24, 25, "Ограничения — говорим честно",
         "краевые объекты дают лишь 2 и 6 STOP кадров; висящий предмет 5 см: STOP с 30 м; объекты ставили от оси лидара "
         f"(−0,24° к рельсам), мы строим габарит по рельсам. Ложных STOP: {N['fake_outside_false']} кадров "
         f"у ящика снаружи, {N['fake_background']} — вне объектов"),
    ]
    for ti, di, t, d in cards:
        fill(placeholder(sl, ti), [t], size=15, bold_all=True)
        fill(placeholder(sl, di), [d], size=11, bullet=False)


def s_reliability(sl):      # template slide 16: four cards
    title_chip(sl, 10, shape(sl, 14), "НАДЁЖНОСТЬ")
    cards = [
        (49, 37, 38, "Любое крепление", "8 ориентаций, крен и тангаж по рельсам и полотну; проверено на "
                                        "повёрнутых реальных кадрах"),
        (50, 39, 40, "Монитор исправности", "ошибки входа → FAULT; задержка → предупреждение "
                                            "без смены решения"),
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
        "**Полотно полно предметов.** «Всё выше полотна» — 1 482 ложных события за 20 мин; порог «≥ 3 см над "
        "головкой рельса + 0,5 с» — единицы",
        f"**Предмет на рельсе делился на две ступени.** Верх на 0,10–0,15 м — между ступенью низких объектов "
        f"и габаритом; кластеризуем его целиком: {N['object_before']} → {N['object_hits']} кадров",
        "**Станции и стрелки.** Край платформы и конструкции у торца — главный источник ложных остановок; "
        "без рельсов в ближней зоне дальше 40 м — только предупреждение",
        "**Дальше 100 м — 1–5 точек на объект.** Высокие объекты — по дальнему правилу до ~150 м; мелкие "
        f"(< 0,6 м) — ближе: кубы 0,3 м организаторов — только с {N['fake_cubes']} м (на 60–115 м — 2–4 точки)",
        "**Объекты организаторов у края и тонкие.** Ящик 2 × 2 м у края — STOP лишь с 10 м (6 кадров): их объекты "
        "стоят от оси лидара (−0,24° к рельсам), наш габарит — от рельсов; висящий предмет 5 см — STOP только с 30 м",
    ]
    for idx, text in zip(range(15, 20), rows):
        ph = placeholder(sl, idx)
        ph.width = Emu(11200000)
        fill(ph, [text], size=13, bullet=False)


def s_next(sl):             # template slide 17: three cards
    fill(placeholder(sl, 0), ["ИТОГИ И ПЛАНЫ"])
    cards = [
        (49, 37, 38, "Что получилось", f"ROS 2-модуль в Docker; все {N['frames']} реальных кадров: человек и "
                                       f"предмет на рельсе найдены, {N['ride_per_km']} ложных события на км (на данных, где решались правила); "
                                       f"ящик организаторов — с {N['fake_box']} м; {N['tests']} тестов и CI"),
        (50, 39, 40, "Что дальше", "мелкие объекты раньше: короткие сигнатуры инфраструктуры, опора высоты "
                                   "по своду тоннеля; скорость от одометрии (своя по лидару — опция); "
                                   "«второе мнение» на реальных препятствиях; репетиция офлайн-запуска"),
        (51, 41, 42, "Внедрение", "docker load → run → ros2 bag play; один файл параметров; стандартные "
                                  "сообщения ROS 2 — стыкуется с системой торможения"),
    ]
    for k, (ni, ti, di, t, d) in enumerate(cards):
        fill(placeholder(sl, ni), [f"0{k + 1}"])
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=13)


NOTES = {  # speaker notes per template slide (the main shot's are set in s_hero)
    8: "Мы — команда «Молоток», четверо друзей из одного лицея; на конкурсы всегда выходим этим составом. "
       "Наше решение называется ReSense. Одной фразой: описываем нормальный тоннель и сообщаем всё, что "
       "попадает в габарит поезда.",
    9: "Роли: капитан — ROS 2, Docker и интеграция; визуализация и презентация; компьютерное зрение — модель "
       "пути и трекинг; данные, синтетика, метрики и тесты. Каждый отвечал за свою часть, код общий.",
    10: "Почему эта задача: метро — наша ежедневная дорога, а препятствий в данных почти нет, поэтому мы не "
        "учим сеть на объектах, а описываем нормальный тоннель. Главные трудности — ложные остановки на "
        "станциях и разные записи; обе решены в самой системе.",
    11: "Одной фразой: описываем нормальный тоннель и сообщаем всё, что попадает в габарит поезда. "
        "Работает в ROS 2 и Docker, без обучения на объектах. GPU мы оценили и не используем: выигрыш — "
        "десятки миллисекунд, а контейнер с запросом GPU не стартует на машине без nvidia-container-toolkit.",
    24: "Почему не нейросеть: реальных препятствий в данных почти нет, а на 100+ м у объекта единицы точек. "
        "Геометрия среды переносится между тоннелями, внешний вид объектов — нет.",
    12: "Все числа дальше — на всех 13 759 кадрах организаторов. Каждая запись обрывается на 209–210 м: "
        "дальше в тоннеле нет ни одного отражения, и это предел для любого алгоритма на этих данных.",
    25: "Пять шагов на каждый кадр, 23–31 мс в среднем на одном ядре; это с необязательными ядрами на C++, "
        "без них время детектора в 1,6–2,3 раза больше при том же выходе бит в бит. Калибровка крепления — сама, по "
        "рельсам; кривизна — по стенам, поэтому коридор осмыслен и там, где рельсов уже не видно.",
    27: "Цепочка организаторов прогнана в Docker на реальных записях: узел в одном контейнере, bag play из "
        "другого, от обычного пользователя. Решение — топик /resense/decision: GO, CAUTION, STOP, FAULT. "
        "Слева — наш дашборд: вид из кабины по статусу того же узла.",
    20: "Человек на пути — 58 из 61 кадра, предмет на рельсе — 125 из 126. Ложных событий в 20-минутной "
        "поездке — 3,5 на км, почти вдвое меньше, чем в v0.6.1. На объектах самих организаторов большой "
        "ящик — с 98 м, кубы 30 см — только с 43–53 м; STOP у всех восьми, но у края — лишь 2 и 6 кадров, о них — через слайд.",
    22: "Первое подтверждение человека — 148 м, медиана шести подходов. В пяти парных подходах — 150 м, "
        "а если ставить его по ближним рельсам, а не по нашей же дальней оси, — 154 м: дальность на прямой "
        "не зависит от оси детектора. Со скоростью поезда "
        "— 167 м; свою скорость мы меряем по лидару с ошибкой 0,07 м/с, но раньше STOP она не даёт, поэтому "
        "это опция. Дальше 210 м отражений нет. Всё это синтетика в реальных кадрах поездки.",
    21: "Это единственная внешняя проверка — объекты, которые вставили сами организаторы, поезд едет к ним до "
        "20 м/с. Большой ящик — с первого появления, 98 м; доска поперёк рельсов — с 82 м. Кубы 30 см — "
        "только с 43–53 м: на 60–115 м от них 2–4 точки в кадре. Висящий предмет 5 см — с 30 м; ящик у верха "
        "габарита — непрерывно с 101 м; у края — STOP лишь в 2 и 6 кадрах: объекты ставили от оси лидара, а наш "
        "габарит идёт по рельсам.",
    16: "Надёжность: сами находим крепление и вход, при проблемах с данными говорим FAULT, а не молчим.",
    15: "Что не сработало и почему: полотно полно железа, станции — главный источник ложных остановок, "
        "мелкие объекты организаторов видим поздно, тонкие — только вблизи, у края — лишь в нескольких кадрах.",
    17: "Итог: работающий модуль, честные цифры, понятные следующие шаги — мелкие объекты раньше, скорость "
        "от одометрии и замер на 8-ядерной машине.",
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
    if a.team:
        placeholders = []
        for slide_number, slide in enumerate(prs.slides, 1):
            for sh in slide.shapes:
                if sh.has_text_frame and re.search(r"<[^>]+>", sh.text):
                    placeholders.append(slide_number)
        if placeholders:
            raise ValueError(f"private deck still has placeholders on slides {sorted(set(placeholders))}")
    prs.save(a.out)
    os.remove(logo_path)
    print(f"{a.out}: {len(keep)} slides")


if __name__ == "__main__":
    main()
