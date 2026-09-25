#!/usr/bin/env python3
"""Driver's-eye view of one frame: the LiDAR cloud in perspective, the train envelope the
detector checks, the points inside it and the confirmed obstacle with its distance.

The picture for the pitch ("the train, the LiDAR, the obstacle our algorithm saw at X m") and
for the README. The detector runs over the frames before the chosen one, so the obstacle on the
picture is a confirmed track, exactly as the ROS node would report it.

    python scripts/hero_view.py --npy /data/cache/doubleT_obstacle --frame 30 --out hero.png
    python scripts/hero_view.py --npy ... --frame 30 --lang en --out hero_en.png
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.io import iter_npy_frames  # noqa: E402

BG = "#16091f"
PINK = "#FF0053"
LIGHT = "#FFD6E4"
VIOLET = "#8A83D1"
DEEP = "#520978"
CORRIDOR = "#FFB000"
GO = "#2ecc71"

TEXT = {
    "ru": {"stop": "STOP", "obstacle": "препятствие {d} м", "go": "GO", "clear": "путь свободен {d:.0f} м",
           "caution": "CAUTION", "label": "ПРЕПЯТСТВИЕ · {d} м", "envelope": "габарит поезда 2,1 × 3,0 м",
           "foot": "{name} · кадр {i} · реальные данные организаторов · без обучения на объектах",
           "inset": "крупно: {n} точек, высота {h} м"},
    "en": {"stop": "STOP", "obstacle": "obstacle at {d} m", "go": "GO", "clear": "path clear {d:.0f} m",
           "caution": "CAUTION", "label": "OBSTACLE · {d} m", "envelope": "train envelope 2.1 × 3.0 m",
           "foot": "{name} · frame {i} · the organizers' real data · no object training",
           "inset": "close-up: {n} points, {h} m tall"},
}


def _font():
    from matplotlib import font_manager
    for f in font_manager.findSystemFonts():
        if "Montserrat-Regular" in os.path.basename(f) or "Montserrat-SemiBold" in os.path.basename(f):
            font_manager.fontManager.addfont(f)
    names = {f.name for f in font_manager.fontManager.ttflist}
    return "Montserrat" if "Montserrat" in names else "DejaVu Sans"


class Camera:
    """Pinhole camera behind and above the LiDAR, looking along the track."""

    def __init__(self, pos, W, H, hfov_deg=36.0, pitch_deg=-1.5):
        self.p = np.asarray(pos, float)
        self.W, self.H = W, H
        self.f = (W / 2) / np.tan(np.radians(hfov_deg / 2))
        self.tp = np.tan(np.radians(pitch_deg))

    def project(self, P):
        P = np.atleast_2d(P)
        d = P - self.p
        x = np.maximum(d[:, 0], 1e-3)
        u = self.W / 2 - self.f * d[:, 1] / x
        v = self.H / 2 - self.f * (d[:, 2] / x - self.tp)
        return u, v, d[:, 0]


def render(frame, res, path, name, index, lang="ru", x_max=110.0, W=1920, H=1080, hud=True):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap

    t = TEXT[lang]
    num = (lambda x: f"{x:.1f}".replace(".", ",")) if lang == "ru" else (lambda x: f"{x:.1f}")
    plt.rcParams["font.family"] = _font()
    xyz = res.xyz if res.xyz is not None else frame.xyz
    tr = res.track
    y0, z0 = float(tr.center_y(np.array([0.0]))[0]), float(tr.rail_z(np.array([0.0]))[0])
    cam = Camera((-8.0, y0, z0 + 2.3), W, H)

    fig = plt.figure(figsize=(W / 120, H / 120), dpi=120)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, W)
    ax.set_ylim(H, 0)
    ax.axis("off")

    sel = (xyz[:, 0] > 1.0) & (xyz[:, 0] < x_max)
    P = xyz[sel]
    u, v, depth = cam.project(P)
    ok = (u > -50) & (u < W + 50) & (v > -50) & (v < H + 50)
    u, v, depth, P = u[ok], v[ok], depth[ok], P[ok]
    order = np.argsort(-depth)                                   # far first, near on top
    cmap = LinearSegmentedColormap.from_list("rs", [LIGHT, VIOLET, DEEP])
    c = np.clip((P[order, 0] - 3) / (x_max * 0.8), 0, 1)
    s = np.clip(18.0 / np.maximum(depth[order], 1.0), 0.15, 2.5)
    ax.scatter(u[order], v[order], s=s, c=cmap(c), linewidths=0, alpha=0.9, rasterized=True)

    # points inside the envelope corridor
    ci = res.corridor_idx
    ci = ci[(xyz[ci, 0] > 1.0) & (xyz[ci, 0] < x_max)]
    if ci.size:
        cu, cv, _ = cam.project(xyz[ci])
        ax.scatter(cu, cv, s=2.0, c=CORRIDOR, linewidths=0, alpha=0.9, rasterized=True)

    # the envelope the detector checks: its floor edges along the axis and a frame every 20 m
    x_end = float(min(x_max, max(tr.axis_valid, 30.0)))
    xs = np.linspace(4.0, x_end, 120)
    yc, zr = tr.center_y(xs), tr.rail_z(xs)
    for side in (-1.05, 1.05):
        for h in (0.12, 3.0):
            eu, ev, _ = cam.project(np.c_[xs, yc + side, zr + h])
            ax.plot(eu, ev, color=GO, lw=1.3 if h < 1 else 0.8, alpha=0.75 if h < 1 else 0.35)
    for xf in np.arange(10.0, x_end, 20.0):
        ycf, zrf = float(tr.center_y(np.array([xf]))[0]), float(tr.rail_z(np.array([xf]))[0])
        rect = np.array([[xf, ycf - 1.05, zrf + 0.12], [xf, ycf + 1.05, zrf + 0.12],
                         [xf, ycf + 1.05, zrf + 3.0], [xf, ycf - 1.05, zrf + 3.0], [xf, ycf - 1.05, zrf + 0.12]])
        ru, rv, _ = cam.project(rect)
        ax.plot(ru, rv, color=GO, lw=0.8, alpha=0.35)
    lu, lv, _ = cam.project(np.array([[14.0, float(tr.center_y(np.array([14.0]))[0]) - 1.05,
                                       float(tr.rail_z(np.array([14.0]))[0]) + 3.0]]))
    ax.text(lu[0], lv[0] - 12, t["envelope"], color=GO, fontsize=14, ha="right", va="bottom",
            bbox=dict(boxstyle="round,pad=0.3", fc=BG, ec="none", alpha=0.85))

    # confirmed detections
    for d in res.detections:
        if d.distance > x_max:
            continue
        lo, hi = d.center - d.size / 2, d.center + d.size / 2
        corners = np.array([[a, b, c_] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c_ in (lo[2], hi[2])])
        bu, bv, _ = cam.project(corners)
        pad = 8
        x0, x1, y0b, y1b = bu.min() - pad, bu.max() + pad, bv.min() - pad, bv.max() + pad
        color = PINK if d.zone == "gauge" else CORRIDOR
        ax.add_patch(plt.Rectangle((x0, y0b), x1 - x0, y1b - y0b, fill=False, ec=color, lw=3.5))
        ax.text((x0 + x1) / 2, y0b - 14, t["label"].format(d=num(d.distance)), color="white", fontsize=20,
                weight="bold", ha="center", va="bottom",
                bbox=dict(boxstyle="round,pad=0.35", fc=color, ec="none"))

    # close-up of the nearest confirmed obstacle: its points seen from the train (front view)
    gauge = [d for d in res.detections if d.zone == "gauge" and d.distance <= x_max]
    if not hud:
        fig.savefig(path, dpi=120, facecolor=BG)
        plt.close(fig)
        return
    if gauge:
        d = min(gauge, key=lambda k: k.distance)
        lo, hi = d.center - d.size / 2 - 0.3, d.center + d.size / 2 + 0.3
        m = np.all((xyz >= lo) & (xyz <= hi), axis=1)
        Q = xyz[m]
        if len(Q) >= 5:
            ins = fig.add_axes([0.80, 0.62, 0.17, 0.30])
            ins.set_facecolor(BG)
            ins.scatter(-Q[:, 1], Q[:, 2], s=9, c=CORRIDOR, linewidths=0)
            cy, cz = -d.center[1], d.center[2]
            half = 0.6 * max(d.size[1], d.size[2]) + 0.3
            ins.set_xlim(cy - half, cy + half)
            ins.set_ylim(cz - half, cz + half)
            ins.set_aspect("equal")
            ins.set_xticks([])
            ins.set_yticks([])
            for sp in ins.spines.values():
                sp.set_color(PINK)
                sp.set_linewidth(2)
            ins.set_title(t["inset"].format(n=len(Q), h=num(float(d.size[2]))), color=LIGHT, fontsize=14, pad=8)

    # decision chip, as the node publishes it on /resense/decision
    if res.obstacle:
        head, sub, fc = t["stop"], t["obstacle"].format(d=num(res.nearest_distance)), PINK
    elif res.warning:
        head, sub, fc = t["caution"], "", CORRIDOR
    else:
        head, sub, fc = t["go"], t["clear"].format(d=getattr(res, "clear_distance", 0.0) or 0.0), GO
    chip = ax.text(60, 70, head, color="white", fontsize=34, weight="bold", va="center",
                   bbox=dict(boxstyle="round,pad=0.4", fc=fc, ec="none"))
    fig.canvas.draw()
    x_right = ax.transData.inverted().transform(chip.get_bbox_patch().get_window_extent())[1, 0]
    ax.text(x_right + 24, 70, sub, color="white", fontsize=26, va="center")
    import textwrap
    foot = "\n".join(textwrap.wrap(t["foot"].format(name=name, i=index), width=max(40, int((W - 120) / 12.5))))
    ax.text(60, H - 30, foot, color=LIGHT, fontsize=15, va="bottom", linespacing=1.4,
            bbox=dict(boxstyle="round,pad=0.4", fc=BG, ec="none", alpha=0.85))
    fig.savefig(path, dpi=120, facecolor=BG)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--npy", required=True, help="directory with cached *.npy frames (scripts/cache_frames.py)")
    ap.add_argument("--frame", type=int, required=True, help="frame to draw; the detector runs over 0..frame")
    ap.add_argument("--out", required=True, help="PNG; with --sequence a directory for frame_NNNNN.png")
    ap.add_argument("--sequence", type=int, default=None, metavar="FIRST",
                    help="draw every frame from FIRST to --frame (for a video: ffmpeg -i DIR/frame_%%05d.png)")
    ap.add_argument("--config", default=None)
    ap.add_argument("--lang", choices=sorted(TEXT), default="ru")
    ap.add_argument("--x-max", type=float, default=110.0)
    ap.add_argument("--name", default=None, help="recording name for the footer (default: the directory name)")
    ap.add_argument("--size", default="1920x1080", help="picture size WxH in pixels")
    ap.add_argument("--no-hud", action="store_true", help="only the cloud, the envelope and the boxes (no decision "
                    "chip, close-up or footer)")
    a = ap.parse_args()
    cfg = DetectorConfig.from_yaml(a.config) if a.config else DetectorConfig()
    det = Detector(cfg)
    name = a.name or os.path.basename(os.path.normpath(a.npy))
    W, H = (int(v) for v in a.size.lower().split("x"))
    if a.sequence is not None:
        os.makedirs(a.out, exist_ok=True)
    res = frame = None
    idx = 0
    for i, frame in iter_npy_frames(a.npy, cfg.sensor, limit=a.frame + 1, index_from_name=True):
        res, idx = det.process(frame), i
        if a.sequence is not None and i >= a.sequence:
            render(frame, res, os.path.join(a.out, f"frame_{i:05d}.png"), name, i, lang=a.lang, x_max=a.x_max,
                   W=W, H=H, hud=not a.no_hud)
        if i >= a.frame:
            break
    if res is None:
        sys.exit("no frames")
    if a.sequence is None:
        render(frame, res, a.out, name, idx, lang=a.lang, x_max=a.x_max, W=W, H=H, hud=not a.no_hud)
    print(f"{a.out}: frame {idx} obstacle={res.obstacle} clear_distance={res.clear_distance:.1f} m "
          f"detections={[round(d.distance, 1) for d in res.detections]}")


if __name__ == "__main__":
    main()
