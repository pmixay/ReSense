"""The overview video's cut table (scripts/make_overview_video.py) and the committed outputs: the
table is consistent, the .srt sidecar is the table's narration with the same timings (at most two
lines a cue), and the MP4 is within the upload budget with its index at the front. Needs neither
Pillow nor ffmpeg: the script imports them only when it renders.

The image copies tests/ and scripts/ but not docs/ (.dockerignore), so the checks of the files in
docs/ are defined only in a checkout that has them (the CI job "pytest"); nothing is skipped."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "make_overview_video.py"
SPEC = importlib.util.spec_from_file_location("resense_make_overview_video", PATH)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_cut_table_is_consistent():
    assert module.check_table(files=False) == []
    assert module.DURATION == 170.0                           # 2:50, docs/PRESENTATION.md
    names = [b["name"] for b in module.BLOCKS]
    assert names == ["Проблема", "Идея", "Алгоритм", "Демонстрация", "Объекты организаторов", "Цифры",
                     "Что дальше"]
    for b in module.BLOCKS:
        for c in b["cards"]:
            assert c["tag"] in (None, *module.TAGS)


def test_archived_visuals_are_identified_separately_from_current_metrics():
    old_sources = ("docker_chain_rviz.mp4", "doubleT_obstacle_cab.mp4", "fake_objects_cab.mp4",
                   "doubleT_obstacle_0024_v062.png")
    for shot in module.all_shots():
        if any(name in str(shot["src"]) for name in old_sources):
            assert "архив" in shot["note"], shot


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
    module.write_chapters(path, (93, 111))
    text = path.read_text()
    assert text.count("[CHAPTER]") == 1
    assert "START=0\nEND=18000\n" in text
    assert "title=Объекты организаторов" in text


if (ROOT / module.OUT_MP4).is_file():

    def test_sources_exist():
        assert module.check_table(files=True) == []

    def test_srt_is_the_tables_narration():
        cues = module.parse_srt(ROOT / module.OUT_SRT)
        subs = module.all_subs()
        assert len(cues) == len(subs)
        for (t0, t1, text), (s0, s1, line) in zip(cues, subs):
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
# The image may carry individual evidence fixtures without the published video/baselines.
# Like the other committed-output checks above, this check belongs to the video checkout.
if (ROOT / module.OUT_MP4).is_file():

    def test_ride_card_follows_the_current_gate_baseline():
        """The ride card is a measured number: it names the ride events of the newest gate baseline
        that measured the ride (by its "created" stamp, as web/demo/test_web.py picks it; since 27.09
        not every baseline is named *_ride*), so a new baseline without a rebuilt video fails here."""
        import json
        baselines = [json.loads(p.read_text()) for p in RESULTS.glob("regression_baseline_*.json")]
        latest = max((b for b in baselines if b.get("ride", {}).get("available")), key=lambda b: b["created"])
        events = latest["ride"]["alarm_events"]
        cards = [c for b in module.BLOCKS for c in b["cards"] if c["kind"] == "num" and "поездке" in c["label"]]
        assert cards, "no ride card in the cut table"
        for c in cards:
            assert f"({events} за 13 км)" in c["label"]
            assert c["big"] == f"{events / 13:.1f} на км".replace(".", ",")
