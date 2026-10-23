"""Build P2's source-labelled defence draft using the existing organizer layouts.

No new evaluation: current gate is the F1a author run; range remains 1.1.0.
The approved deck is never overwritten. P1 approval and final J1 are pending.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import build_deck as deck  # noqa: E402

HERE = Path(__file__).resolve().parent
GATE = ROOT / "docs/evidence/f1a_completion_2026-10-20/gate-c-candidate.json"
OUTPUT = ROOT / "docs/presentation/P2_defence_2026-10-21.pptx"


def wrap(original, after):
    def apply(slide):
        original(slide)
        after(slide)
    return apply


def range_labels(sl):
    for idx, text in [(21, "Замер 16.10 · 1.1.0"), (18, "лучевая синтетика, реальные фоны"),
                      (24, "Три геометрии"), (25, "прямая · кривая · двухпутный"),
                      (26, "Итоговый J1 ожидается"), (27, "не замер финальной 1.2.0")]:
        deck.fill(deck.placeholder(sl, idx), [text], size=14 if idx in (21, 24, 26) else 12, bullet=False)


def results_labels(sl):
    rows = ["**Дальность:** 218 м прямая, 52–83 м кривые (синтетика, 1.1.0)",
            "**Набор O:** STOP у 8 из 8 объектов в габарите",
            "**Поездка:** 24 эпизода / 13 км; шлюз F1a, в выборке",
            "**Скорость:** 360° p95 111 мс, v1.0.0, 4 vCPU",
            "**Запуск:** пауза, скорость, смена бэгов в одном узле"]
    for idx, text in zip(range(15, 20), rows):
        deck.fill(deck.placeholder(sl, idx), [text], size=12, bullet=False)
    # Historical display measurement is distinguished from current detector quality.
    deck.fill(deck.placeholder(sl, 14), [
        ("61 из 61", {"size": 36, "bold": True, "color": deck.PINK}),
        ("человек — STOP · Pandar, реальная запись", {"size": 13}),
        ("~125 м", {"size": 36, "bold": True, "color": deck.PINK, "space_before": 14}),
        ("человек — первый STOP · Falcon", {"size": 13}),
        ("≈ 0,04 м", {"size": 36, "bold": True, "color": deck.PINK, "space_before": 14}),
        ("дрожание рисуемого бокса · замер 18.10", {"size": 13}),
    ], bullet=False, color="1C1D22")


def fake_labels(sl):
    for sh in sl.shapes:
        if sh.has_text_frame and "Синтетика; гейт" in sh.text:
            deck.fill(sh, ["Синтетика организаторов; шлюз F1a, 20.10. Сиреневый: неустойчиво."], size=10, color="E6E1F5", bullet=False)


def hard_labels(sl):
    rows = ["**Столбы:** H1 частично улучшен: 114/177; 63 пропуска на инъекции",
            "**Кривые:** K1/K2 выключены; синхронизация с поворотом не решена",
            "**Ложные STOP:** шлюз поездки 30 → 24 эпизода; итоговый J1 ожидается",
            "**Пыль:** редкие частицы организаторов проверены; плотная пыль не решена",
            "**Мелкое:** кубы 0,3 м — 43–56 м; висящий 5 см — 35 м (шлюз)"]
    for idx, text in zip(range(15, 20), rows):
        deck.fill(deck.placeholder(sl, idx), [text], size=13, bullet=False)


def final_labels(sl):
    deck.fill(deck.placeholder(sl, 38), ["ROS 2 на CPU; два лидара; 3D-бокс; пауза и смена бэгов. P4: 2 387 тестов пройдено, 8 без данных не запускались (f56ad5e)."], size=13, bullet=False)


def falcon_labels(sl):
    for sh in sl.shapes:
        if sh.has_text_frame and "кадров STOP" in sh.text:
            for paragraph in sh.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.text = run.text.replace("кадров STOP", "кадра STOP")


def demo_labels(sl):
    for sh in sl.shapes:
        if sh.has_text_frame and "Запасной ролик:" in sh.text:
            deck.fill(sh, ["RViz в контейнере: 3D-габарит по поддержанной геометрии; на кривой короче.",
                           "Резерв 21.10: ROS/RViz 1.2.0, Pandar + Falcon, 1:46. Исходник 31154690; выбор P1 ожидается."], size=12, bullet=False)


def main():
    source = deck.gate_from_baseline(GATE)
    deck.GATE = source
    for key in ("person", "rail_object", "obstacle_stop", "obstacle_first_frame", "ride_events", "ride_episodes", "empty_events", "empty_episodes", "bed_box_found"):
        deck.N[key] = source[key]
    for key, values in source["set_o"].items():
        old = deck.N["set_o"][key]
        deck.N["set_o"][key] = (old[0], *values)
    deck.V12.update(commit="31154690", tests="2 387")
    deck.FALCON.update(false=(4, 4, 115, 0, "9,4"))
    common = ("Редакция P2 21.10 для утверждения P1. 1.2.0 — кандидат; окончательный выбор образа, J1 и "
              "репетиции не закрыты. Исходник локальной подготовки 31154690. Все записи — данные разработки. ")
    gate_note = ("Источник шлюза: docs/evidence/f1a_completion_2026-10-20/gate-c-candidate.json, "
                 "авторский прогон a77d884, 20.10, кэш 1 см; не новая независимая оценка J1. "
                 "Поездка: 18 событий, 24 эпизода STOP, 102 кадра / 11271; пять пустых: 7 событий, "
                 "11 эпизодов, 37 кадров / 2287. Событие и эпизод — разные единицы. ")
    falcon_note = ("Falcon: P4 p4_review_final_bundle_2026-10-20 на f56ad5e и F1a completion "
                   "(4443 строки без изменений). 4 ложных кадра на конструкции около 115 м. "
                   "H′ убрал 8 кадров потолка, не пола. Первый STOP человека 124,8 м — полный "
                   "прогон с автопоиском ориентации; профиль falcon_ros и холодный старт окна могут "
                   "дать другое начало. Эти числа не подменяют замер короткого демо-бэга. "
                   "Оси falcon_ros +X/+Y/+Z; человек виден в сырых точках с ~249 м; 300 м не достигнуты. ")
    range_note = ("Источник: docs/evidence/rejudge_2026-10-16/prebuild/summary_1.1.0.json. "
                  "Измерено 16.10 на 1.1.0; это исторические числа, НЕ итоговая 1.2.0. "
                  "Идеальные лучевые возвраты бокса на собственной оси детектора, реальные фоны. "
                  "Прямая: человек 218,38 м, куб 1 м 151,1 м, куб 0,3 м 44,86 м; платформа 105,82; "
                  "кривая с гермозатвором 82,77; кривая в двухпутный участок 51,8 м. "
                  "Финальный J1 ожидается; не заявлять реальное обнаружение человека на 218 м. ")
    notes = {
        11: "Геометрический детектор на CPU, два лидара, ROS 2 Humble и Docker. Эксперты оценивали v1.0.0; 66/100 — внутренняя оценка агента от 13.10, не оценка организаторов.",
        12: "Pandar: 13759 реальных кадров; Falcon: 4443 кадра за 444 с, поезд стоит, человек идёт к нему. Новая синтетика: 1667 кадров. Все данные использовались в разработке. G3 зарегистрирован, не выполнен; скрытых данных организаторов нет.",
        13: gate_note + "Реальная запись doubleT_obstacle: человек 61/61, предмет 126/126, STOP 193/201 с кадра 8. Изображение главного кадра архивное; текущая цепочка проверяется отдельно.",
        27: "Сценарий и результаты локального воспроизведения: docs/evidence/p2_defence_2026-10-21/README.md. Новый резерв docs/video/p2_defence_2026-10-21.mp4: две непрерывные записи отдельных запусков, Pandar 0,5x и Falcon 1x. Между ними склейка, это не доказательство переключения одного узла. STOP после команды: 5,04 с / 55,53 м и 3,79 с / 144 м. Холодный старт Falcon с falcon_ros, не число полного прогона. Снимок кривой на слайде — 18.10. Пауза и изменение скорости не отключают контроль свежести.",
        20: gate_note + falcon_note + range_note + "Дрожание бокса 0,04 м — p90 видимого края до 120 м, замер 18.10; это не точность оси. Скорость p95 111 мс — v1.0.0, узел, 4 vCPU, 13.10; финальный S5 ожидается.",
        22: range_note,
        21: gate_note + "Набор O: восемь объектов внутри дали STOP; это не покадровая полнота 100%. Тонкий висящий: 18/42 видимых кадров, первый STOP 35,1 м. Куб снаружи имеет отдельные ложные кадры — не говорить, что ложных нет.",
        16: falcon_note + "Наклон −2,39° против −2,37° независимой подгонки — замер 19.10. Числа полного прогона не смешивать с коротким окном. Редакторская проверка источников не заменяет новое измерение.",
        15: gate_note + "H1: 82 →114/177, 63 пропуска остаются; wrong-pair случаи не приняты. K1/K2 выключены. Пыль организаторов: 13 кадров, 30 коробок, пылевых обнаружений нет; это редкие частицы, не плотная пыль. CAUTION на препятствии внутри габарита считается пропуском по ответу организаторов 19.10.",
        17: "Тесты: 2387/2387 в CI-подобной среде P4 на f56ad5e; 8 внешних-data тестов не запускались, 17 подтестов. Это результат конкретного источника, не новый прогон текущего checkout. Релиз/финальный J1/репетиции ожидаются. Торможение не подключено. Публичный веб по уточнению пользователя: https://resense.arbuz.lol/.",
    }
    for tmpl, text in notes.items():
        deck.NOTES[tmpl] = common + text
    replacements = {20: wrap(deck.s_results, results_labels), 22: wrap(deck.s_range, range_labels),
                    21: wrap(deck.s_fake, fake_labels), 15: wrap(deck.s_hard, hard_labels),
                    17: wrap(deck.s_next, final_labels), 16: wrap(deck.s_falcon, falcon_labels),
                    27: wrap(deck.s_demo, demo_labels)}
    deck.PLAN = [(n, replacements.get(n, fn)) for n, fn in deck.PLAN]
    deck.refresh(ROOT / "docs/presentation/ReSense_LCT2026.pptx", OUTPUT)
    # Enforce exact title/team visual XML preservation, not merely the presence of names.
    import zipfile
    with zipfile.ZipFile(ROOT / "docs/presentation/ReSense_LCT2026.pptx") as before, zipfile.ZipFile(OUTPUT) as after:
        for n in (1, 2, 3):
            name = f"ppt/slides/slide{n}.xml"
            assert before.read(name) == after.read(name), name
    paths = [GATE, ROOT / "docs/evidence/rejudge_2026-10-16/prebuild/summary_1.1.0.json",
             ROOT / "docs/evidence/f1a_completion_2026-10-20/README.md",
             ROOT / "docs/evidence/p4_review_final_bundle_2026-10-20/MOCK_JURY.md"]
    receipt = {"draft": str(OUTPUT.relative_to(ROOT)), "p1_approved": False, "final_j1": False,
               "title_team_xml_identical": True, "gate": source,
               "word_counts": deck.slide_word_counts(deck.Presentation(OUTPUT)),
               "sources": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    (HERE / "deck_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
