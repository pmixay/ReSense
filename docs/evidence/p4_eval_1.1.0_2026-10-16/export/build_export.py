#!/usr/bin/env python3
"""P4 case register and numeric export (proposed format v1, see FORMAT.md).

    python docs/evidence/p4_eval_1.1.0_2026-10-16/export/build_export.py [--check]

Reads only committed evidence and writes, next to this script:
  case_register.csv / .json   one row per evaluated (or registered) case and detector version
  numbers.csv / .json         one row per number: stage, case, version, metric, value, unit, status,
                              scope, and the source file + JSON pointer + source SHA-256
With --check (or always after writing) every exported number is re-read from its source through its
JSON pointer and compared; exit 1 on any difference. Nothing is computed that is not in a source file,
except the totals marked ``derived`` (their formula is in the row).
"""
import csv
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EV = ROOT / "docs/evidence"
SCHEMA = "resense-p4-export-v1"
ALIAS = {"roundT_squareT_pressureGate_squareT": "A", "roundT_doubleT": "B", "roundT_pressureGate_roundT": "C",
         "squareT_platform_squareT_switch": "S/D", "doubleT_obstacle": "obstacle", "doubleT_platform": "platform",
         "cloud_with_fake_obj": "Set O"}
VERSIONS = {"707ea9c": ("v1.0.0", "707ea9cda051369326fb9407c42488c1033dad76"),
            "1.1.0": ("1.1.0", "492e407b76d9dee7852f9e1884200e27939f0fca")}
RECORD_COLS = ["case_id", "stage", "recording", "alias", "object", "variant", "version", "commit", "runtime",
               "status", "scope", "result", "evidence"]
NUM_COLS = ["stage", "case_id", "version", "metric", "value", "unit", "status", "scope", "runtime", "source",
            "pointer", "source_sha256", "derived"]

_cache = {}


def load(rel):
    if rel not in _cache:
        p = ROOT / rel
        _cache[rel] = (json.loads(p.read_text()), hashlib.sha256(p.read_bytes()).hexdigest())
    return _cache[rel]


def get(doc, pointer):
    for part in pointer.strip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def esc(s):
    return str(s).replace("~", "~0").replace("/", "~1")


class Export:
    def __init__(self):
        self.cases, self.nums = [], []

    def num(self, stage, case, version, metric, rel, pointer, unit, status, scope, runtime):
        doc, sha = load(rel)
        self.nums.append({"stage": stage, "case_id": case, "version": version, "metric": metric,
                          "value": get(doc, pointer), "unit": unit, "status": status, "scope": scope,
                          "runtime": runtime, "source": rel, "pointer": pointer, "source_sha256": sha, "derived": ""})

    def derived(self, stage, case, version, metric, value, unit, status, scope, runtime, formula):
        self.nums.append({"stage": stage, "case_id": case, "version": version, "metric": metric, "value": value,
                          "unit": unit, "status": status, "scope": scope, "runtime": runtime, "source": "",
                          "pointer": "", "source_sha256": "", "derived": formula})

    def case(self, **kw):
        self.cases.append({c: kw.get(c, "") for c in RECORD_COLS})


LINUX = "linux-cloud-4vcpu (OPENBLAS_CORETYPE=Haswell)"
WIN = "windows-team-computer"


