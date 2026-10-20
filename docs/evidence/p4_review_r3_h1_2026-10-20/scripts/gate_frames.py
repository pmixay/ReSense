"""Every gate row whose detector decision (STOP = obstacle, CAUTION = advisory warning), detections or warnings
differ between two gate work directories (the shipped run and a switch-off run), per file, with both sides'
objects. Only these three are compared here; cmp_frames.py checks every other non-timing field.

    python gate_frames.py <shipped work> <switch-off work>
"""
import glob
import json
import os
import sys


def objs(ds):
    return [(o["id"], o["distance"], o["lateral"], o["zone"], o["reason"], o["kind"], round(o["size"][2], 2))
            for o in ds]


def main():
    A, B = sys.argv[1], sys.argv[2]
    tot = {"rows": 0, "dec": 0, "dets": 0, "stop_lost": 0, "stop_added": 0}
    for fa in sorted(glob.glob(os.path.join(A, "*.jsonl"))):
        name = os.path.basename(fa)[:-6]
        la = [json.loads(x) for x in open(fa)]
        lb = [json.loads(x) for x in open(os.path.join(B, os.path.basename(fa)))]
        assert len(la) == len(lb), name
        rows = []
        for i, (x, y) in enumerate(zip(la, lb)):
            tot["rows"] += 1
            # decision on the raw detection lists; the latency-driven decision_level is compared by cmp_frames
            dx = "STOP" if x["obstacle"] else ("CAUTION" if x["warning"] else "-")
            dy = "STOP" if y["obstacle"] else ("CAUTION" if y["warning"] else "-")
            if (dx, x["detections"], x["warnings"]) == (dy, y["detections"], y["warnings"]):
                continue
            tot["dets"] += 1
            tot["dec"] += dx != dy
            tot["stop_lost"] += dx == "STOP" and dy != "STOP"
            tot["stop_added"] += dy == "STOP" and dx != "STOP"
            rows.append((i, x["frame_id"], dx, dy, objs(x["detections"]), objs(x["warnings"]),
                         objs(y["detections"]), objs(y["warnings"])))
        if rows:
            print(f"== {name}: {len(rows)} rows differ")
            for i, fid, dx, dy, xd, xw, yd, yw in rows:
                print(f"  row {i} {fid}: shipped {dx} -> off {dy}")
                print(f"      shipped dets {xd} warns {xw}")
                print(f"      off     dets {yd} warns {yw}")
    print("TOTAL", json.dumps(tot))


if __name__ == "__main__":
    main()
