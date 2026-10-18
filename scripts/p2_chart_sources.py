"""PT1 preparation: verify references into existing P4 JSONs, render without rescoring.

This is a P2-local input declaration, not a new P4 API. Final exports and numeric
review still need P4 agreement. Unapproved inputs can only produce a labelled draft.
All source paths are relative to the declaration; every value is a JSON pointer.
"""
from __future__ import annotations

import hashlib
import html
import json
import math
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pointer(data, path):
    if not isinstance(path, str) or not path.startswith("/"):
        raise ValueError("source key must be an absolute JSON pointer")
    for part in path[1:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        data = data[int(part)] if isinstance(data, list) else data[part]
    return data


def load_sources(path, *, final=False):
    path = Path(path)
    spec = json.loads(path.read_text())
    if spec.get("pipeline") != "node-decoded":
        raise ValueError("headline range source must be node-decoded, not the 1 cm cache gate")
    for field, length in (("measured_sha", 40), ("seal_digest", 64)):
        if not re.fullmatch(r"[0-9a-f]{%d}" % length, spec.get(field, "")):
            raise ValueError(f"missing full {field}")
    for field in ("protocol", "scorer", "scope", "release", "image", "raw_restore", "held_definition"):
        if not isinstance(spec.get(field), str) or not spec[field].strip():
            raise ValueError(f"missing {field}; explicitly describe unavailable inputs")
    if final and (spec.get("p4_review") != "approved" or spec.get("p1_review") != "approved"
                  or spec.get("release_verified") is not True or spec.get("raw_available") is not True):
        raise ValueError("final chart blocked: P1/P4 approval, verified release and retrievable raw evidence required")
    rows = spec.get("rows", [])
    ids = [r["id"] for r in rows]
    expected = spec.get("expected_ids", [])
    if not ids or len(set(ids)) != len(ids) or len(set(expected)) != len(expected) or set(ids) != set(expected):
        raise ValueError("rows must cover the entire P4 case register exactly once")
    if len({r["geometry"] for r in rows}) < 3:
        raise ValueError("at least three geometries must be represented")
    sources = {}
    resolved = []
    for row in rows:
        for key in ("criterion", "recording", "geometry", "object", "dimensions_m", "data_type", "scope", "limitations", "verdict"):
            if key not in row:
                raise ValueError(f"{row['id']}: missing {key}")
        if row["verdict"] not in ("PASS", "FAIL", "NOT_MEASURED"):
            raise ValueError("invalid verdict")
        values = {}
        for metric in ("first_stop_m", "held_90_m", "visible", "matched"):
            ref = row["values"][metric]
            if ref.get("unavailable"):
                value = None
            else:
                source = (path.parent / ref["file"]).resolve()
                if digest(source) != ref["sha256"]:
                    raise ValueError(f"source hash mismatch: {source}")
                if source not in sources:
                    sources[source] = json.loads(source.read_text())
                value = pointer(sources[source], ref["pointer"])
            if value is None:
                if not ref.get("null_reason") and not ref.get("unavailable"):
                    raise ValueError(f"{row['id']}/{metric}: null needs a reason (miss is not zero)")
            elif (isinstance(value, bool) or not isinstance(value, (int, float))
                  or not math.isfinite(value) or value < 0):
                raise ValueError(f"{row['id']}/{metric}: invalid numeric value")
            if metric in ("visible", "matched") and value is not None and int(value) != value:
                raise ValueError("counts must be integers")
            values[metric] = value
        if values["matched"] is not None and values["visible"] is not None and values["matched"] > values["visible"]:
            raise ValueError("matched count exceeds visible denominator")
        resolved.append({**row, "resolved": values})
    return {**spec, "rows": resolved, "declaration_sha256": digest(path)}


def render_sources(path, output, *, final=False):
    """Full-table draft SVG + the same resolved rows for future deck/video cards.

    No favourable subset, interpolation, invented zero for a miss, or scored claims.
    Final slide selection/layout is deferred until P4's export and P1's approval.
    """
    data = load_sources(path, final=final)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    rows = data["rows"]
    def esc(s):
        return html.escape(str(s))
    width, height = 1600, 140 + 90 * len(rows)
    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
           '<rect width="100%" height="100%" fill="white"/>',
           '<g font-family="sans-serif" font-size="20" fill="#16151a">',
           f'<text x="24" y="32">{"REVIEWED SOURCE TABLE" if final else "DRAFT — NOT RELEASE EVIDENCE"}</text>',
           '<text x="24" y="66">Geometry / object / data type</text>',
           '<text x="850" y="66">First STOP / held-90% (m)</text>',
           '<text x="1250" y="66">Matched / visible</text>']
    def fmt(v):
        return "not measured / miss" if v is None else f"{v:g}"
    for i, row in enumerate(rows):
        y = 110 + 90 * i
        v = row["resolved"]
        label = f"{row['geometry']} / {row['object']} / {row['data_type']}"
        svg += [f'<text x="24" y="{y}">{esc(label)}</text>',
                f'<text x="850" y="{y}">{esc(fmt(v["first_stop_m"]))} / {esc(fmt(v["held_90_m"]))}</text>',
                f'<text x="1250" y="{y}">{esc(fmt(v["matched"]))} / {esc(fmt(v["visible"]))}</text>',
                f'<text x="24" y="{y + 30}" font-size="16">{esc(row["id"])} · {esc(row["verdict"])} · {esc(row["limitations"])}</text>']
    svg += ['</g></svg>']
    chart = output / "range-source-table.svg"
    chart.write_text("\n".join(svg), encoding="utf-8")
    table = output / "chart-input.json"
    table.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    receipt = {"source_declaration": str(Path(path)), "source_sha256": data["declaration_sha256"],
               "mode": "final" if final else "draft", "artifacts": {p.name: digest(p) for p in (chart, table)},
               "p1_review": data.get("p1_review", "pending"), "p4_review": data.get("p4_review", "pending")}
    (output / "manifest.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
