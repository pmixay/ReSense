#!/usr/bin/env python3
"""Plot the already-computed crosswalk; no detector, ICP or data fitting."""
import gzip
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    with gzip.open(HERE / "crosswalk_rows.json.gz", "rt") as stream:
        rows = json.load(stream)
    report = json.loads((HERE / "report.json").read_text())
    outputs = {}
    for label, data in rows.items():
        frames = data["frames"]
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, constrained_layout=True)
        indices = np.arange(len(frames))
        distances = (90, 135) if label == "B" else (80, 100, 120)
        for distance in distances:
            values = [abs(row["errors_at_m"][str(distance)])
                      if str(distance) in row["errors_at_m"] and row["axis_valid_m"] >= distance
                      else np.nan for row in frames]
            axes[0].plot(indices, values, lw=1.3, label=f"Raw axis at {distance} m, within axis trust")
        if label == "B":
            shown = [p for p in data["points"] if p["distance_m"] == 90
                     and p["display_error_signed_m"] is not None]
            axes[0].scatter([p["frame"] for p in shown],
                            [abs(p["display_error_signed_m"]) for p in shown],
                            s=12, color="#20804e", label="Displayed axis at 90 m, actually visible", zorder=5)
        axes[0].axhline(1.05, color="#7a7a7a", ls=":", label="1.05 m reference threshold")
        axes[0].set_ylabel("Lateral path-proxy error (m)")
        axes[0].legend(loc="upper left", fontsize=8)
        axes[0].set_title(f"{label}: {report['recordings'][label]['recording']} — archived evidence")
        axes[1].plot(indices, [f["axis_valid_m"] for f in frames], label="Raw trusted axis range", color="#386aaf")
        axes[1].plot(indices, [f["monitored_v110_m"] for f in frames], label="B6 monitored range (1.1.0)", color="#b87813")
        if label == "B":
            axes[1].plot(indices, [f["N1_solid_m"] for f in frames], label="N1 solid display range (f5ff15f)", color="#20804e")
        else:
            axes[1].text(.02, .05, "No saved N1 display capture for C; no display result inferred.",
                         transform=axes[1].transAxes, fontsize=9)
        for ax in axes:
            ax.grid(alpha=.2)
            ax.set_xlim(0, len(frames) - 1)
            ax.set_ylim(bottom=0)
        axes[1].set_xlabel("Recording frame")
        axes[1].set_ylabel("Range (m)")
        axes[1].legend(loc="upper right", fontsize=8)
        fig.suptitle("A shorter visible gauge does not correct the detector's curved path", fontsize=12)
        destination = HERE / f"curve_{label}.png"
        fig.savefig(destination, dpi=150)
        plt.close(fig)
        outputs[destination.name] = digest(destination)
    receipt = {"script_sha256": digest(Path(__file__)),
               "report_sha256": digest(HERE / "report.json"),
               "rows_sha256": digest(HERE / "crosswalk_rows.json.gz"), "figures": outputs,
               "scope": "Plots only archived path-reference errors and saved ranges. Gaps are unavailable path references or distances outside axis trust, not zero error. No detector/ICP rerun."}
    (HERE / "figure_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
