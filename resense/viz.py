"""Matplotlib rendering of frames, corridor and detections (reports, video frames)."""
from __future__ import annotations

from typing import Optional

import numpy as np

from resense.detector import FrameResult
from resense.frame import Frame


def render_frame(frame: Frame, result: Optional[FrameResult], path: str, x_max: float = 150.0,
                 title: str = "", dpi: int = 80, show_candidates: bool = True) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle

    xyz = frame.xyz
    sel = xyz[:, 0] < x_max
    P = xyz[sel]
    fig, ax = plt.subplots(2, 1, figsize=(16, 9), gridspec_kw={"height_ratios": [1.3, 1]})
    for a, col, lim, lab in ((ax[0], 1, (-8, 8), "Y left [m]"), (ax[1], 2, (-4, 6), "Z up [m]")):
        a.scatter(P[:, 0], P[:, col], s=0.15, c="#b8b8b8", rasterized=True)
        a.set_xlim(0, x_max)
        a.set_ylim(*lim)
        a.set_ylabel(lab)
        a.grid(True, alpha=0.3)
    if result is not None:
        ci = result.corridor_idx
        ci = ci[xyz[ci, 0] < x_max]
        C = xyz[ci]
        for a, col in ((ax[0], 1), (ax[1], 2)):
            a.scatter(C[:, 0], C[:, col], s=1.2, c="#f2a900", rasterized=True, label="inside gauge corridor")
        xs = np.linspace(0, x_max, 100)
        ax[1].plot(xs, result.track.floor_z(xs), "g--", lw=1, label="floor model")
        ax[0].plot(xs, result.track.center_y(xs), "g--", lw=1, label="track axis")
        if show_candidates:
            for c in result.candidates:
                if c.distance > x_max:
                    continue
                for a, col in ((ax[0], 1), (ax[1], 2)):
                    a.add_patch(Rectangle((c.bbox_min[0], c.bbox_min[col]), max(c.size[0], 0.3),
                                          max(c.size[col], 0.3), fill=False, ec="#4a90d9", lw=0.8))
        for d in result.detections:
            if d.distance > x_max:
                continue
            lo = d.center - d.size / 2
            color = "#d0021b" if getattr(d, "zone", "gauge") == "gauge" else "#ff8c00"
            for a, col in ((ax[0], 1), (ax[1], 2)):
                a.add_patch(Rectangle((lo[0], lo[col]), max(d.size[0], 0.4), max(d.size[col], 0.4),
                                      fill=False, ec=color, lw=2))
            ax[0].annotate(f"#{d.id} {d.distance:.1f} m  p={d.confidence:.2f}", (d.center[0], d.center[1]),
                           xytext=(4, 8), textcoords="offset points", color=color, fontsize=9, weight="bold")
        status = ("OBSTACLE  %.1f m" % result.nearest_distance) if result.obstacle else "path clear"
        warn = getattr(result, "warnings", [])
        if warn and not result.obstacle:
            status = "WARNING (near gauge)  %.1f m" % min(w.distance for w in warn)
        ax[0].set_title(f"{title}   |   {status}   |   {result.timing_ms.get('total', 0):.0f} ms",
                        color="#d0021b" if result.obstacle else "#2c7a2c", loc="left")
        ax[0].legend(loc="upper right", fontsize=8)
    ax[1].set_xlabel("X forward along track [m]")
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
