"""The organizers' object recording (`cloud_with_fake_obj`) scored from an offline run: per object,
the frames it is labelled and inside the envelope, the STOP frames whose detection lies within 3 m of
the object's box along the track, CAUTION-only frames and the first STOP distance; plus STOP
detections near no labelled object.

    python score_setO.py <labels/cloud_with_fake_obj.json> <run.jsonl>
"""
import json
import sys


def near(dets, box):
    return [d for d in dets if box[0][0] - 3 <= d["distance"] <= box[1][0] + 3]


def score(labels_path: str, run_path: str) -> dict:
    lab = json.load(open(labels_path))
    rows = [json.loads(line) for line in open(run_path)]
    stray = 0
    for r in rows:
        objs = [o for o in lab.get(f"{r['frame']:05d}", []) if o["plausible"]]
        stray += sum(1 for d in r["detections"] if not any(near([d], o["bbox"]) for o in objs))
    out = {}
    for name, meta in lab["_meta"]["objects"].items():
        f0, f1 = meta["frames"]
        st = dict(in_gauge_intent=meta["in_gauge"], size=meta["size_m"], frames_labelled=0, frames_in_env=0,
                  stop_frames=0, stop_frames_in_env=0, caution_frames=0, first_stop_m=None,
                  env_first_m=None, env_last_m=None)
        for r in rows[f0:f1 + 1]:
            rows_o = [x for x in lab.get(f"{r['frame']:05d}", []) if x["name"] == name and x["plausible"]]
            if not rows_o:
                continue
            x = rows_o[0]
            st["frames_labelled"] += 1
            inside = x["n_in_envelope"] > 0
            if inside:
                st["frames_in_env"] += 1
                st["env_first_m"] = st["env_first_m"] or x["distance"]
                st["env_last_m"] = x["distance"]
            hit = near(r["detections"], x["bbox"])
            if hit:
                st["stop_frames"] += 1
                st["stop_frames_in_env"] += inside
                if st["first_stop_m"] is None:
                    st["first_stop_m"] = round(hit[0]["distance"], 1)
            elif near(r["warnings"], x["bbox"]):
                st["caution_frames"] += 1
        out[name] = st
    return dict(objects=out, stop_detections_near_no_object=stray,
                frames_with_stop=sum(r["obstacle"] for r in rows), frames=len(rows))


if __name__ == "__main__":
    print(json.dumps(score(*sys.argv[1:]), indent=1, ensure_ascii=False))
