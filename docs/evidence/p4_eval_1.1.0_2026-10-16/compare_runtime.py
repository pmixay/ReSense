#!/usr/bin/env python3
"""Runtime comparability of two X3 batteries of the same detector (PROTOCOL §B.1).

    compare_runtime.py <windows battery.json> <linux battery.json> <out.json>

Every metric of every entry must be equal; paths, hashes and timing are not metrics. Also checks that
both ran the same evaluated commit, driver and protocol (judge script bytes may differ only by CRLF,
which is checked against the committed LF scripts). Exit 0 equal, 1 different.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
JUDGE = ROOT / "docs/evidence/judgement_2026-10-13/scripts"


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), f"{path}/{k}")
        return out
    return [] if a == b else [{"path": path, "windows": a, "linux": b}]


def main(win_path, lin_path, out_path):
    win, lin = (json.loads(Path(p).read_text()) for p in (win_path, lin_path))
    crlf = {n: hashlib.sha256((JUDGE / n).read_bytes().replace(b"\n", b"\r\n")).hexdigest()
            for n in win["protocol"]["scripts"]}
    report = {
        "windows": {"path": win_path, "status": win["status"], "commit": win["evaluation"]["commit"],
                    "runtime": win["runtime"]["platform"]},
        "linux": {"path": lin_path, "status": lin["status"], "commit": lin["evaluation"]["commit"],
                  "runtime": lin["runtime"]["platform"]},
        "same_commit": win["evaluation"]["commit"] == lin["evaluation"]["commit"],
        "same_driver": win["protocol"]["driver_sha256"] == lin["protocol"]["driver_sha256"],
        "judge_scripts_equal_modulo_crlf": crlf == win["protocol"]["scripts"]
        and {n: hashlib.sha256((JUDGE / n).read_bytes()).hexdigest() for n in crlf} == lin["protocol"]["scripts"],
        "same_labels": win["labels"] == lin["labels"],
        "source_meta_equal": {b: win["sources"][b]["meta_sha256"] == lin["sources"][b]["meta_sha256"]
                              for b in win["sources"]},
        "entries": len(lin["entries"]),
        "differences": {},
    }
    for key in sorted(set(win["entries"]) | set(lin["entries"])):
        d = diff(win["entries"].get(key, {}).get("metrics"), lin["entries"].get(key, {}).get("metrics"))
        if d:
            report["differences"][key] = d
    report["judge_reproduction"] = {"windows": win.get("judge_reproduction", {}).get("passed"),
                                    "linux": lin.get("judge_reproduction", {}).get("passed")}
    report["equal"] = (not report["differences"] and report["same_commit"] and report["same_driver"]
                       and report["judge_scripts_equal_modulo_crlf"] and report["same_labels"])
    Path(out_path).write_text(json.dumps(report, indent=1) + "\n")
    print("EQUAL" if report["equal"] else f"DIFFERENT: {len(report['differences'])} entries", out_path)
    return 0 if report["equal"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
