#!/usr/bin/env python3
"""Look at the raw points around the detection in a few frames of the cut bag (top-down and side view).

    RESENSE_REPO=<tree> plot_person.py --bag BAG_DIR --first-frame A --record l16.jsonl.xz --frames 2955,2972,3000,3100 --out pic.png

For each frame the points of the bag's message (node decode, 2.5-250 m, the sensor's own axes: x forward, y left,
z up) near the record's nearest detection or warning at that frame are drawn: left the view from above (x forward,
y left), right the side view (x forward, z up). The record's centre is in the detector's vehicle frame, where the
mount pitch (-2.39 deg) is removed; at 100 m that tilts z by 4 m, so only x and y are taken from the record: points
within 1.5 m in x and 1.2 m in y of it are orange, and the height window of both views is centred on their median z
(the person's height is read from the picture, not from the record). Pure numpy and Pillow, no matplotlib.
"""
from __future__ import annotations

import argparse
import json
import lzma
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

REPO = os.environ.get("RESENSE_REPO")
if not REPO:
    sys.exit("set RESENSE_REPO to the tree being evaluated")
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "ros2_ws/src/resense_ros"))
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

SCALE = 36            # pixels per metre
HALF_X, HALF_Y = 10.0, 4.0
Z_HALF = 3.0


def panel(draw, ox, oy, w, h, pts_u, pts_v, hi, u0, v0, u_span, v_span, title):
    draw.rectangle([ox, oy, ox + w, oy + h], outline=(120, 120, 120))
    for (u, v), is_hi in zip(zip(pts_u, pts_v), hi):
        px = ox + int((u - u0) / u_span * w)
        py = oy + h - int((v - v0) / v_span * h)
        if ox <= px < ox + w and oy <= py < oy + h:
            draw.rectangle([px, py, px + 1, py + 1], fill=(255, 140, 0) if is_hi else (90, 90, 90))
    draw.text((ox + 4, oy + 3), title, fill=(0, 0, 0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bag", required=True)
    ap.add_argument("--first-frame", type=int, required=True)
    ap.add_argument("--record", required=True)
    ap.add_argument("--centers", default="", help="take the objects from this replay (.jsonl with a frame field) "
                    "instead of the record, e.g. the cold-start replay of the bag")
    ap.add_argument("--frames", required=True, help="comma list of frame numbers of the recording")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    want = [int(v) for v in a.frames.split(",")]
    with (lzma.open(a.record, "rt") if a.record.endswith(".xz") else open(a.record)) as fh:
        record = [json.loads(line) for line in fh]
    shown = record
    if a.centers:
        by_frame = {r.get("frame", r["i"]): r for r in map(json.loads, open(a.centers))}
        shown = [by_frame.get(f) for f in range(len(record))]
    w, h = int(2 * HALF_X * SCALE), int(2 * HALF_Y * SCALE)
    hz = int(2 * Z_HALF * SCALE)
    sheet = Image.new("RGB", (w + 12 + w, len(want) * (max(h, hz) + 26) + 6), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    wanted = {f: k for k, f in enumerate(want)}
    k = -1
    for db3 in jr.db3_files(a.bag):
        for ts, topic, raw in jr.iter_raw(db3):
            k += 1
            frame = a.first_frame + k
            if frame not in wanted:
                continue
            msg = fastcloud.parse_pointcloud2(raw)
            xyz_s, _, _, _, _ = fastcloud.decode(fastcloud.packed(msg), 2.5, 250.0)
            xyz = xyz_s
            r = shown[frame]
            if r is None:
                continue
            obj = (r["dets"] or r["warns"] or [None])[0]
            if obj is None:
                continue
            cx, cy = obj["c"][0], obj["c"][1]
            core = (np.abs(xyz[:, 0] - cx) < 1.5) & (np.abs(xyz[:, 1] - cy) < 1.2)
            if not core.any():
                continue
            cz = float(np.median(xyz[core, 2]))
            z_lo, z_hi = cz - Z_HALF, cz + Z_HALF
            box = (np.abs(xyz[:, 0] - cx) < HALF_X) & (np.abs(xyz[:, 1] - cy) < HALF_Y) & (xyz[:, 2] > z_lo) & (xyz[:, 2] < z_hi)
            p = xyz[box]
            hi = (np.abs(p[:, 0] - cx) < 1.5) & (np.abs(p[:, 1] - cy) < 1.2)
            y0 = 4 + wanted[frame] * (max(h, hz) + 26)
            title = (f"frame {frame}  t={r['bag_t'] - record[0]['bag_t']:.1f} s  {r['decision']}  "
                     f"{'detection' if r['dets'] else 'warning'} {obj['d']} m lat {obj['lat']} n={obj['n']}  "
                     f"size {obj['size']}  box points {len(p)}  centre z {cz:.2f}")
            draw.text((4, y0), title, fill=(0, 0, 0))
            panel(draw, 0, y0 + 14, w, h, p[:, 0], p[:, 1], hi, cx - HALF_X, cy - HALF_Y, 2 * HALF_X, 2 * HALF_Y,
                  "from above: x forward (right), y left (up)")
            panel(draw, w + 12, y0 + 14, w, hz, p[:, 0], p[:, 2], hi, cx - HALF_X, z_lo, 2 * HALF_X, 2 * Z_HALF,
                  f"side: x forward, z up (sensor frame, {z_lo:.1f}..{z_hi:.1f} m)")
            near = p[hi]
            if len(near):
                print(f"frame {frame}: orange points {len(near)}, x {near[:, 0].min():.2f}..{near[:, 0].max():.2f}, "
                      f"y {near[:, 1].min():.2f}..{near[:, 1].max():.2f}, z {near[:, 2].min():.2f}..{near[:, 2].max():.2f}")
    sheet.save(a.out)
    print("wrote", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
