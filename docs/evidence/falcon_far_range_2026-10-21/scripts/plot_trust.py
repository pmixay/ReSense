#!/usr/bin/env python3
"""Figure: the far trusted range per frame (19.10 candidate vs the 21.10 candidate) against the main person's
raw distance, and the STOP frames of v1.2.0 / 19.10 / 21.10, frames 2550-3150.

    plot_trust.py --base v120_base.jsonl --c89 v120_cand_trace.jsonl --cand cand.jsonl --out figs/trust.png"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

LR = Path(__file__).resolve().parents[2] / "falcon_long_range_2026-10-19"
BLUE, ORANGE, INK, MUTED = "#2a78d6", "#eb6834", "#2b2b2a", "#8a8980"


def load(p):
    return [json.loads(line) for line in open(p)]


def main():
    ap = argparse.ArgumentParser()
    for k in ("base", "c89", "cand", "out"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--lo", type=int, default=2550)
    ap.add_argument("--hi", type=int, default=3150)
    a = ap.parse_args()
    B, C9, C = load(a.base), load(a.c89), load(a.cand)
    cal = json.loads((LR / "person_calibration.json").read_text())
    pr = sorted((r["frame"], r["x"]) for r in cal["rows"] if r["episode"].startswith("main"))
    f = np.arange(a.lo, a.hi)
    px = np.interp(f, [p[0] for p in pr], [p[1] for p in pr])
    fig, ax = plt.subplots(2, 1, figsize=(12, 7), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for rows, col, lab in ((C9, ORANGE, "19.10 candidate (one side, capped at the near trust)"),
                           (C, BLUE, "21.10 candidate (axis_stable)")):
        v = np.array([((rows[i].get("far") or {}).get("valid") or np.nan) for i in f])
        ax[0].plot(f, v, color=col, lw=1.5, label=lab)
    ax[0].plot(f, px, color=INK, lw=2, ls="--", label="main person, raw distance")
    ax[0].set_ylabel("m")
    ax[0].set_title("far trusted range (far.valid) per frame; gaps = no far axis")
    ax[0].legend(frameon=False, loc="upper right")
    ax[0].grid(alpha=.25)
    for k, (rows, lab) in enumerate(((B, "v1.2.0"), (C9, "19.10 cand"), (C, "21.10 cand"))):
        s = [i for i in f if rows[i]["decision"] == "STOP"]
        ax[1].scatter(s, [k] * len(s), marker="|", s=80, color=INK)
    ax[1].set_yticks([0, 1, 2], ["v1.2.0", "19.10 cand", "21.10 cand"])
    ax[1].set_title("STOP frames")
    ax[1].set_xlabel("frame (10 Hz)")
    ax[1].set_ylim(-0.6, 2.6)
    for x in ax:
        x.spines[["top", "right"]].set_visible(False)
    plt.tight_layout()
    plt.savefig(a.out, dpi=80)


if __name__ == "__main__":
    main()
