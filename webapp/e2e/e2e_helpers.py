"""Helpers shared by the e2e modules (fixtures live in conftest.py)."""
from __future__ import annotations

import re
import socket
import time


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def real_errors(errors: list[str], allowed: tuple[int, ...] = (), patterns: tuple[str, ...] = ()) -> list[str]:
    """Console errors, minus the browser's own lines for failures a test provoked on purpose: an HTTP
    status it asked for (``allowed``), or a line matching one of ``patterns`` (a refused WebSocket, an
    aborted request)."""
    out = []
    for e in errors:
        m = re.search(r"status of (\d{3})", e)
        if m and int(m.group(1)) in allowed:
            continue
        if any(re.search(p, e) for p in patterns):
            continue
        out.append(e)
    return out


def box_of(locator, timeout: float = 15_000, scroll: bool = True) -> dict:
    """The element's bounding box once it is visible and laid out. ``Locator.bounding_box()`` does not
    wait: right after a navigation a lazily rendered chart is not in the layout yet and it returns
    None (CI run 36613216928). ``scroll=False`` measures the page as it is (layout-fit checks)."""
    locator.wait_for(state="visible", timeout=timeout)
    if scroll:
        locator.scroll_into_view_if_needed(timeout=timeout)
    deadline = time.monotonic() + timeout / 1000
    while True:
        box = locator.bounding_box()
        if box and box["width"] > 0 and box["height"] > 0:
            return box
        if time.monotonic() > deadline:
            raise AssertionError(f"{locator} is visible but has no layout box after {timeout / 1000:.0f} s")
        time.sleep(0.05)


def api_route(base: str, path_re: str) -> re.Pattern:
    """A ``page.route`` pattern for backend calls only: ``base + /api + path_re`` (the page's own
    assets never match)."""
    return re.compile("^" + re.escape(base) + "/api" + path_re)


class Held:
    """Holds the matching backend requests until ``release()``: the page's loading state stays up."""

    def __init__(self, page, pattern: re.Pattern):
        self.page, self.pattern, self.routes = page, pattern, []
        page.route(pattern, lambda route: self.routes.append(route))

    def release(self) -> None:
        self.page.unroute(self.pattern)
        for r in self.routes:
            try:
                r.continue_()
            except Exception:  # a request the page cancelled meanwhile
                pass


def wait_until(cond, timeout: float = 20.0, interval: float = 0.25) -> None:
    """Poll ``cond()`` (server-side state) until it is true."""
    deadline = time.monotonic() + timeout
    while not cond():
        if time.monotonic() > deadline:
            raise TimeoutError("condition not met")
        time.sleep(interval)
