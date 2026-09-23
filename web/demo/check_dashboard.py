#!/usr/bin/env python3
"""Headless check of the dashboard's offline replay mode (Playwright + Chromium).

Opens ``web/index.html`` from disk, loads a ``results.jsonl`` (from ``resense run --out`` or
``web/demo/make_demo_run.py``) through the file input, plays it back and asserts that the
Russian banner shows ПУТЬ СВОБОДЕН at the start and ПРЕПЯТСТВИЕ with a distance inside ``[--min-dist,
--max-dist]`` at some point.  Saves a screenshot of the frame with the nearest obstacle and,
with ``--video``, a WebM recording of the replay.

    python web/demo/make_demo_run.py                                  # -> out/demo_run.jsonl
    python web/demo/check_dashboard.py                                # screenshot -> docs/img/dashboard_synthetic.png
    python web/demo/check_dashboard.py --video out/dashboard.webm     # + recording of the replay

Needs ``pip install playwright`` and a Chromium build Playwright can find (``PLAYWRIGHT_BROWSERS_PATH``
or ``playwright install chromium``); ``--chromium <path>`` points at an explicit binary.
Exit code 0 when every assertion holds, 1 otherwise.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
INDEX = os.path.join(_ROOT, "web", "index.html")
OBSTACLE_RE = re.compile(r"ПРЕПЯТСТВИЕ\s+([\d.]+)\s*м")


def banner_text(page) -> str:
    """The banner's own text node (innerText would collapse the double space and append the
    replay sub-line)."""
    return page.evaluate("document.getElementById('banner').firstChild.textContent").strip()


def find_chromium(explicit: str | None = None) -> str | None:
    """An explicit path, else a Chromium under PLAYWRIGHT_BROWSERS_PATH (newest revision)."""
    if explicit:
        return explicit
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if not root:
        return None
    cands = sorted(glob.glob(os.path.join(root, "chromium-*", "chrome-linux", "chrome")))
    cands += sorted(glob.glob(os.path.join(root, "chromium_headless_shell-*", "chrome-linux", "headless_shell")))
    return cands[-1] if cands else None


def launch(p, chromium: str | None):
    """Try Playwright's own browser first, then fall back to a binary found on disk."""
    try:
        return p.chromium.launch(headless=True)
    except Exception as e:      # revision mismatch between the pip package and the installed build
        path = find_chromium(chromium)
        if not path:
            raise
        print(f"default launch failed ({str(e).splitlines()[0]}); using {path}", file=sys.stderr)
        return p.chromium.launch(headless=True, executable_path=path)


def media_duration_s(path: str) -> float | None:
    """Duration of a media file via ffprobe/ffmpeg if one is available (Playwright ships an ffmpeg)."""
    cands = [shutil.which("ffprobe"), shutil.which("ffmpeg")]
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if root:
        cands += sorted(glob.glob(os.path.join(root, "ffmpeg-*", "ffmpeg-linux")))
    for exe in [c for c in cands if c]:
        try:
            out = subprocess.run([exe, "-i", path], capture_output=True, text=True, timeout=30)
            m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", out.stderr + out.stdout)
            if m:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception:
            continue
    return None


