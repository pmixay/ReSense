#!/usr/bin/env python3
"""Reviewer script: write the snapshot lists (stem:k) used for the picture galleries into out/list_*.txt."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent / "out"
c = {(r["stem"], r["k"]): r for r in json.load(open(D / "snap_pad_wt_cand.json"))["rows"]}
pa = {(r["stem"], r["k"]): r for r in json.load(open(D / "snap_pad_wt_parent.json"))["rows"]}
keep = [f"{s}:{k}" for (s, k), r in c.items() if not r["rejected"]]
cp = [f"{s}:{k}" for (s, k), r in c.items() if r["rejected"] and not pa[(s, k)]["rejected"]]
pc = [f"{s}:{k}" for (s, k), r in c.items() if not r["rejected"] and pa[(s, k)]["rejected"]]
(D / "list_keep.txt").write_text(" ".join(keep))
(D / "list_cand_only.txt").write_text(" ".join(cp))
(D / "list_parent_only.txt").write_text(" ".join(pc))
(D / "list_removed.txt").write_text("new_data_52_0016:5 new_data_52_0017:5 new_data_52_0018:5 new_data_52_0022:2 "
                                    "new_data_52_0023:2 new_data_205_0031:0 new_data_111_0049:0 new_data_112_0000:4")
print(len(keep), "kept by candidate;", len(cp), "rejected by candidate but not parent;", len(pc), "parent only")
print("kept:", keep)
print("cand only:", cp)
print("parent only:", pc)
