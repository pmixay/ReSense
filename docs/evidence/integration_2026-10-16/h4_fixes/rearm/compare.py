"""Validate the retained red/green physical comparison without importing production code."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
red = HERE / "red-abd09df"
green = HERE / "green-bb62b94"
before = {p["label"]: p for p in json.loads((red / "physical.json").read_text())}
after = {p["label"]: p for p in json.loads((green / "physical.json").read_text())}
identities = [json.loads((p / "identity.json").read_text()) for p in (red, green)]
for key in ("native_sha256", "clustering_sha256", "config_sha256", "open3d"):
    assert identities[0][key] == identities[1][key], key
assert before.keys() == after.keys()
rows = []
for label in before:
    a, b = before[label], after[label]
    assert a["initial"] == b["initial"]
    assert a["object_returns"] == b["object_returns"]
    changes = [f for f in range(20) if a["frames"][f]["stop_ids"] != b["frames"][f]["stop_ids"]]
    assert changes == ([11] if label == "case44_free" else [])
    rows.append(dict(label=label, before=a["stop_frames"], after=b["stop_frames"], changed_frames=changes))
pole = after["case44_free"]["frames"]
assert pole[9]["stop_ids"] and not pole[10]["stop_ids"] and pole[11]["stop_ids"]
assert pole[0]["tracks"][0]["provisional_explained_hist"] == [True]
assert not any(pole[5]["tracks"][0]["provisional_explained_hist"])
assert not any(pole[11]["tracks"][0]["explained_hist"])
column = after["genuine_column_to_vault"]["frames"]
assert column[9]["tracks"][0]["explained_hist"] == column[10]["tracks"][0]["explained_hist"]
assert any(column[11]["tracks"][0]["explained_hist"])
suites = [ET.parse(p / "pytest.xml").getroot().find("testsuite").attrib for p in (red, green)]
assert (suites[0]["failures"], suites[1]["failures"]) == ("2", "0")
assert all(s["tests"] == "250" and s["errors"] == "0" and s["skipped"] == "0" for s in suites)
summary = dict(red_source=identities[0]["source_commit"], green_source=identities[1]["source_commit"],
               red=dict(tests=250, passed=248, failed=2, skipped=0),
               green=dict(tests=250, passed=250, failed=0, skipped=0),
               physical=rows, native_sha256=identities[1]["native_sha256"],
               open3d=identities[1]["open3d"])
(HERE / "comparison.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