def x3(ex):
    runs = [("v1.0.0", "707ea9c", "docs/evidence/p4_start_2026-10-15/battery_707ea9c.json", WIN, "MEASURED"),
            ("v1.0.0", "707ea9c", "docs/evidence/p4_eval_1.1.0_2026-10-16/battery_707ea9c_linux_haswell.json", LINUX,
             "MEASURED (control, equal to Windows on all 40)"),
            ("1.1.0", "1.1.0", "docs/evidence/p4_eval_1.1.0_2026-10-16/battery_1.1.0_linux_haswell.json", LINUX,
             "PASS vs control")]
    for version, key, rel, runtime, status in runs:
        doc, _ = load(rel)
        for entry, e in doc["entries"].items():
            bag, variant = entry.split("/")
            cid = f"x3/{bag}/{variant}"
            m = e["metrics"]
            res = f"STOP {m['stop_frames']}/{m['frames']} frames, {m['stop_episodes']} episodes"
            ex.case(case_id=cid, stage="X3", recording=bag, alias=ALIAS[bag], object="labelled objects" if "objects" in m
                    else "none (empty)", variant=variant, version=version, commit=VERSIONS[key][1], runtime=runtime,
                    status=status, scope="development data (in-sample)", result=res, evidence=rel)
            base = f"/entries/{esc(entry)}/metrics"
            for metric, unit in (("frames", "frames"), ("stop_frames", "frames"), ("stop_episodes", "episodes")):
                ex.num("X3", cid, version, metric, rel, f"{base}/{metric}", unit, status, "in-sample", runtime)
            if "false_stop_episodes" in m:
                ex.num("X3", cid, version, "false_stop_episodes", rel, f"{base}/false_stop_episodes", "episodes",
                       status, "in-sample", runtime)
            for k in ("outside_false_stop_frames", "outside_false_stop_episodes", "unmatched_stop_frames",
                      "unmatched_stop_episodes"):
                if k in m:
                    ex.num("X3", cid, version, k, rel, f"{base}/{k}", "frames" if k.endswith("frames") else "episodes",
                           status, "in-sample", runtime)
            for name, o in m.get("objects", {}).items():
                ob = f"{base}/objects/{esc(name)}"
                if o["in_gauge"]:
                    ex.num("X3", cid, version, f"object.{name}.inside_stop_rows", rel, f"{ob}/inside_stop_rows",
                           "rows", status, "in-sample", runtime)
                    ex.num("X3", cid, version, f"object.{name}.inside_visible_rows", rel, f"{ob}/inside_visible_rows",
                           "rows", status, "in-sample", runtime)
                    if o["first_stop_m"] is not None:
                        ex.num("X3", cid, version, f"object.{name}.first_stop_m", rel, f"{ob}/first_stop_m", "m",
                               status, "in-sample", runtime)
                else:
                    ex.num("X3", cid, version, f"object.{name}.outside_stop_rows", rel, f"{ob}/outside_stop_rows",
                           "rows", status, "in-sample", runtime)
                    ex.num("X3", cid, version, f"object.{name}.outside_stop_episodes", rel,
                           f"{ob}/outside_stop_episodes", "episodes", status, "in-sample", runtime)
            if "objects" in m:
                ins = sum(o["inside_stop_rows"] for o in m["objects"].values())
                vis = sum(o["inside_visible_rows"] for o in m["objects"].values())
                ex.derived("X3", cid, version, "inside_matched_stop_rows", ins, "rows", status, "in-sample", runtime,
                           "sum of object.*.inside_stop_rows")
                ex.derived("X3", cid, version, "inside_visible_rows", vis, "rows", status, "in-sample", runtime,
                           "sum of object.*.inside_visible_rows")
    rel = "docs/evidence/p4_eval_1.1.0_2026-10-16/comparison_rows.json"
    doc, _ = load(rel)
    ex.num("X3", "x3/acceptance", "1.1.0", "acceptance_passed", rel, "/passed", "bool", "PASS", "in-sample", LINUX)
    ex.derived("X3", "x3/acceptance", "1.1.0", "acceptance_rows", len(doc["rows"]), "rows", "PASS", "in-sample", LINUX,
               "len(rows) in comparison_rows.json")
    ex.derived("X3", "x3/acceptance", "1.1.0", "acceptance_rows_failing", sum(not r["passed"] for r in doc["rows"]),
               "rows", "PASS", "in-sample", LINUX, "count(rows where passed is false)")


