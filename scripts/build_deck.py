#!/usr/bin/env python3
"""Fill the organizers' presentation template with the ReSense deck.

The template (37 slides, Montserrat, "Лидеры цифровой трансформации 2026") is exported from
Google Slides:

    curl -L -o template.pptx \\
      https://docs.google.com/presentation/d/17ciElVAWgeuPLiFHw7y5HMaAXmTo7g16/export/pptx
    python scripts/build_deck.py --template template.pptx --out docs/presentation/ReSense_LCT2026.pptx

Slides 7-11 (title, team, team cards, history, solution in short) keep their design and
structure as the organizers require; the solution slides use the template's own layouts
(12-29). Personal data stay as ``<...>`` placeholders for the captain. Every number is taken
from ``N`` below, which is copied from docs/EXPERIMENTS.md; the pictures are made by
``scripts/hero_view.py`` and ``resense run --render`` (paths in ``IMG``).

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
    "dashboard": "docs/img/dashboard_doubleT_obstacle.png",
    "render": "docs/img/doubleT_obstacle_0024_v062.png",   # resense run --render, frame 24
    "logo": None,                                     # the template's own "Московский транспорт" logo
}

# ---- every number on the slides (docs/EXPERIMENTS.md §0, §1d, §2d, §3) --------------------
N = {
    "frames": "13 759",
    "person_hits": "58 из 61", "person_first": "0,3 с", "person_err": "0,35 м",
    "object_hits": "118 из 126", "object_before": "2",
    "ride_events": "47", "ride_per_km": "3,6", "ride_km": "13",
    "empty_events": "20",
    "first_person": "148", "sustained_person": "135", "speed_person": "167",
    "latency": "42–58 мс", "p95": "69 мс",
    "tests": "147",
    # first confirmed detection, straight track, median over the approaches [synthetic in real frames]
    "range_chart": [("человек 1,7 м", 148), ("тележка", 144), ("ящик 1 м", 111), ("висящий кабель 3 см", 95),
                    ("предмет поперёк рельса", 46), ("ящик 30 см на рельсе", 44)],
}

PINK, DEEP, VIOLET, LIGHT = "FF0053", "520978", "8A83D1", "FFD6E4"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"


def qa(tag):
    return "{%s}%s" % (A, tag)


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


# ------------------------------------------------------------------------------------ slides
def s07_title(sl, logo_path):
    fill(placeholder(sl, 0), ["ReSense"])
    body = placeholder(sl, 12)
    fill(body, ["Кейс 05", "Обнаружение посторонних объектов в тоннеле метро по данным 3D-лидара"], size=15)
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
    fill(shape(sl, 18), ["КОМАНДА «ReSense»"])
    fill(shape(sl, 14), [
        "**Капитан:** <ФИО>, <специальность>",
        "**Кол-во участников:** 4 человека",
        "**Краткое описание:**",
        ("собрались под этот кейс из четырёх специализаций: ROS 2 и интеграция, визуализация, "
         "компьютерное зрение, данные и оценка", {"italic": False}),
        ("место работы / учёбы: <организации участников>", {}),
        "**Город и регион:** <город>, <регион>",
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


def s09_cards(sl):
    fill(shape(sl, 7), ["КОМАНДА «ReSense»"])
    cards = [  # (card, photo, name, details) shape ids, left to right
        (17, 2, 15, 9), (56, 3, 58, 57), (59, 4, 61, 60), (62, 5, 64, 63), (65, 6, 67, 66)]
    roles = ["Капитан · ROS 2, Docker, интеграция", "Визуализация, демо, презентация",
             "Компьютерное зрение: модель пути, трекинг", "Данные, синтетика, метрики, тесты"]
    for (card, photo, name, det), role in zip(cards, roles):
        fill(shape(sl, name), ["<Имя Фамилия>"])
        fill(shape(sl, det), [role, "<@ник>", "<телефон>", "<место работы / учёбы>"], size=11)
    for sid in cards[4]:                       # a team of four: the fifth card goes
        remove(shape(sl, sid))
    step = shape(sl, 56).left - shape(sl, 17).left
    span = 3 * step + shape(sl, 17).width
    dx = (12192000 - span) // 2 - shape(sl, 17).left
    for group in cards[:4]:
        for sid in group:
            s = shape(sl, sid)
            s.left = Emu(s.left + dx)


def s10_history(sl):
    fill(shape(sl, 7), ["ИСТОРИЯ КОМАНДЫ"])
    fill(shape(sl, 37), ["Собрались под этот кейс вчетвером: системный анализ и ROS 2, фронтенд и визуализация, "
                         "компьютерное зрение, данные и оценка. <личная история, одна фраза>"], size=12)
    fill(shape(sl, 43), ["Задача безопасности на настоящих данных метро: поезд без машиниста должен сам ответить "
                         "«путь свободен» или «тормозить». Вдохновил сам лидар — стены видны на 150–200 м, "
                         "значит, ось пути можно вести по стенам там, где рельсов уже не видно."], size=12)
    fill(shape(sl, 40), ["Препятствий в данных почти нет — «поставили» людей и ящики в реальные кадры трассировкой "
                         "лучей лидара. Станции и стрелки давали ложные остановки — ось по стенам, зона доверия, "
                         "фильтры инфраструктуры, подтверждение 0,5 с. Записи разные (топик, frame_id, 120° и 360°, "
                         "наклон стенда 3°) — узел сам находит вход и калибруется по рельсам."], size=12)


def s11_short(sl):
    fill(shape(sl, 3), [
        "ROS 2 Humble-узел на Python (numpy / scipy / scikit-learn), только CPU",
        "Вход — PointCloud2 любого из двух наборов топик / frame_id; выход — решение GO / CAUTION / STOP / "
        "FAULT, дистанция до препятствия и «проверенно свободная» дистанция, Detection3DArray, маркеры RViz, "
        "JSON-статус",
        "В каждом кадре: автокалибровка крепления → модель пути (полотно, рельсы, ось, кривизна по стенам) → "
        "габарит 2,1 × 3,0 м + низкие объекты на рельсах → кластеры → фильтры инфраструктуры → "
        "подтверждение 0,5 с",
        f"{N['latency']} на кадр (p95 ≤ {N['p95']}), одно ядро CPU",
        f"Все {N['frames']} реальных кадров: человек на пути найден в {N['person_hits']} кадров, "
        f"{N['ride_per_km']} ложных события на км поездки",
    ], size=12, space_before=4)
    fill(shape(sl, 7), [
        "**Применение:** «взгляд вперёд» для беспилотного поезда (GoA3/4) и хозяйственных поездов; контроль "
        "габарита при обкатке линий",
        "**Развитие:** опора высоты по своду тоннеля — мелкие объекты дальше 100 м; накопление кадров "
        "со скоростью поезда; дообучение «второго мнения» на реальных препятствиях",
        "**Внедрение:** docker build → docker run → ros2 bag play; один файл параметров; стандартные "
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
        "**Самая дальняя точка во всех данных — 208,5 м**: 300 м этим лидаром физически недостижимы",
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
        (f"Ошибка дальности < {N['person_err']}", {"space_before": 8}),
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
    picture_in_placeholder(placeholder(sl, 18), os.path.join(ROOT, IMG["render"]))
    fill(shape(sl, 10), ["localhost:8080"])
    fill(shape(sl, 33), ["resense run --render"])
    fill(placeholder(sl, 15), ["Веб-дашборд: живой узел через rosbridge или воспроизведение results.jsonl — "
                               "решение, дистанция, детекции, исправность"], size=12)
    fill(placeholder(sl, 16), ["Офлайн-рендер кадра: вид сверху и сбоку, коридор габарита, подтверждённое "
                               "препятствие; RViz и Foxglove — готовые раскладки"], size=12)
    textbox(sl, Emu(1210643), Emu(5700000), Emu(9770000), Emu(480000),
            [("docker build → docker run → ros2 bag play → /resense/decision", {"align": "ctr"})], size=16,
            color=DEEP, bold=True, anchor="ctr")


def s_results(sl):          # template slide 20: left card + five rows
    title_chip(sl, 2, shape(sl, 14), "РЕЗУЛЬТАТЫ")
    fill(placeholder(sl, 14), [
        (N["frames"], {"size": 36, "bold": True, "color": PINK}),
        ("реальных кадров прогнаны целиком", {"size": 13}),
        (N["person_hits"], {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        ("кадров с человеком на пути — тревога", {"size": 13}),
        (f"{N['ride_per_km']} на км", {"size": 36, "bold": True, "color": PINK, "space_before": 14}),
        (f"ложных событий в поездке ({N['ride_events']} за {N['ride_km']} км)", {"size": 13}),
    ], bullet=False, color="1C1D22")
    rows = [
        f"**Человек на пути** (реальная запись): {N['person_hits']} кадров, тревога через {N['person_first']}, "
        f"ошибка < {N['person_err']}",
        f"**Предмет на рельсе** (реальная): {N['object_hits']} кадров после ухода человека (v0.6.1: {N['object_before']})",
        f"**Ложные остановки:** поездка {N['ride_km']} км — {N['ride_events']} событий, пять пустых записей — "
        f"{N['empty_events']}",
        f"**Человек на подходе** [синтетика]: первое подтверждение ~{N['first_person']} м, непрерывно "
        f"с {N['sustained_person']} м; {N['speed_person']} м со скоростью поезда",
        f"**Задержка** {N['latency']} на кадр, p95 ≤ {N['p95']}, одно ядро CPU, без GPU",
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
    plot = ch.plots[0]
    plot.has_data_labels = True
    plot.data_labels.number_format = '0" м"'
    plot.data_labels.number_format_is_linked = False
    plot.data_labels.font.size = Pt(12)
    plot.data_labels.font.bold = True
    cols = [PINK, "310F53", DEEP, VIOLET, LIGHT, "FC3777"][:len(data)][::-1]
    for i, pt in enumerate(plot.series[0].points):
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = RGBColor.from_string(cols[i % len(cols)])
    ch.value_axis.maximum_scale = 200
    ch.value_axis.minimum_scale = 0
    ch.value_axis.major_unit = 50
    ch.category_axis.tick_labels.font.size = Pt(12)
    ch.value_axis.tick_labels.font.size = Pt(10)
    pairs = [
        (21, 18, "300 м — предел лидара", "дальше 208,5 м в данных нет ни одной точки"),
        (22, 23, "Со скоростью поезда", f"накопление 5 кадров: человек {N['speed_person']} м"),
        (24, 25, "Устойчиво", f"≥ 90 % кадров: человек с ~{N['sustained_person']} м"),
        (26, 27, "В кривых", "6 из 7 подходов, с 58–86 м — предел видимости за стеной (R ≈ 350 м)"),
    ]
    for ti, di, t, d in pairs:
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=12, bullet=False)
    textbox(sl, Emu(346075), Emu(5900000), Emu(5800000), Emu(380000),
            ["первое подтверждение на прямой, медиана 6 подходов, поезд 17–21 м/с без датчика скорости · "
             "синтетика в реальных кадрах поездки"],
            size=10, color="6B6B6B")


def s_reliability(sl):      # template slide 16: four cards
    title_chip(sl, 10, shape(sl, 14), "НАДЁЖНОСТЬ")
    cards = [
        (49, 37, 38, "Любое крепление", "8 ориентаций, крен и тангаж по рельсам и полотну; проверено на "
                                        "повёрнутых реальных кадрах"),
        (50, 39, 40, "Монитор исправности", "мало точек, закрытый обзор, потеря рельсов, задержка → FAULT и "
                                            "честная свободная дистанция"),
        (51, 41, 42, "Любой вход", "оба набора топик / frame_id, поиск топика, перезапуск на новой записи"),
        (52, 43, 44, "Воспроизводимо", f"{N['tests']} тестов; CI собирает образ и проигрывает бэги через "
                                       "узел; цепочка организаторов прогнана в Docker на реальных записях"),
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
        "(< 0,6 м) тревожат не дальше ~100 м",
        "**Записи разные.** Топик, frame_id, 120° и 360°, наклон стенда 3° — узел сам находит вход и "
        "калибруется по рельсам",
    ]
    for idx, text in zip(range(15, 20), rows):
        ph = placeholder(sl, idx)
        ph.width = Emu(11200000)
        fill(ph, [text], size=13, bullet=False)


def s_next(sl):             # template slide 17: three cards
    fill(placeholder(sl, 0), ["ИТОГИ И ПЛАНЫ"])
    cards = [
        (49, 37, 38, "Что получилось", f"ROS 2-модуль в Docker; все {N['frames']} реальных кадров: человек и "
                                       f"предмет на рельсе найдены, {N['ride_per_km']} ложных события на км; "
                                       f"{N['tests']} тестов и CI"),
        (50, 39, 40, "Что дальше", "опора высоты по своду тоннеля — мелкие объекты дальше 100 м; скорость "
                                   "поезда в узел; «второе мнение» на реальных препятствиях; замер на i7-9700E"),
        (51, 41, 42, "Внедрение", "docker build → run → ros2 bag play; один файл параметров; стандартные "
                                  "сообщения ROS 2 — стыкуется с системой торможения"),
    ]
    for k, (ni, ti, di, t, d) in enumerate(cards):
        fill(placeholder(sl, ni), [f"0{k + 1}"])
        fill(placeholder(sl, ti), [t], size=16)
        fill(placeholder(sl, di), [d], size=13)


# template slide number -> filler, in the order of the deck
PLAN = [(7, None), (8, s08_team), (9, s09_cards), (10, s10_history), (11, s11_short),
        (24, s_problem), (12, s_data), (25, s_algorithm), (13, s_hero), (27, s_demo), (20, s_results),
        (22, s_range), (16, s_reliability), (15, s_hard), (17, s_next)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--template", required=True, help="the organizers' template exported as .pptx")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
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
    prs.save(a.out)
    os.remove(logo_path)
    print(f"{a.out}: {len(keep)} slides")


if __name__ == "__main__":
    main()
