"""Offline completeness/input-byte checks and remaining serialized-field differences."""
from collections import Counter
import json
import re

from package import DATA, EXTERNAL, P, REFERENCE, encoded, file_id, load


def diff(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(a.keys() | b.keys()) for d in diff(a.get(k), b.get(k), path + "/" + k)]
    return [] if a == b else [dict(path=path, sealed=a, withdrawal=b)]


def main():
    directory = DATA / "cache/new_data"
    natural = lambda p: [int(s) if s.isdigit() else s for s in re.split(r"(\d+)", p.name)]
    files = sorted([*directory.glob("*.npy"), *directory.glob("*.npy.zst")], key=natural)
    assert len(files) == 11271
    result = {}
    for index in (1, 3):
        piece = "ride_" + str(index)
        quotient, remainder = divmod(len(files), 8)
        start = index * quotient + min(index, remainder)
        expected = files[start:start + quotient + (index < remainder)]
        inputs = load(P / "dark_input_identity.json")[piece]
        assert len(expected) == len(inputs) == 1409
        sidecars, paths, differences = set(), Counter(), []
        for path, row in zip(expected, inputs, strict=True):
            stem = path.name.removesuffix(".zst").removesuffix(".npy")
            assert stem == row["frame_id"] and file_id(path)["sha256"] == row["cache_sha256"]
            sidecars.add(directory / (stem.rsplit("_", 1)[0] + "_stamps.json"))
        with (REFERENCE / (piece + ".jsonl")).open() as rf, \
                (EXTERNAL / "dark-c9aea87-20261016a/results" / (piece + ".jsonl")).open() as gf:
            for r, g in zip(map(json.loads, rf), map(json.loads, gf), strict=True):
                assert r["frame_id"] == g["frame_id"]
                ds = diff(r["serialized"], g["serialized"])
                paths.update(d["path"] for d in ds)
                if ds:
                    differences.append(dict(frame=g["frame_id"], differences=ds))
        result[piece] = dict(entire_piece=True, split="numpy.array_split natural cache order into 8 pieces, zero-based indices 1 and 3",
                             total_ride_frames=len(files), frames=len(inputs), all_cache_bytes_match_logged_sha256=True,
                             stamp_sidecars=[file_id(p) for p in sorted(sidecars)],
                             serialized_differing_frames=len(differences), paths=dict(paths), differences=differences)
    target = P / "dark_details.json"
    assert not target.exists()
    target.write_bytes(encoded(result))
    print(json.dumps({piece: {k: v for k, v in value.items() if k not in ("differences", "stamp_sidecars")}
                      for piece, value in result.items()}, indent=2))


if __name__ == "__main__":
    main()