def x1(ex):
    rel = "docs/evidence/range_attribution_2026-10-16/x1_summary.json"
    doc, _ = load(rel)
    for case, entry in doc["cases"].items():
        for key in ("707ea9c", "1.1.0"):
            version = VERSIONS[key][0]
            e = entry[key]
            cid = f"x1/{case}"
            js = e.get("judge_summary")
            spec = json.loads((ROOT / f"docs/evidence/range_attribution_2026-10-16/{key}/{case}.attrib.json")
                              .read_text())["args"]
            res = (f"STOP hits {e['stop_hits']}/{e['visible']} visible; first STOP {js['first_stop_X']} m, held "
                   f"{js['held_from_X']} m" if js else f"STOP hits {e['stop_hits']}/{e['visible']} visible rows (windows)")
            ex.case(case_id=cid, stage="X1", recording=spec[0].rsplit("/", 1)[-1], alias=case.split("_")[0],
                    object=case, variant=" ".join(spec[3:]) if js else "windows small_center 300-340, thin_hanging "
                    "760-790", version=version, commit=VERSIONS[key][1], runtime=LINUX, status="MEASURED (attributed)",
                    scope="development data (in-sample), synthetic ray-cast object" if js else
                    "development data (in-sample), organizers' synthetic objects", result=res, evidence=rel)
            base = f"/cases/{esc(case)}/{esc(key)}"
            st = "MEASURED"
            ex.num("X1", cid, version, "visible_frames", rel, f"{base}/visible", "frames", st, "in-sample", LINUX)
            ex.num("X1", cid, version, "stop_hit_frames", rel, f"{base}/stop_hits", "frames", st, "in-sample", LINUX)
            if js:
                for k, unit in (("first_visible_X", "m"), ("first_stop_X", "m"), ("held_from_X", "m")):
                    if js[k] is not None:
                        ex.num("X1", cid, version, k.replace("_X", "_m"), rel, f"{base}/judge_summary/{k}", unit, st,
                               "in-sample", LINUX)
            for cause, bins in e["causes"].items():
                for b in bins:
                    ex.num("X1", cid, version, f"cause.{cause}.{b}m", rel, f"{base}/causes/{esc(cause)}/{esc(b)}",
                           "frames", st, "in-sample", LINUX)
    for key in ("707ea9c", "1.1.0"):
        lc = f"/label_check/{esc(key)}/causes"
        for cause in doc["label_check"][key]["causes"]:
            for k in ("checked", "confirmed"):
                ex.num("X1", "x1/label_check", VERSIONS[key][0], f"label_check.{cause}.{k}", rel,
                       f"{lc}/{esc(cause)}/{k}", "frames", "CHECKED", "harness", LINUX)
        ex.derived("X1", "x1/label_check", VERSIONS[key][0], "label_check.wrong_labels",
                   len(doc["label_check"][key]["wrong"]), "frames", "CHECKED", "harness", LINUX,
                   "len(label_check.<version>.wrong)")


def j1(ex):
    rel = "docs/evidence/rejudge_2026-10-16/dryrun/dryrun.json"
    doc, _ = load(rel)
    for tag, status, version in (("707ea9c", "DRY RUN (reproduction of 13.10)", "v1.0.0"),
                                 ("prerelease_1.1.0", "PRE-RELEASE, not a J1 result", "1.1.0")):
        for bag, r in doc["runs"][tag]["recordings"].items():
            cid = f"j1/{bag}"
            ex.case(case_id=cid, stage="J1", recording=bag, alias=ALIAS[bag], object="real person + object" if
                    bag == "doubleT_obstacle" else "none (empty)", variant="nominal, node path from raw bag",
                    version=version, commit=VERSIONS["707ea9c" if tag == "707ea9c" else "1.1.0"][1], runtime=LINUX,
                    status=status, scope="development data (in-sample)",
                    result=f"STOP {r['decisions']['STOP']}/{r['frames']}, {r['stop_episodes']} episodes, first STOP "
                           f"frame {r['first_stop_frame']}", evidence=rel)
            base = f"/runs/{esc(tag)}/recordings/{esc(bag)}"
            for k in ("GO", "CAUTION", "STOP", "FAULT"):
                ex.num("J1", cid, version, f"decisions.{k}", rel, f"{base}/decisions/{k}", "frames", status,
                       "in-sample", LINUX)
            ex.num("J1", cid, version, "stop_episodes", rel, f"{base}/stop_episodes", "episodes", status, "in-sample",
                   LINUX)
            if r["first_stop_frame"] is not None:
                ex.num("J1", cid, version, "first_stop_frame", rel, f"{base}/first_stop_frame", "frame index", status,
                       "in-sample", LINUX)
        for k in ("stop_frames", "stop_episodes"):
            ex.num("J1", "j1/empty_five", version, f"empty_five.{k}", rel, f"/runs/{esc(tag)}/empty_five/{k}",
                   "frames" if k == "stop_frames" else "episodes", status, "in-sample", LINUX)


