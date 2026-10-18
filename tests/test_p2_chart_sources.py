"""Chart provenance must fail closed on missing cases, source mutation and premature final claims."""
import copy
import json

import pytest

from scripts.p2_chart_sources import digest, load_sources, render_sources


@pytest.fixture
def declaration(tmp_path):
    source = tmp_path / "range.json"
    source.write_text(json.dumps({"summary": {"first": 50, "held": None, "visible": 20, "matched": 3}}))
    row = {"criterion": "8.2", "recording": "test-only", "object": "box", "dimensions_m": [1, 1, 1],
           "data_type": "team-synthetic", "scope": "test-only", "limitations": "fixture, not measurement",
           "verdict": "FAIL", "values": {key: {"file": source.name, "sha256": digest(source),
           "pointer": f"/summary/{field}", "null_reason": "not sustained"} for key, field in
           (("first_stop_m", "first"), ("held_90_m", "held"), ("visible", "visible"), ("matched", "matched"))}}
    spec = {"pipeline": "node-decoded", "measured_sha": "a" * 40, "seal_digest": "b" * 64,
            **{k: "test-only" for k in ("protocol", "scorer", "scope", "release", "image", "raw_restore", "held_definition")},
            "expected_ids": ["straight", "curve", "double-track"],
            "rows": [{**copy.deepcopy(row), "id": g, "geometry": g} for g in ("straight", "curve", "double-track")]}
    path = tmp_path / "declaration.json"
    path.write_text(json.dumps(spec))
    return path, source, spec


def test_draft_preserves_nulls_counts_and_every_geometry(declaration, tmp_path):
    path, _, _ = declaration
    receipt = render_sources(path, tmp_path / "chart")
    data = json.loads((tmp_path / "chart/chart-input.json").read_text())
    assert len(data["rows"]) == 3
    assert all(r["resolved"]["held_90_m"] is None for r in data["rows"])
    assert all(r["resolved"]["matched"] == 3 for r in data["rows"])
    assert receipt == render_sources(path, tmp_path / "chart")
    assert "DRAFT" in (tmp_path / "chart/range-source-table.svg").read_text()
    with pytest.raises(ValueError, match="final chart blocked"):
        load_sources(path, final=True)


def test_source_mutation_cannot_silently_change_chart(declaration):
    path, source, _ = declaration
    source.write_text('{}')
    with pytest.raises(ValueError, match="hash mismatch"):
        load_sources(path)


def test_omitted_unfavourable_case_is_rejected(declaration):
    path, _, spec = declaration
    spec["rows"].pop()
    path.write_text(json.dumps(spec))
    with pytest.raises(ValueError, match="entire P4 case register"):
        load_sources(path)
