"""The overview video's cut table (scripts/make_overview_video.py) and the committed outputs: the
table is consistent, the .srt sidecar is the table's narration with the same timings (at most two
lines a cue), the MP4 is within the upload budget with its index at the front, and the numbers of the
``GATE`` block are those of the newest team regression gate baseline. Needs neither Pillow, ffmpeg
nor a TTS voice: the script imports them only when it renders.

The image copies tests/ and scripts/ but not docs/ (.dockerignore), so the checks of the files in
docs/ are defined only in a checkout that has them (the CI job "pytest"); nothing is skipped."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "make_overview_video.py"
SPEC = importlib.util.spec_from_file_location("resense_make_overview_video", PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_cut_table_is_consistent():
    assert module.check_table(files=False) == []
    assert module.DURATION <= 180.0                           # the organizers' "short video", ~3 min
    names = [b["name"] for b in module.BLOCKS]                # the pitch arc of ТЗ §8.8
    assert names == ["Проблема", "Идея", "Алгоритм", "Демонстрация", "Результаты", "Что получилось"]
    for b in module.BLOCKS:
        for c in b["cards"]:
            assert c["tag"] in (None, *module.TAGS)


def test_ends_on_the_organizers_sentence():
    """ТЗ §8.8: «… А вот препятствие, которое наш алгоритм увидел за X метров» — the real person and
    the organizers' box, with the distances of the GATE block."""
    last = module.BLOCKS[-1]["subs"]
    text = " ".join(c[2] for c in last)
    assert "Вот лидар" in text
    assert f"увидел за {module.DT_SAY_M} " in text
    assert f"увидел за {module.GATE['o_big_center_m']} " in text


def test_archived_visuals_are_identified_separately_from_current_metrics():
    old_sources = ("docker_chain_rviz.mp4", "doubleT_obstacle_cab.mp4", "fake_objects_cab.mp4",
                   "doubleT_obstacle_0024_v062.png", "doubleT_obstacle_offline.mp4", "dashboard_current.mp4")
    for shot in module.all_shots():
        if any(name in str(shot["src"]) for name in old_sources):
            assert "архив" in shot["note"], shot


def test_voice_text_has_no_digits_and_numbers_are_spelled():
    for cue in module.all_subs():
        assert not any(ch.isdigit() for ch in module.spoken(cue)), cue
    assert module.words(98) == "девяносто восемь"
    assert module.words(151) == "сто пятьдесят один"
    assert module.words(201, "gen") == "двухсот одного"
    assert module.words(26, gender="n") == "двадцать шесть"
    assert module.words(21, gender="n") == "двадцать одно"
    assert module.words(13759) == "тринадцать тысяч семьсот пятьдесят девять"
    assert module.words_dec(2.0) == "два"
    assert module.words_dec(2.2) == "две целых две десятых"
    assert [module.pl(n, "кадр", "кадра", "кадров") for n in (1, 3, 11, 21, 193, 126)] == \
        ["кадр", "кадра", "кадров", "кадр", "кадра", "кадров"]


def test_srt_time_format():
    assert module.fmt_srt_time(0.6) == "00:00:00,600"
    assert module.fmt_srt_time(169.4) == "00:02:49,400"
    assert module.fmt_srt_time(3725.25) == "01:02:05,250"


def test_span_subtitles_are_clipped_and_rebased(tmp_path):
    from types import SimpleNamespace
    renderer = SimpleNamespace(cues=[(90, 95, ["first"], None, 0), (100, 115, ["last"], None, 0),
                                    (115, 120, ["outside"], None, 0)])
    path = tmp_path / "nested" / "clip.srt"
    module.write_srt(path, renderer, (93, 111))
    assert module.parse_srt(path) == [(0, 2, "first"), (7, 18, "last")]


def test_span_chapters_use_the_clip_timeline(tmp_path):
    path = tmp_path / "chapters.txt"
    b = module.BLOCKS[4]
    module.write_chapters(path, (b["t0"] + 1, b["t0"] + 10))
    text = path.read_text()
    assert text.count("[CHAPTER]") == 1
    assert "START=0\nEND=9000\n" in text
    assert f"title={b['name']}" in text


def test_script_markdown_lists_every_cue():
    md = module.script_markdown()
    for cue in module.all_subs():
        assert cue[2] in md


if (ROOT / module.OUT_MP4).is_file():

    def test_sources_exist():
        assert module.check_table(files=True) == []

    def test_srt_is_the_tables_narration():
        cues = module.parse_srt(ROOT / module.OUT_SRT)
        subs = module.all_subs()
        assert len(cues) == len(subs)
        for (t0, t1, text), cue in zip(cues, subs):
            s0, s1, line = cue[:3]
            assert abs(t0 - s0) < 1e-6 and abs(t1 - s1) < 1e-6
            assert 1 <= len(text.splitlines()) <= 2
            assert " ".join(text.splitlines()) == line

    def test_mp4_within_budget_and_faststart():
        mp4 = ROOT / module.OUT_MP4
        assert 5e6 < mp4.stat().st_size <= 25e6
        head = mp4.read_bytes()[: 1 << 16]
        assert b"ftyp" in head[:16]
        assert head.find(b"moov") != -1                       # the index before the media data
        assert head.find(b"mdat") == -1 or head.find(b"moov") < head.find(b"mdat")