def j1_range(ex):
    """The judge's 37 range jobs pre-built on both versions (rejudge_2026-10-16/prebuild)."""
    for key, status in (("707ea9c", "DRY RUN (reproduction of 13.10)"), ("1.1.0", "PRE-RELEASE, not a J1 result")):
        version = VERSIONS[key][0]
        rel = f"docs/evidence/rejudge_2026-10-16/prebuild/summary_{key}.json"
        doc, _ = load(rel)
        for i, j in enumerate(doc["jobs"]):
            s = j["summary"]
            cid = f"j1range/{j['job']}"
            ex.case(case_id=cid, stage="J1-range", recording=j["recording"], alias=j["job"].split("_")[0],
                    object=j["job"], variant=j["args"], version=version, commit=VERSIONS[key][1], runtime=LINUX,
                    status=status, scope="development data (in-sample), synthetic ray-cast object",
                    result=f"first STOP {s['first_stop_X']} m, held {s['held_from_X']} m, STOP hits "
                           f"{s['stop_frames']}/{s['visible_frames']}", evidence=rel)
            base = f"/jobs/{i}/summary"
            for k, unit in (("first_visible_X", "m"), ("first_stop_X", "m"), ("held_from_X", "m")):
                if s[k] is not None:
                    ex.num("J1-range", cid, version, k.replace("_X", "_m"), rel, f"{base}/{k}", unit, status,
                           "in-sample", LINUX)
            for k in ("visible_frames", "stop_frames"):
                ex.num("J1-range", cid, version, k, rel, f"{base}/{k}", "frames", status, "in-sample", LINUX)
            for k in ("GO", "CAUTION", "STOP", "FAULT"):
                ex.num("J1-range", cid, version, f"decisions_while_visible.{k}", rel,
                       f"{base}/decisions_while_visible/{k}", "frames", status, "in-sample", LINUX)


NEW = "MEASURED (development data, observation)"
B6_BAGS = ["doubleT_obstacle", "doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
           "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch", "cloud_with_fake_obj",
           "synthetic_platform", "synthetic_switch", "synthetic_tunnels"]
SHORT = {"v1.0.0": "v100", "1.1.0": "v110"}


def syn(ex):
    """B1 / A5 (17.10): the organizers' 16.10 synthetic platform, frames 0-314 with exact labels."""
    for version in ("v1.0.0", "1.1.0"):
        commit = VERSIONS["707ea9c" if version == "v1.0.0" else "1.1.0"][1]
        rel = f"docs/evidence/synthetic_labels_2026-10-17/score_platform_0-314_{SHORT[version]}.json"
        doc, _ = load(rel)
        for obj, o in doc["objects"].items():
            cid = f"syn/synthetic_platform/{obj}"
            ex.case(case_id=cid, stage="SYN", recording="synthetic_platform (frames 0-314)", alias="synthetic 16.10",
                    object=obj, variant="nominal, node path from decoded cache", version=version, commit=commit,
                    runtime=LINUX, status=NEW, scope="development data (organizers' 16.10 synthetic)",
                    result=f"first STOP {o['first_stop_d']} m, STOP rows {o['stop_rows']}/{o['rows_plausible']}, "
                           f"intent (measured) {'STOP' if o['in_gauge_intent'] else 'no STOP'}", evidence=rel)
            base = f"/objects/{esc(obj)}"
            for k, unit in (("first_visible_d", "m"), ("first_stop_d", "m"), ("held_from_d", "m"),
                            ("stop_rows", "rows"), ("rows_plausible", "rows")):
                if o[k] is not None:
                    ex.num("SYN", cid, version, f"object.{obj}.{k}", rel, f"{base}/{k}", unit, NEW, "in-sample", LINUX)
        ex.num("SYN", "syn/synthetic_platform/unmatched", version, "unmatched_stop_frames", rel,
               "/unmatched_stop_frames", "frames", NEW, "in-sample", LINUX)
        rel = f"docs/evidence/synthetic_labels_2026-10-17/attribution/{SHORT[version]}/table.json"
        doc, _ = load(rel)
        for cause, bins in doc["cases"]["plat"]["causes"].items():
            for b in bins:
                ex.num("SYN", "syn/synthetic_platform/attribution", version, f"cause.{cause}.{b}m", rel,
                       f"/cases/plat/causes/{esc(cause)}/{esc(b)}", "rows", NEW, "in-sample", LINUX)


