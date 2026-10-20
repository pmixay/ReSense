"""Shared helpers of the final-bundle review (20.10): row flattening and the latency normalisation.

Wall-clock fields are the only thing removed before rows are compared: ``timing_ms`` / ``decode_ms`` / ``detect_ms`` /
``total_ms``, ``health.latency_p95_ms`` and the health messages that start with "latency p95". The health ``level`` /
``decision_level`` are compared too; when they differ they are only accepted if exactly one side carries a latency
message (``level_explained``), so a level change from any other cause is a difference.
"""
import json
import re

LAT_MSG = re.compile(r"latency p95")


def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat(v, p + "/" + k)
    elif isinstance(o, list):
        if all(not isinstance(x, (dict, list)) for x in o):
            yield p, tuple(o)
        else:
            yield p + "#len", len(o)
            for i, x in enumerate(o):
                yield from flat(x, f"{p}[{i}]")
    else:
        yield p, o


def jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def msgs(row):
    """health messages of a gate row ({health: {messages}}) or of a probe/Falcon row ({msgs})."""
    return row["health"]["messages"] if "health" in row else row["msgs"]


def has_latency_msg(row):
    return any(LAT_MSG.match(m) or LAT_MSG.search(m) for m in msgs(row))


def levels(row):
    return (row["health"]["level"], row["health"]["decision_level"]) if "health" in row else (row["level"], row["dlevel"])


def normalise(row):
    """Row without wall-clock fields and without the level fields (compare those with ``level_explained``)."""
    r = json.loads(json.dumps(row))
    r.pop("timing_ms", None)
    for k in ("decode_ms", "detect_ms", "total_ms"):
        r.pop(k, None)
    if "health" in r:
        h = r["health"]
        h.pop("latency_p95_ms", None)
        h["messages"] = [m for m in h.get("messages", []) if not LAT_MSG.search(m)]
        h.pop("level", None)
        h.pop("decision_level", None)
    else:
        r["msgs"] = [m for m in r.get("msgs", []) if not LAT_MSG.search(m)]
        r.pop("level", None)
        r.pop("dlevel", None)
    return r


def level_explained(a, b):
    """True when the level fields agree, or differ while exactly one side has a latency message."""
    if levels(a) == levels(b):
        return True
    return has_latency_msg(a) != has_latency_msg(b)


def rows_equal(a, b):
    return dict(flat(normalise(a))) == dict(flat(normalise(b))) and level_explained(a, b)


def is_stop(row):
    return row["decision"] == "STOP" if "decision" in row else bool(row["obstacle"])
