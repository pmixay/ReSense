#!/usr/bin/env python3
"""Per-frame parity of two regression-gate work directories (protocol step 4).

    python compare_outputs.py <control work dir> <candidate work dir> --out parity.json

Every ``<name>.jsonl`` / ``<name>_<k>.jsonl`` of the control must exist in the candidate with the
same rows. A row is compared without ``timing_ms`` and without the latency-derived health fields:
``latency_p95_ms``, the ``latency p95 ...`` messages and a ``level`` that differs only where
exactly one run carries such a message (``decision_level`` must always match: with
``health.latency_affects_decision`` off a latency warning never reaches it). ``setF_straight.json``
is compared without ``summary.wall_s``. ``health.blocked_sectors`` (the histogram's output) is also
counted separately and must match on every frame. Both runs must hold exactly the same capture
files, all of ``EXPECTED`` and none empty, and set F must hold its 30 sequences with rows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EXPECTED = ("cloud_with_fake_obj", "doubleT_obstacle", "doubleT_platform", "roundT_doubleT",
            "roundT_pressureGate_roundT", "roundT_squareT_pressureGate_squareT",
            "squareT_platform_squareT_switch", *(f"new_data_{i}" for i in range(8)))


def rows(path: Path) -> list:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def latency_messages(health: dict) -> list:
    return [m for m in health.get("messages", []) if m.startswith("latency p95 ")]


def normalized(row: dict) -> tuple[dict, bool]:
    """(row without timing, whether its health carries a latency message)."""
    out = {k: v for k, v in row.items() if k != "timing_ms"}
    health = dict(out.get("health") or {})
    late = bool(latency_messages(health))
    health.pop("latency_p95_ms", None)
    health["messages"] = [m for m in health.get("messages", []) if not m.startswith("latency p95 ")]
    out["health"] = health
    return out, late


def compare_rows(a: dict, b: dict) -> str | None:
    """None when equal under the protocol; else the reason."""
    na, la = normalized(a)
    nb, lb = normalized(b)
    if na == nb:
        return None
    ha, hb = na["health"], nb["health"]
    levels = ("level",)
    if la != lb and {k: v for k, v in na.items() if k != "health"} == {k: v for k, v in nb.items() if k != "health"} \
            and {k: v for k, v in ha.items() if k not in levels} == {k: v for k, v in hb.items() if k not in levels}:
        return None                      # the level differs only by one run's latency warning
    keys = sorted(k for k in set(na) | set(nb) if na.get(k) != nb.get(k))
    if keys == ["health"]:
        keys = ["health." + k for k in sorted(set(ha) | set(hb)) if ha.get(k) != hb.get(k)]
    return ",".join(keys)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("control", type=Path)
    ap.add_argument("candidate", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    report = {"schema": "resense-gate-output-parity-v1", "recordings": {}, "frames": 0,
              "changed_frames": 0, "blocked_sectors_changed_frames": 0, "latency_only_frames": 0}
    names = {p.stem for p in a.control.glob("*.jsonl")}
    if names != {p.stem for p in a.candidate.glob("*.jsonl")} or names != set(EXPECTED):
        raise SystemExit(f"capture files differ from each other or from the expected {len(EXPECTED)}")
    for path in sorted(a.control.glob("*.jsonl")):
        other = a.candidate / path.name
        ra, rb = rows(path), rows(other)
        if not ra:
            raise SystemExit(f"{path.name}: no rows")
        if len(ra) != len(rb):
            raise SystemExit(f"{path.name}: {len(ra)} control rows, {len(rb)} candidate rows")
        changed, blocked, latency_only, examples = 0, 0, 0, []
        for x, y in zip(ra, rb):
            blocked += x["health"].get("blocked_sectors") != y["health"].get("blocked_sectors")
            reason = compare_rows(x, y)
            if reason is not None:
                changed += 1
                if len(examples) < 5:
                    examples.append({"frame": x.get("frame"), "frame_id": x.get("frame_id"), "fields": reason})
            elif normalized(x)[0] != normalized(y)[0]:
                latency_only += 1
        report["recordings"][path.stem] = {"frames": len(ra), "changed_frames": changed,
                                           "blocked_sectors_changed_frames": blocked,
                                           "latency_level_only_frames": latency_only, "examples": examples}
        report["frames"] += len(ra)
        report["changed_frames"] += changed
        report["blocked_sectors_changed_frames"] += blocked
        report["latency_only_frames"] += latency_only
    setf_a, setf_b = (json.loads((d / "setF_straight.json").read_text()) for d in (a.control, a.candidate))
    wall = {"control": setf_a["summary"].pop("wall_s", None), "candidate": setf_b["summary"].pop("wall_s", None)}
    setf_rows = sum(len(s.get("rows", [])) for s in setf_a.get("sequences", []))
    if len(setf_a.get("sequences", [])) != 30 or not setf_rows:
        raise SystemExit("set F must hold 30 sequences with rows")
    report["set_F"] = {"equal_except_wall_s": setf_a == setf_b, "wall_s": wall, "rows": setf_rows}
    report["passed"] = (report["frames"] > 0 and report["changed_frames"] == 0
                        and report["blocked_sectors_changed_frames"] == 0 and report["set_F"]["equal_except_wall_s"])
    a.out.write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("passed", "frames", "changed_frames",
                                             "blocked_sectors_changed_frames", "latency_only_frames")}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