def falcon(ex):
    """B2 (whole Falcon recording, one detector) and B3 / B8 (switch and timing), 18.10."""
    rel = "docs/evidence/falcon_full_2026-10-18/check_v110.json"
    doc, _ = load(rel)
    ex.case(case_id="b2/falcon_test_second_dark", stage="B2", recording="falcon_test_second_dark (whole)",
            alias="Falcon", object="walking person (real)", variant="whole recording, one detector, streamed",
            version="1.1.0", commit=VERSIONS["1.1.0"][1], runtime=LINUX, status=NEW,
            scope="development data (second lidar)", result=f"{doc['frames']} frames, prefix equal "
            f"{doc['prefix_equal_frames']}/{doc['prefix_frames']} decisions", evidence=rel)
    for k in ("frames", "prefix_equal_frames", "window_times_found"):
        ex.num("B2", "b2/falcon_test_second_dark", "1.1.0", k, rel, f"/{k}", "frames", NEW, "in-sample", LINUX)
    for part, p in doc["parts"].items():
        key = part.split(" ")[0]
        for d in p["decisions"]:
            ex.num("B2", "b2/falcon_test_second_dark", "1.1.0", f"part.{key}.decisions.{d}", rel,
                   f"/parts/{esc(part)}/decisions/{d}", "frames", NEW, "in-sample", LINUX)
        ex.num("B2", "b2/falcon_test_second_dark", "1.1.0", f"part.{key}.caution_share", rel,
               f"/parts/{esc(part)}/caution_share", "share", NEW, "in-sample", LINUX)
    for version in ("v1.0.0", "1.1.0"):
        rel = f"docs/evidence/falcon_switch_2026-10-18/{SHORT[version]}/compare.json"
        doc, _ = load(rel)
        commit = VERSIONS["707ea9c" if version == "v1.0.0" else "1.1.0"][1]
        for order in ("p2f", "f2p"):
            cid = f"b3/{order}"
            ex.case(case_id=cid, stage="B3", recording="doubleT_obstacle + falcon prefix", alias="switch",
                    object="", variant=" then ".join(doc[order]["order"]), version=version, commit=commit,
                    runtime=LINUX, status=NEW, scope="development data", result=f"frames differing from stand-alone: "
                    f"{doc[order]['first_part_differs']} + {doc[order]['second_part_differs']}", evidence=rel)
            for k in ("first_part_differs", "second_part_differs"):
                ex.num("B3", cid, version, k, rel, f"/{order}/{k}", "frames", NEW, "in-sample", LINUX)
        for sensor in ("pandar", "falcon"):
            for t in ("decode_ms", "detect_ms"):
                for q in ("p50", "p95"):
                    ex.num("B8", f"b8/{sensor}", version, f"{t}.{q}", rel, f"/alone/{sensor}/timing/{t}/{q}", "ms",
                           NEW, "in-sample", LINUX)


