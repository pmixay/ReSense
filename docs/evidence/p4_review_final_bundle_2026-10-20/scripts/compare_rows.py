"""Row-by-row comparison of two sets of per-frame outputs, with planted controls.

    python compare_rows.py gate  <dirA> <dirB> [label]   # the 15 gate pieces (*.jsonl, gate-run rows)
    python compare_rows.py x3    <rawA> <rawB> [label]   # <src>/<variant>/probe.jsonl, 40 cases
    python compare_rows.py jsonl <fileA> <fileB> [label] # one file (the Falcon record)

Reports rows compared, rows that differ after the latency normalisation (common.py), level differences and whether
each is explained by a latency message, and STOP rows lost / added. ``--control`` plants three known changes in a copy
of side A (a STOP flipped, one detection distance +0.01 m, one clear distance -0.1 m) and must find exactly those.
"""
import copy
import os
import sys

from common import flat, is_stop, jsonl, level_explained, normalise, rows_equal


def pairs_gate(a, b):
    for f in sorted(x for x in os.listdir(a) if x.endswith(".jsonl")):
        yield f, jsonl(f"{a}/{f}"), jsonl(f"{b}/{f}")


def pairs_x3(a, b):
    for s in sorted(os.listdir(a)):
        for v in sorted(os.listdir(f"{a}/{s}")):
            yield f"{s}/{v}", jsonl(f"{a}/{s}/{v}/probe.jsonl"), jsonl(f"{b}/{s}/{v}/probe.jsonl")


def pairs_file(a, b):
    yield os.path.basename(a), jsonl(a), jsonl(b)


def compare(pairs, label, plant=None):
    rows = diff = lvl = unexpl = lost = added = 0
    dets_lost = 0
    for name, A, B in pairs:
        assert len(A) == len(B), (name, len(A), len(B))
        if plant:
            plant(name, A)
        for a, b in zip(A, B):
            rows += 1
            na, nb = dict(flat(normalise(a))), dict(flat(normalise(b)))
            if na != nb:
                diff += 1
            from common import levels
            if levels(a) != levels(b):
                lvl += 1
                unexpl += not level_explained(a, b)
            sa, sb = is_stop(a), is_stop(b)
            lost += sb and not sa
            added += sa and not sb
            key = "detections" if "detections" in a else "dets"
            da = {repr(sorted(x.items())) for x in a[key]}
            dets_lost += sum(repr(sorted(x.items())) not in da for x in b[key])
    print(f"{label}: rows {rows} | rows differing after latency normalisation {diff} | level differences {lvl} "
          f"(not explained by a latency message: {unexpl}) | STOP rows lost {lost} added {added} | "
          f"detections of side B absent in side A {dets_lost}")
    return rows, diff, unexpl, lost, added, dets_lost


def planted(kind):
    done = set()

    def plant(name, A):
        if kind == "gate":
            if name == "doubleT_obstacle.jsonl" and "d" not in done:
                A[9]["detections"][0]["distance"] += 0.01
                done.add("d")
            if name == "new_data_5.jsonl" and "o" not in done:
                A[700]["obstacle"] = not A[700]["obstacle"]
                done.add("o")
            if name == "squareT_platform_squareT_switch.jsonl" and "c" not in done:
                A[300]["clear_distance"] -= 0.1
                done.add("c")
        elif kind == "jsonl":
            if "o" not in done:
                for a in A[2000:]:
                    if a["decision"] == "STOP":
                        a["decision"] = "CAUTION"
                        a["obstacle"] = False
                        done.add("o")
                        break
        else:
            if name == "cloud_with_fake_obj/nominal" and "o" not in done:
                for a in A[400:]:
                    if a["decision"] == "STOP":
                        a["decision"] = "CAUTION"
                        a["obstacle"] = False
                        done.add("o")
                        break
            if name == "doubleT_obstacle/hz5" and "d" not in done:
                for a in A:
                    if a["dets"]:
                        a["dets"] = a["dets"][1:]
                        done.add("d")
                        break
    return plant


if __name__ == "__main__":
    mode, a, b = sys.argv[1:4]
    label = next((x for x in sys.argv[4:] if not x.startswith("--")), mode)
    fn = {"gate": pairs_gate, "x3": pairs_x3, "jsonl": pairs_file}[mode]
    if "--control" in sys.argv:
        r = compare(fn(a, b), label + " [planted control]", planted(mode))
        expect = {"gate": 3, "x3": 2, "jsonl": 1}[mode]
        print("control", "FOUND" if r[1] == expect else "MISSED", f"(planted {expect}, found {r[1]})")
    else:
        compare(fn(a, b), label)
