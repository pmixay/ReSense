# Presentation refresh — 26 September 2026

The public deck/PDF, five dashboard images, overview video and short dashboard
replay were rebuilt after correcting the output contract: `GO` means no obstacle
detected, and `clear_distance` is an estimated monitored range. Missed obstacles
can remain inside that range. The dashboard now shows health-only `CAUTION` and
`FAULT` in its main banner as well as its status chip.

## Evidence

- [Manifest](manifest.json): SHA-256 hashes of outputs, relevant sources and the
  downloaded organizer template; video metadata and verification summary.
- [Browser checks](web_tests.log): 14 passed, including FAULT/CAUTION/GO/STOP
  precedence and the 16-slide presentation check.
- [Dashboard capture](dashboard_current.log): 103 real recorded messages at 2×,
  STOP at 56.1 m; 6.88 s H.264 clip at 1440 × 900.
- [Overview build](overview_build.log): 170 s, 1920 × 1080, 25 fps, H.264,
  20,222,715 bytes, 37 subtitle cues. All six overview tests passed, including
  the current ride baseline, matching subtitles, upload size and faststart.

The real dashboard input is the committed
[`obstacle_status.jsonl.gz`](../docker_2026-09-23/obstacle_status.jsonl.gz).
The gallery combines its real cab capture with explicitly described
demonstration scenes; see [`docs/images/README.md`](../../images/README.md).
Slides 2 and 8, the clear dashboard image and the overview at 46 s were visually
inspected. Montserrat Regular/Bold are embedded in the PDF.

## Rebuild

Run `web/demo/capture_gallery.py`, then `scripts/build_deck.py --template TEMPLATE`
and export its PPTX through LibreOffice with Montserrat available. Run
`scripts/make_overview_video.py --ffmpeg /usr/bin/ffmpeg --preset medium`.
The short dashboard clip uses `web/demo/check_dashboard.py --speed 2` on the
decompressed source capture, then FFmpeg H.264/yuv420p with faststart.

Private team data and photos remain absent from this clone, so the public deck
keeps its intended placeholders. Existing raw clips from 23–25 September retain
historical UI text; the presentation describes its corrected meaning. This
refresh does not change detector code or create new detector accuracy evidence.
