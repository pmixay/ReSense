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


def test_srt_time_format():
    assert module.fmt_srt_time(0.6) == "00:00:00,600"
    assert module.fmt_srt_time(169.4) == "00:02:49,400"
    assert module.fmt_srt_time(3725.25) == "01:02:05,250"


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