def check(jsonl: str, screenshot: str | None, video: str | None, speed: float, min_dist: float,
          max_dist: float, chromium: str | None = None, timeout_s: float = 120.0) -> dict:
    from playwright.sync_api import sync_playwright

    jsonl = os.path.abspath(jsonl)
    if not os.path.exists(jsonl):
        raise SystemExit(f"{jsonl} not found; run: python web/demo/make_demo_run.py --out {jsonl}")
    report = {"jsonl": jsonl, "frames": 0, "observed": [], "first_banner": None, "obstacle_banner": None,
              "nearest_min_m": None, "screenshot": None, "video": None, "video_bytes": None,
              "video_s": None, "ok": False, "errors": []}
    video_tmp = tempfile.mkdtemp(prefix="resense_video_") if video else None
    with sync_playwright() as p:
        browser = launch(p, chromium)
        ctx_kw = {"viewport": {"width": 1440, "height": 900}}
        if video:
            ctx_kw.update(record_video_dir=video_tmp, record_video_size={"width": 1440, "height": 900})
        context = browser.new_context(**ctx_kw)
        page = context.new_page()
        page.on("pageerror", lambda e: report["errors"].append(f"page error: {e}"))
        page.goto("file://" + INDEX, wait_until="domcontentloaded")   # the roslib CDN may be unreachable: do not wait for 'load'
        page.wait_for_function("window.resense !== undefined")
        report["first_banner"] = banner_text(page)

        page.set_input_files("#file", jsonl)
        page.wait_for_function("window.resense.state.frames.length > 0")
        n = page.evaluate("window.resense.state.frames.length")
        report["frames"] = n
        banner0 = banner_text(page)
        report["observed"].append((0, banner0))
        page.select_option("#speed", "%g" % speed)
        page.click("#play")
        t_end = time.time() + timeout_s
        last_idx = -1
        while time.time() < t_end:
            st = page.evaluate("({idx: window.resense.state.idx, playing: window.resense.state.playing})")
            if st["idx"] != last_idx:
                last_idx = st["idx"]
                report["observed"].append((last_idx, banner_text(page)))
            if not st["playing"] and st["idx"] >= n - 1:
                break
            time.sleep(0.02)
        else:
            report["errors"].append("playback did not finish in time")
        # deterministic screenshot: the frame with the nearest confirmed obstacle
        best = page.evaluate("""() => { const f = window.resense.state.frames; let b = -1, d = Infinity;
            f.forEach((r, i) => { if (r.obstacle && r.nearest_distance != null && r.nearest_distance < d) { d = r.nearest_distance; b = i; } });
            return b; }""")
        if best >= 0:
            page.evaluate(f"window.resense.pause(); window.resense.seek({best})")
            report["obstacle_banner"] = banner_text(page)
            page.wait_for_timeout(300)
        if screenshot:
            os.makedirs(os.path.dirname(os.path.abspath(screenshot)) or ".", exist_ok=True)
            page.screenshot(path=screenshot, full_page=False)
            report["screenshot"] = os.path.abspath(screenshot)
        if video:
            page.wait_for_timeout(500)
        context.close()
        if video:
            try:
                src = page.video.path()
            except Exception:
                src = None
            if src and os.path.exists(src):
                os.makedirs(os.path.dirname(os.path.abspath(video)) or ".", exist_ok=True)
                shutil.move(src, video)
                report["video"] = os.path.abspath(video)
                report["video_bytes"] = os.path.getsize(video)
                report["video_s"] = media_duration_s(video)
            else:
                report["errors"].append("no video file was produced")
        browser.close()
    if video_tmp:
        shutil.rmtree(video_tmp, ignore_errors=True)

    # --- assertions ------------------------------------------------------------------------
    texts = [t for _, t in report["observed"]]
    if not texts or not texts[0].startswith("ПУТЬ СВОБОДЕН"):
        report["errors"].append(f"banner at the start is {texts[:1]!r}, expected ПУТЬ СВОБОДЕН")
    dists = [float(m.group(1)) for t in texts for m in [OBSTACLE_RE.search(t)] if m]
    report["nearest_min_m"] = min(dists) if dists else None
    if not dists:
        report["errors"].append("the banner never showed ПРЕПЯТСТВИЕ during playback")
    elif not any(min_dist <= d <= max_dist for d in dists):
        report["errors"].append(f"ПРЕПЯТСТВИЕ distances {sorted(set(dists))[:5]}... never inside [{min_dist}, {max_dist}] m")
    if report["obstacle_banner"] and not OBSTACLE_RE.search(report["obstacle_banner"]):
        report["errors"].append(f"after seeking to the nearest-obstacle frame the banner says {report['obstacle_banner']!r}")
    report["ok"] = not report["errors"]
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jsonl", default="out/demo_run.jsonl")
    p.add_argument("--screenshot", default="out/dashboard_synthetic.png",
                   help="PNG to write ('' to skip); pass docs/img/dashboard_synthetic.png to refresh the committed one")
    p.add_argument("--video", default=None, help="record the replay to this .webm (e.g. out/dashboard.webm)")
    p.add_argument("--speed", type=float, default=1.0, help="replay speed: 0.25 0.5 1 2 4 10")
    p.add_argument("--min-dist", type=float, default=40.0)
    p.add_argument("--max-dist", type=float, default=125.0)
    p.add_argument("--chromium", default=None, help="explicit Chromium binary (fallback when the default launch fails)")
    p.add_argument("--timeout", type=float, default=120.0)
    a = p.parse_args(argv)
    r = check(a.jsonl, a.screenshot or None, a.video, a.speed, a.min_dist, a.max_dist, a.chromium, a.timeout)
    seen = {t for _, t in r["observed"]}
    print(f"frames: {r['frames']}  banner states seen: {len(seen)}  first: {r['observed'][0][1] if r['observed'] else None!r}")
    print(f"nearest ПРЕПЯТСТВИЕ shown: {r['nearest_min_m']} m  (accepted window {a.min_dist}-{a.max_dist} m)")
    if r["screenshot"]:
        print(f"screenshot: {r['screenshot']} ({os.path.getsize(r['screenshot'])} bytes)")
    if r["video"]:
        print(f"video: {r['video']} ({r['video_bytes']} bytes, {r['video_s']} s)")
    for e in r["errors"]:
        print("ERROR:", e)
    print("PASS" if r["ok"] else "FAIL")
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
