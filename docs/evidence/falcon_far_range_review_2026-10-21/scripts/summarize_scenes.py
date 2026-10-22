#!/usr/bin/env python3
"""Table of the scene runs: v1.2.0 (wt_v120) vs candidate (wt_cand) per scene, with evalrows.evaluate.

    summarize_scenes.py <specdir> <rundir> --json out.json --md out.md
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evalrows import evaluate  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specdir")
    ap.add_argument("rundir")
    ap.add_argument("--json", required=True)
    ap.add_argument("--md", required=True)
    a = ap.parse_args()
    idx = json.loads((Path(a.specdir) / "index.json").read_text())
    res, lines = {}, []
    hdr = ("| scene | run | decisions G/C/S | STOP eps | false eps | STOP frames w/ unassoc det | target: first STOP (x) | "
           "held STOP (x) | STOP frames | GO with target inside clear | far frames / max valid |")
    lines += [hdr, "|" + "---|" * 11]
    for name, frames in idx:
        spec = json.loads((Path(a.specdir) / f"{name}.json").read_text())
        res[name] = {}
        for w in ("wt_v120", "wt_cand"):
            p = Path(a.rundir) / f"{name}__{w}.jsonl"
            if not p.exists() or not (Path(a.rundir) / f"{name}__{w}.meta.json").exists():
                continue
            rows = [json.loads(line) for line in open(p)]
            e = evaluate(rows, spec, int(frames.split(":")[0]))
            res[name][w] = e
            d = e["decisions"]
            tg = "; ".join(f"{n}: {t['first_stop_x']}" for n, t in e["targets"].items() if t.get("present"))
            held = "; ".join(f"{t['held_stop_x']}" for n, t in e["targets"].items() if t.get("present"))
            sf = "; ".join(f"{t['stop_frames']}/{t['present']}" for n, t in e["targets"].items() if t.get("present"))
            go = "; ".join(f"{t.get('go_inside_clear', 0)}" for n, t in e["targets"].items() if t.get("present"))
            lines.append(f"| {name} | {'v1.2.0' if w == 'wt_v120' else 'cand'} | {d.get('GO', 0)}/{d.get('CAUTION', 0)}/{d.get('STOP', 0)} | "
                         f"{e['stop_episodes']} | {e['false_episodes']} {e['false_episode_frames'][:4] if e['false_episodes'] else ''} | "
                         f"{e['stop_frames_with_unassociated_det']} | {tg} | {held} | {sf} | {go} | {e['far_frames']} / {e['max_far_valid']} |")
    Path(a.json).write_text(json.dumps(res, indent=1))
    Path(a.md).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