def gauge(ex):
    """B6 (18.10): gauge range and stability against the driven path, ten recordings, both versions."""
    mon_rel = "docs/evidence/gauge_stability_2026-10-18/monitored.json"
    mon, _ = load(mon_rel)
    for version in ("v1.0.0", "1.1.0"):
        commit = VERSIONS["707ea9c" if version == "v1.0.0" else "1.1.0"][1]
        for bag in B6_BAGS:
            cid = f"b6/{bag}"
            rel = f"docs/evidence/gauge_stability_2026-10-18/{SHORT[version]}/measure_{bag}.json"
            doc, _ = load(rel)
            ex.case(case_id=cid, stage="B6", recording=bag, alias=ALIAS.get(bag, "synthetic 16.10"), object="gauge",
                    variant="nominal; truth = driven path (ICP)", version=version, commit=commit, runtime=LINUX,
                    status=NEW, scope="development data (in-sample)",
                    result=f"trusted range p50 {doc['range']['p50']} m, blinks {doc['blinks']}", evidence=rel)
            ex.num("B6", cid, version, "trusted_range.p50", rel, "/range/p50", "m", NEW, "in-sample", LINUX)
            ex.num("B6", cid, version, "blinks", rel, "/blinks", "events", NEW, "in-sample", LINUX)
            for x in ("40m", "80m", "120m"):
                ex.num("B6", cid, version, f"flicker_compensated.{x}.p90", rel, f"/jitter_compensated/{x}/p90", "m",
                       NEW, "in-sample", LINUX)
            for b in ("40-60", "80-100", "120-150"):
                if doc["offtrack"][b]["within_trusted"].get("p50") is not None:
                    ex.num("B6", cid, version, f"offtrack.{b}m.p50", rel, f"/offtrack/{b}/within_trusted/p50", "m",
                           NEW, "in-sample", LINUX)
            vals = sorted(mon[f"{bag}|{SHORT[version]}"])
            n = len(vals)
            ex.derived("B6", cid, version, "reported_range.p50", (vals[(n - 1) // 2] + vals[n // 2]) / 2, "m", NEW,
                       "in-sample", LINUX, f"median of {mon_rel}[{bag}|{SHORT[version]}]")
            hrel = f"docs/evidence/gauge_stability_2026-10-18/{SHORT[version]}/honesty_{bag}.json"
            if (ROOT / hrel).exists():
                ex.num("B6", cid, version, "reported_range.share_off_over_1.05m", hrel, "/inside_over_1.05m", "share",
                       NEW, "in-sample", LINUX)


def g3(ex):
    rel = "docs/evidence/heldout_2026-10-15/spec.json"
    doc, _ = load(rel)
    variants = ",".join(v["id"] for v in doc["variants"])
    for c in doc["cases"]:
        ex.case(case_id=f"g3/{c['id']}", stage="G3", recording=f"window {c['window']}", alias=c["window"],
                object=c["shape"], variant=f"{c['motion']}; variants: {variants}", version="final seal (not yet)",
                commit="", runtime="", status="REGISTERED, NOT RUN", scope="held-out synthetic probes",
                result="", evidence=rel)
    ex.derived("G3", "g3/spec", "", "registered_cases", len(doc["cases"]), "cases", "REGISTERED, NOT RUN",
               "held-out", "", "len(spec.cases)")
    ex.derived("G3", "g3/spec", "", "registered_runs", len(doc["cases"]) * len(doc["variants"]), "runs",
               "REGISTERED, NOT RUN", "held-out", "", "len(spec.cases) * len(spec.variants)")


def check(ex):
    bad = []
    for n in ex.nums:
        if n["derived"]:
            continue
        p = ROOT / n["source"]
        doc = json.loads(p.read_text())
        if hashlib.sha256(p.read_bytes()).hexdigest() != n["source_sha256"] or get(doc, n["pointer"]) != n["value"]:
            bad.append(n)
    return bad


def write(rows, cols, stem):
    with open(HERE / f"{stem}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    (HERE / f"{stem}.json").write_text(json.dumps({"schema": SCHEMA, "rows": rows}, indent=0, ensure_ascii=False) + "\n")


def main():
    ex = Export()
    for part in (x3, x1, j1, j1_range, syn, falcon, gauge, g3):
        part(ex)
    if "--check" not in sys.argv:
        write(ex.cases, RECORD_COLS, "case_register")
        write(ex.nums, NUM_COLS, "numbers")
    bad = check(ex)
    by_stage = {}
    for c in ex.cases:
        by_stage[c["stage"]] = by_stage.get(c["stage"], 0) + 1
    print(f"cases {len(ex.cases)} {by_stage}; numbers {len(ex.nums)} "
          f"({sum(bool(n['derived']) for n in ex.nums)} derived); source mismatches {len(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
