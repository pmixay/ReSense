"""Expose the unchanged range_test visible-frame denominator versus raw hit flags."""
import json

from package import EXTERNAL, P, PARENT_PROBES, encoded, load


def score(result):
    visible = [r for r in result["rows"] if r["X"] is not None and r["X"] > 3.0 and r["n_obj"] > 0]
    matched = [r["k"] for r in visible if r["hit"]]
    raw = [r["k"] for r in result["rows"] if r["hit"]]
    excluded = [r for r in result["rows"] if r["hit"] and r["k"] not in matched]
    assert len(visible) == result["summary"]["visible_frames"]
    assert len(matched) == result["summary"]["stop_frames"]
    return dict(visible_frames=len(visible), visible_matched_stop_frames=matched,
                raw_hit_frames=raw, excluded_nonvisible_hit_rows=excluded)


def main():
    result = {}
    for name in ("pole_c", "C_person"):
        current = score(load(EXTERNAL / "probes-c9aea87-20261016a/results" / (name + ".json")))
        sealed = score(load(EXTERNAL / "probes-sealed-707ea9c-20261016a/results" / (name + ".json")))
        reference = sealed if name == "pole_c" else score(load(PARENT_PROBES / "results/C_person.json"))
        assert current["visible_matched_stop_frames"] == reference["visible_matched_stop_frames"]
        assert len(current["visible_matched_stop_frames"]) == (82 if name == "pole_c" else 55)
        result[name] = dict(definition="Unchanged range_test.py lines 216-219: X > 3, n_obj > 0, hit=True",
                            current=current, registered_reference=reference, sealed=sealed,
                            lost_visible_matched_frames=[], new_visible_matched_frames=[])
    target = P / "probe_scoring_details.json"
    assert not target.exists()
    target.write_bytes(encoded(result))
    print(json.dumps({name: dict(visible_frames=value["current"]["visible_frames"],
                                 visible_matched_stops=len(value["current"]["visible_matched_stop_frames"]),
                                 raw_hit_flags=len(value["current"]["raw_hit_frames"]),
                                 excluded_nonvisible=[r["k"] for r in value["current"]["excluded_nonvisible_hit_rows"]])
                      for name, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()