RESULTS = ROOT / "docs" / "evidence" / "results"

# GATE key -> (path in the baseline JSON, rounding): the one block of gate-dependent numbers
GATE_FIELDS = {
    "ride_events": (("ride", "alarm_events"), None),
    "ride_stop_episodes": (("ride", "stop_episodes"), None),
    "empty_events": (("five_empty", "alarm_events"), None),
    "empty_stop_episodes": (("five_empty", "stop_episodes"), None),
    "o_inside_stop": (("set_O", "inside_objects_with_stop"), None),
    "o_inside": (("set_O", "inside_objects"), None),
    "o_outside_false": (("set_O", "outside_false_stop_frames"), None),
    "o_big_center_m": (("set_O", "objects", "big_center", "first_stop_m"), 0),
    "o_big_above_m": (("set_O", "objects", "big_above", "first_stop_m"), 0),
    "o_long_low_m": (("set_O", "objects", "long_low_on_rails", "first_stop_m"), 0),
    "o_small_center_m": (("set_O", "objects", "small_center", "first_stop_m"), 0),
    "o_small_on_rail_m": (("set_O", "objects", "small_on_rail", "first_stop_m"), 0),
    "o_small_edge_m": (("set_O", "objects", "small_edge_inside", "first_stop_m"), 0),
    "o_thin_hanging_m": (("set_O", "objects", "thin_hanging", "first_stop_m"), 0),
    "o_big_edge_m": (("set_O", "objects", "big_edge_inside", "first_stop_m"), 0),
    "f_person_m": (("set_F_straight", "kinds", "person", "first_detection_median_m"), 0),
    "f_trolley_m": (("set_F_straight", "kinds", "trolley", "first_detection_median_m"), 0),
    "f_box1_m": (("set_F_straight", "kinds", "box1.0", "first_detection_median_m"), 0),
    "f_cable_m": (("set_F_straight", "kinds", "cable", "first_detection_median_m"), 0),
    "f_box05_m": (("set_F_straight", "kinds", "box0.5", "first_detection_median_m"), 0),
    "dt_stop_frames": (("recordings", "doubleT_obstacle", "alarm_frames"), None),
    "dt_first_stop_frame": (("recordings", "doubleT_obstacle", "first_alarm_frame"), None),
    "dt_near_m": (("recordings", "doubleT_obstacle", "alarm_dist", 0), 1),
    "dt_far_m": (("recordings", "doubleT_obstacle", "alarm_dist", 1), 1),
    "dt_person": (("recordings", "doubleT_obstacle", "labelled", "per_label", "person_crossing", "hits"), None),
    "dt_rail": (("recordings", "doubleT_obstacle", "labelled", "per_label", "object_on_rail_from_frame_75",
                 "hits"), None),
}


def test_every_gate_number_has_a_baseline_field():
    assert set(GATE_FIELDS) == set(module.GATE) - {"run"}


# The image may carry individual evidence fixtures without the published video/baselines.
# Like the other committed-output checks above, this check belongs to the video checkout.
if (ROOT / module.OUT_MP4).is_file():

    def _latest_baseline():
        """The newest gate baseline that measured the ride (by its "created" stamp, as
        web/demo/test_web.py picks it; since 27.09 not every baseline is named *_ride*)."""
        baselines = [json.loads(p.read_text()) for p in RESULTS.glob("regression_baseline_*.json")]
        return max((b for b in baselines if b.get("ride", {}).get("available")), key=lambda b: b["created"])

    def test_gate_block_follows_the_newest_gate_baseline():
        """Every number of the GATE block equals its field in the newest baseline, so a new baseline
        without an updated block (and a re-rendered video: the .srt test above) fails here."""
        latest = _latest_baseline()
        wrong = {}
        for key, (path, digits) in GATE_FIELDS.items():
            value = latest
            for step in path:
                value = value[step]
            if digits is not None:
                value = round(value, digits) if digits else int(round(value))
            if module.GATE[key] != value:
                wrong[key] = (module.GATE[key], value)
        assert not wrong, f"GATE differs from the newest baseline (block, baseline): {wrong}"
        assert latest["recordings"]["doubleT_obstacle"]["frames"] == module.FIXED["dt_frames"]

    def test_ride_card_follows_the_current_gate_baseline():
        events = _latest_baseline()["ride"]["alarm_events"]
        cards = [c for b in module.BLOCKS for c in b["cards"] if c["kind"] == "num" and "поездке" in c["label"]]
        assert cards, "no ride card in the cut table"
        for c in cards:
            assert f"({events} за 13 км)" in c["label"]
            assert c["big"] == f"{events / 13:.1f} на км".replace(".", ",")
