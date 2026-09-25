#!/usr/bin/env python3
"""Recreate docs/images dashboard captures from the built-in demo and real status stream.

Run from the repository root after installing Playwright and a Chromium browser:

    python web/demo/capture_gallery.py --chromium /path/to/chrome

Use --output-dir for a preview outside the repository.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "web" / "index.html"
REAL_RUN = ROOT / "docs" / "evidence" / "docker_2026-09-23" / "obstacle_status.jsonl.gz"


def capture(output_dir: Path, chromium: str | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        launch = {"headless": True}
        if chromium:
            launch["executable_path"] = chromium
        browser = playwright.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=1)
        page.goto(INDEX.as_uri(), wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        page.evaluate("document.fonts.ready")

        page.click("#demo")
        page.evaluate("window.resense.pause()")
        for filename, index in (("dashboard-clear.png", 0), ("dashboard-caution.png", 10), ("dashboard-stop.png", 30)):
            page.evaluate("index => { window.resense.seek(index); window.scrollTo(0, 0); }", index)
            page.wait_for_timeout(150)
            page.screenshot(path=str(output_dir / filename), full_page=True, animations="disabled")
            print(output_dir / filename)

        page.click("#tab-plan")
        page.locator("#source-panel").evaluate("section => section.open = false")
        page.locator("#safety-card").evaluate("section => section.open = false")
        page.locator("#detector-card").evaluate("section => section.open = true")
        page.locator("#node-card").evaluate("section => section.open = true")
        page.wait_for_timeout(150)
        page.screenshot(path=str(output_dir / "dashboard-plan.png"), full_page=True, animations="disabled")
        print(output_dir / "dashboard-plan.png")
        page.click("#tab-cab")
        page.locator("#source-panel").evaluate("section => section.open = true")
        page.locator("#safety-card").evaluate("section => section.open = true")
        page.locator("#detector-card").evaluate("section => section.open = false")
        page.locator("#node-card").evaluate("section => section.open = false")

        with gzip.open(REAL_RUN, "rt", encoding="utf-8") as stream:
            lines = "\n".join(line for line in stream if line.lstrip().startswith("{"))
        frames = [json.loads(line) for line in lines.splitlines() if line.strip()]
        first_alarm = next(index for index, frame in enumerate(frames) if frame.get("obstacle"))
        page.evaluate("text => window.resense.loadText(text, 'doubleT_obstacle')", lines)
        page.evaluate("index => { window.resense.seek(index); window.scrollTo(0, 0); }", first_alarm)
        page.wait_for_timeout(150)
        page.screenshot(path=str(output_dir / "dashboard-cab-real.png"), full_page=True, animations="disabled")
        print(output_dir / "dashboard-cab-real.png")
        browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium", help="Path to an installed Chromium or Chrome binary")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs" / "images")
    arguments = parser.parse_args()
    capture(arguments.output_dir, arguments.chromium)
