#!/usr/bin/env python3
"""Score a synthetic_platform run with the jury scorer, on the labelled frames only.

    score_platform.py <run .jsonl> <labels.json> <out.json>

The labels cover frames 0-314 (exact reference); the run covers all 386 frames. Unlabelled frames would
count every STOP as unmatched, so the run is restricted to the labelled frames first, then the judge's
unchanged ``score_objects.py`` scores it.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SCORER = Path(__file__).resolve().parents[2] / "judgement_2026-10-13/scripts/score_objects.py"


def main():
    run, labels, out = sys.argv[1:4]
    keep = {int(k) for k in json.load(open(labels)) if k != "_meta"}
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as f:
        for line in open(run):
            if json.loads(line)["i"] in keep:
                f.write(line)
    subprocess.run([sys.executable, str(SCORER), f.name, labels, out], check=True, stdout=subprocess.DEVNULL)
    Path(f.name).unlink()
    print(out, len(keep), "labelled frames scored")


if __name__ == "__main__":
    main()
