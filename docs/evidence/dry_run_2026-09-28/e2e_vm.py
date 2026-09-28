"""End-to-end latency of the 28.09 VM captures (docs/evidence/{dry_run,offline}_2026-09-28), current
results and all frame results, with the definitions of docs/evidence/node_input_2026-09-28/e2e_all_frames.py.

    python3 docs/evidence/dry_run_2026-09-28/e2e_vm.py
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
EV = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(EV, "node_input_2026-09-28"))
import e2e_all_frames as e  # noqa: E402  (its folder; it puts scripts/ on the path)

for folder in ("dry_run_2026-09-28", "offline_2026-09-28"):
    for path in sorted(glob.glob(os.path.join(EV, folder, "**", "*_status.jsonl.gz"), recursive=True)):
        frames, _ = e.load(path)
        current = [e.age_ms(f) for f in frames if (f.get("freshness") or {}).get("valid") is True and e.age_ms(f) is not None]
        every = [e.age_ms(f) for f in frames if e.age_ms(f) is not None]
        print(f"{os.path.relpath(path, EV):68s} current {e.stats(current):>22s}   all {e.stats(every):>22s}")
