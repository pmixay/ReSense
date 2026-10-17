#!/usr/bin/env python3
"""Prove a Linux node-decoded cache equals the committed Windows H0/X3 decoded inputs.

    python scripts/p4_linux_intake.py --decoded <root> --out <new intake.json>
        [--reference docs/evidence/p4_start_2026-10-15/intake.json]

``cache_decoded.py`` writes ``np.savez_compressed`` archives. Their bytes depend on the platform
only through the zip writer: Python's ``zipfile`` records ``create_system`` (0 on win32, 3 elsewhere)
and Python 3.10 writes numpy's ``force_zip64`` entries without the zip64 version / size fields
that Python >= 3.11 writes (verified on frame 0 of Set O: 3.10 differs, 3.11 and 3.13 reproduce).
For every frame this script loads the three arrays, checks dtypes / shapes / finiteness, and
re-serialises them in memory exactly as the Windows tool did (numpy ``savez_compressed`` under a
Python >= 3.11 ``zipfile`` with ``create_system=0``). The SHA-256 of that canonical byte stream must
equal the committed Windows file hash, and ``meta.json`` must be byte-identical. Equality therefore
proves the arrays are identical, not merely similar. Exit 0: all identical; 1: any difference.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REF = ROOT / "docs/evidence/p4_start_2026-10-15/intake.json"


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha256(path):
    return sha256_bytes(Path(path).read_bytes())


def windows_npz_bytes(arrays):
    """numpy.savez_compressed bytes as written on win32 (zip create_system 0)."""
    buf = io.BytesIO()
    np.savez_compressed(buf, **arrays)
    b = bytearray(buf.getvalue())
    i = 0
    while (i := b.find(b"PK\x01\x02", i)) >= 0:  # central directory: version made by = (spec, system)
        b[i + 5] = 0
        i += 4
    return bytes(b)


def check_bag(cache, ref):
    meta_path = cache / "meta.json"
    meta = json.loads(meta_path.read_text())
    files = sorted(cache.glob("f_*.npz"))
    out = {"path": str(cache), "frames": len(meta), "meta_sha256": sha256(meta_path),
           "reference_meta_sha256": ref["meta_sha256"], "arrays_checked": 0, "mismatches": []}
    if [p.name for p in files] != [f["name"] for f in ref["files"]] or len(meta) != ref["frames"]:
        out["mismatches"].append("file list / frame count differs from reference")
        return out
    if out["meta_sha256"] != ref["meta_sha256"]:
        out["mismatches"].append("meta.json differs from reference")
    native_inventory = []
    for path, expected in zip(files, ref["files"]):
        with np.load(path) as d:
            arrays = {k: d[k] for k in ("xyz", "inten", "ring")}
        xyz, inten, ring = arrays["xyz"], arrays["inten"], arrays["ring"]
        if (xyz.dtype != np.float32 or inten.dtype != np.float32 or ring.dtype != np.uint16
                or xyz.ndim != 2 or xyz.shape[1] != 3 or len(inten) != len(xyz) or len(ring) != len(xyz)
                or not np.isfinite(xyz).all()):
            out["mismatches"].append(f"{path.name}: invalid arrays")
        canonical = windows_npz_bytes(arrays)
        if sha256_bytes(canonical) != expected["sha256"] or len(canonical) != expected["bytes"]:
            out["mismatches"].append(f"{path.name}: canonical bytes differ from reference")
        native_inventory.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)})
        out["arrays_checked"] += 1
    # Same digest construction as robustness_battery.source_info, over the Linux file bytes.
    out["linux_payload_sha256"] = sha256_bytes(json.dumps(native_inventory, sort_keys=True).encode())
    out["reference_payload_sha256"] = ref["payload_sha256"]
    for i, m in enumerate(meta):
        if m["i"] != i or not all(math.isfinite(m[k]) for k in ("stamp", "bag_t")):
            out["mismatches"].append(f"meta row {i} invalid")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--decoded", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--reference", type=Path, default=DEFAULT_REF)
    ap.add_argument("--bags", help="comma list; default every bag in the reference")
    a = ap.parse_args(argv)
    if sys.version_info < (3, 11):
        ap.error("needs Python >= 3.11: its zipfile reproduces the Windows writer's zip64 extra field")
    if a.out.exists():
        ap.error("output exists; choose a fresh --out")
    ref = json.loads(a.reference.read_text())["decoded"]
    bags = a.bags.split(",") if a.bags else list(ref)
    report = {"schema": "resense-p4-linux-decoded-intake-v1", "reference": str(a.reference.relative_to(ROOT))
              if a.reference.resolve().is_relative_to(ROOT) else str(a.reference),
              "reference_sha256": sha256(a.reference), "tool_sha256": sha256(__file__),
              "runtime": {"platform": platform.platform(), "python": sys.version, "numpy": np.__version__},
              "bags": {}}
    for bag in bags:
        report["bags"][bag] = check_bag(a.decoded / bag, ref[bag])
        r = report["bags"][bag]
        print(bag, r["frames"], "frames", "IDENTICAL" if not r["mismatches"] else f"{len(r['mismatches'])} MISMATCHES",
              flush=True)
    report["status"] = "IDENTICAL" if all(not r["mismatches"] for r in report["bags"].values()) else "DIFFERENT"
    with open(a.out, "x", encoding="utf-8") as f:
        json.dump(report, f, indent=1)
        f.write("\n")
    print(report["status"], a.out)
    return 0 if report["status"] == "IDENTICAL" else 1


if __name__ == "__main__":
    sys.exit(main())
