#!/usr/bin/env python3
"""Generate a deterministic, fully synthetic LiDAR fixture for detector regression tests.

The fixture uses the repository's round-tunnel ray caster and Pandar128 ray grid. It is
controlled test input only: it is not organizer data and is not evidence of real-world
generalization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from resense.config import DetectorConfig
from resense.frame import Frame, axis_matrix
from resense.pointcloud import COMPACT_DTYPE, compact_to_compact16
from resense.sensor import RING_ELEVATION_DEG
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "tests" / "fixtures" / "synthetic_lidar_v1"
SCHEMA = "resense.synthetic_lidar_fixture.v1"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_compact16(frame: Frame, labels: np.ndarray, sensor_cfg) -> tuple[np.ndarray, np.ndarray]:
    """Encode vehicle-frame ray hits as the cache's compact16 sensor-frame rows."""
    xyz_vehicle = np.asarray(frame.xyz, dtype=np.float32)
    # For row vectors, vehicle = sensor @ R.T, so sensor = vehicle @ R.
    xyz_sensor = xyz_vehicle @ axis_matrix(sensor_cfg).astype(np.float32)
    elevation = np.degrees(np.arctan2(
        xyz_vehicle[:, 2], np.hypot(xyz_vehicle[:, 0], xyz_vehicle[:, 1])
    ))
    ring = np.abs(elevation[:, None] - RING_ELEVATION_DEG[None, :]).argmin(axis=1)
    raw = np.zeros(xyz_sensor.shape[0], dtype=COMPACT_DTYPE)
    raw["x"], raw["y"], raw["z"] = xyz_sensor[:, 0], xyz_sensor[:, 1], xyz_sensor[:, 2]
    raw["intensity"] = frame.intensity
    raw["ring"] = ring.astype(np.uint16)
    packed = compact_to_compact16(raw)
    if packed.size != raw.size:
        raise ValueError("synthetic points unexpectedly exceeded compact16 range")
    return packed, np.asarray(labels, dtype=np.uint8)


def object_transform(spec: ObstacleSpec, track) -> dict:
    mesh_origin = [spec.distance + spec.size[0] / 2,
                   float(track.center_y(spec.distance + spec.size[0] / 2)) + spec.lateral,
                   float(spec.base_z)]
    center = [mesh_origin[0], mesh_origin[1], mesh_origin[2] + spec.size[2] / 2]
    return {
        "kind": spec.kind,
        "size_m_xyz": list(spec.size),
        "nearest_face_distance_m": spec.distance,
        "lateral_offset_from_track_m": spec.lateral,
        "yaw_deg": spec.yaw_deg,
        "mesh_origin_vehicle_m": [round(float(v), 5) for v in mesh_origin],
        "center_vehicle_m": [round(float(v), 5) for v in center],
        "reflectivity": spec.reflectivity,
        "placement": "box mesh bottom at base_z; lateral is relative to synthetic track axis",
    }


def write_scene(output: Path, name: str, specs: list[ObstacleSpec], frame_seeds: list[int], sensor_cfg,
                *, keep_masks: bool) -> tuple[list[dict], dict]:
    frames_dir = output / "frames" / name
    masks_dir = output / "masks" / name
    frames_dir.mkdir(parents=True, exist_ok=True)
    if keep_masks:
        masks_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    scene_manifest = None
    for index, seed in enumerate(frame_seeds):
        frame, labels, track = synthetic_tunnel_frame(
            rng=np.random.default_rng(seed), specs=specs,
        )
        packed, labels = to_compact16(frame, labels, sensor_cfg)
        frame_name = f"frame_{index:03d}.npy"
        frame_path = frames_dir / frame_name
        np.save(frame_path, packed, allow_pickle=False)
        row = {
            "index": index,
            "stamp_s": round(index / 10.0, 3),
            "points_file": frame_path.relative_to(output).as_posix(),
            "point_count": int(packed.size),
            "point_sha256": sha256(frame_path),
            "rng_seed": int(seed),
            "object_return_counts": {
                str(k): int(np.count_nonzero(labels == k)) for k in range(1, len(specs) + 1)
            },
        }
        if keep_masks:
            for k in range(1, len(specs) + 1):
                mask = labels == k
                mask_path = masks_dir / f"object_{k}_frame_{index:03d}.bits.npy"
                packed_mask = np.packbits(mask, bitorder="little")
                np.save(mask_path, packed_mask, allow_pickle=False)
                row.setdefault("object_masks", {})[str(k)] = {
                    "file": mask_path.relative_to(output).as_posix(),
                    "encoding": "numpy.packbits(bitorder='little'); one bit per point row",
                    "point_count": int(packed.size),
                    "positive_count": int(mask.sum()),
                    "sha256": sha256(mask_path),
                }
        rows.append(row)
        if scene_manifest is None:
            scene_manifest = {
                "synthetic_track": track.to_dict(),
                "obstacles": [object_transform(s, track) for s in specs],
                "background_model": {
                    "type": "fully ray-cast round tunnel with flat bed, two side benches, two rails",
                    "length_m": 250.0,
                    "radius_m": 2.7,
                    "axis_y_m": 0.25,
                    "axis_z_m": 0.8,
                    "floor_z_m": -1.5,
                },
            }
    return rows, scene_manifest or {"obstacles": [], "background_model": {}}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed", type=int, default=20260928)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    if any(output.iterdir()):
        old_manifest = output / "manifest.json"
        if not old_manifest.is_file():
            raise SystemExit(f"refusing to overwrite non-fixture directory: {output}")
        try:
            old_schema = json.loads(old_manifest.read_text(encoding="utf-8")).get("schema")
        except (OSError, json.JSONDecodeError):
            old_schema = None
        if old_schema != SCHEMA:
            raise SystemExit(f"refusing to overwrite a different fixture: {output}")

    cfg = DetectorConfig()
    rail = ObstacleSpec(
        kind="box", size=(0.4, 0.6, 0.31), distance=24.0, lateral=0.8,
        yaw_deg=0.0, reflectivity=30.0, label="stationary low box across the positive rail",
        base_z=-1.5,
    )
    positive_seeds = [args.seed + i for i in range(12)]
    clear_seeds = [args.seed + 100 + i for i in range(6)]

    positive_rows, positive_scene = write_scene(
        output, "rail_straddle", [rail], positive_seeds, cfg.sensor, keep_masks=True,
    )
    clear_rows, clear_scene = write_scene(
        output, "clear_tunnel", [], clear_seeds, cfg.sensor, keep_masks=False,
    )

    long_gap_windows = [(110, 112), (116, 118), (196, 198)]
    long_replay = []
    for index in range(205):
        source = positive_rows[index % len(positive_rows)]
        drop = any(start <= index < end for start, end in long_gap_windows)
        long_replay.append({
            "frame_index": index,
            "stamp_s": round(index / 10.0, 3),
            "frame_ref": source["points_file"],
            "mask_ref": source["object_masks"]["1"]["file"],
            "drop_target_returns": drop,
        })

    survey_rows: list[dict] = []
    survey_specs: list[dict] = []
    survey_cases = [
        ((0.3, 0.3, 0.3), 50.0, 0.0, -4.0),
        ((0.3, 0.3, 0.3), 75.0, 1.0, 3.0),
        ((0.3, 0.3, 0.3), 100.0, 1.0, -2.0),
        ((0.5, 0.5, 0.5), 50.0, 1.0, 5.0),
        ((0.5, 0.5, 0.5), 75.0, 0.0, -3.0),
        ((0.5, 0.5, 0.5), 100.0, 1.0, 2.0),
    ]
    survey_dir = output / "frames" / "range_edge_survey"
    survey_mask_dir = output / "masks" / "range_edge_survey"
    survey_dir.mkdir(parents=True, exist_ok=True)
    survey_mask_dir.mkdir(parents=True, exist_ok=True)
    for i, (size, distance, lateral, yaw) in enumerate(survey_cases):
        spec = ObstacleSpec(
            kind="box", size=size, distance=distance, lateral=lateral, yaw_deg=yaw,
            reflectivity=30.0, label=f"{int(size[0] * 100)}cm box range/edge visibility sample",
            base_z=-1.5,
        )
        seed = args.seed + 200 + i
        frame, labels, track = synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=[spec])
        packed, labels = to_compact16(frame, labels, cfg.sensor)
        stem = f"box_{int(size[0] * 100)}cm_{int(distance)}m_{'edge' if lateral else 'center'}"
        frame_path = survey_dir / f"{stem}.npy"
        np.save(frame_path, packed, allow_pickle=False)
        mask = labels == 1
        mask_path = survey_mask_dir / f"{stem}.bits.npy"
        np.save(mask_path, np.packbits(mask, bitorder="little"), allow_pickle=False)
        survey_rows.append({
            "case": stem,
            "points_file": frame_path.relative_to(output).as_posix(),
            "point_count": int(packed.size),
            "point_sha256": sha256(frame_path),
            "rng_seed": seed,
            "object_mask": {
                "file": mask_path.relative_to(output).as_posix(),
                "encoding": "numpy.packbits(bitorder='little'); one bit per point row",
                "point_count": int(packed.size),
                "positive_count": int(mask.sum()),
                "sha256": sha256(mask_path),
            },
            "obstacle": object_transform(spec, track),
            "purpose": "sensor sampling/coverage probe only; detector success is not guaranteed",
        })
        survey_specs.append(spec.to_dict())

    manifest = {
        "schema": SCHEMA,
        "provenance": {
            "synthetic": True,
            "not_organizer_data": True,
            "not_real_world_validation": True,
            "generator": {
                "path": "scripts/generate_synthetic_lidar_fixture.py",
                "sha256": sha256(ROOT / "scripts" / "generate_synthetic_lidar_fixture.py"),
                "ray_caster_base_commit": "a2f9122acdd9de83d4bf30a2befdc0d3e1f9cdd5",
            },
            "base_seed": int(args.seed),
            "seed_policy": "base seed plus fixed offsets; each frame uses its own seed",
            "ray_caster": "resense.synthetic.synthetic_tunnel_frame (Open3D RaycastingScene)",
            "track_truth_available": True,
        },
        "sensor": {
            "model": "Hesai Pandar128 E3X model from resense.sensor",
            "frame_rate_hz": 10,
            "azimuth_fov_deg": [-50.0, 50.0],
            "azimuth_step_deg": 0.1,
            "rings": 128,
            "return_model": "single nearest hit per ray; the synthetic fixture does not model the Pandar dual-return slots",
            "ray_hit_noise": "synthetic_tunnel_frame defaults: Gaussian range sigma 0.01 m times (1 + range/100), intensity multiplier N(1, 0.1)",
            "ring_assignment": "nearest configured ring elevation to ray-hit elevation",
            "saved_coordinate_frame": "sensor frame expected by frame_from_compact",
            "array_dtype": "COMPACT16_DTYPE: x/y/z int16 cm, intensity uint8, ring uint8",
            "quantization_m": 0.01,
            "mount_transform": {
                "sensor_config": cfg.sensor.__dict__,
                "vehicle_from_sensor_matrix": axis_matrix(cfg.sensor).tolist(),
                "encoding_rule": "vehicle row-vector coordinates multiplied by this matrix to save sensor-frame coordinates",
            },
        },
        "label_encoding": {
            "0": "background return or non-object return",
            "1": "rail-straddling target object return",
            "mask_storage": "per-object bit-packed Boolean mask aligned with the point rows in the matching frame",
            "mask_bit_order": "little",
        },
        "scenes": {
            "rail_straddle": {
                **positive_scene,
                "frames": positive_rows,
                "sequence": {
                    "stationary_target": True,
                    "frame_rate_hz": 10,
                    "positive_warmup_frames": 6,
                    "gap_start_index": 6,
                    "positive_recovery_frames": 3,
                    "gap_variants": [0, 1, 2, 3],
                    "dropout_semantics": "For a gap variant of N frames, remove target-mask rows from frames [6, 6+N); object-hit rays become no returns and the target has occluded the background behind it.",
                    "observation_notes": "Six visible frames make the target a reported track with the baseline config; verify the desired tracker behavior after masking returns before using this as an expected-result test.",
                },
            },
            "long_dropout_replay": {
                "sequence_length": len(long_replay),
                "frame_rate_hz": 10,
                "frames": long_replay,
                "source_reuse": "the 12 rail_straddle clouds cycle by frame index modulo 12; masks are applied to the referenced source cloud",
                "drop_windows_half_open": [{"start": a, "end": b} for a, b in long_gap_windows],
                "window_note": "these 2-frame gaps reproduce the index scale of the reported track-continuity cases; they are not copied from any recording",
                "purpose": "long-running tracker continuity/recovery smoke scenario with three known missing-return windows",
            },
            "clear_tunnel": {
                **clear_scene,
                "frames": clear_rows,
                "sequence": {"empty_scene": True, "frame_rate_hz": 10},
            },
            "single_frame_transient": {
                "sequence_length": 7,
                "frame_rate_hz": 10,
                "frames": [
                    {"frame_ref": f"frames/clear_tunnel/frame_{i:03d}.npy", "target_visible": False}
                    for i in range(3)
                ] + [
                    {"frame_ref": "frames/rail_straddle/frame_006.npy", "mask_ref": "masks/rail_straddle/object_1_frame_006.bits.npy", "target_visible": True}
                ] + [
                    {"frame_ref": f"frames/clear_tunnel/frame_{i:03d}.npy", "target_visible": False}
                    for i in range(3, 6)
                ],
                "purpose": "One-frame object-return transient surrounded by fully clear synthetic scans; useful as a persistence negative control.",
            },
            "range_edge_survey": {
                "cases": survey_rows,
                "purpose": "Coverage-only samples for 0.3 m and 0.5 m boxes at 50 m, 75 m, and 100 m, with center/edge lateral placements and varied yaw/seed.",
            },
        },
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output / "README.md").write_text(readme_text(), encoding="utf-8")
    print(f"Wrote {output}")
    print(f"Manifest SHA-256: {sha256(manifest_path)}")
    print(f"Rail target returns/frame: {[r['object_return_counts']['1'] for r in positive_rows]}")
    print(f"Range survey target returns: {[r['object_mask']['positive_count'] for r in survey_rows]}")


def readme_text() -> str:
    return """# Synthetic LiDAR detector fixture v1

This fixture is generated entirely from the repository's round-tunnel mesh and Pandar128
ray grid. It is controlled regression data, **not organizer data, not real LiDAR, and not
evidence of performance on unseen tunnels**.

## Files

- `frames/**/*.npy`: ordinary cache-compatible `COMPACT16_DTYPE` point arrays in sensor
  coordinates (`xyz` in centimetres, intensity and ring as bytes).
- `masks/**/*.bits.npy`: bit-packed per-object masks aligned with the corresponding point rows.
  Decode with `np.unpackbits(mask, bitorder="little")[:point_count].astype(bool)`.
- `manifest.json`: seeds, sensor transform, mesh placements, frame stamps, hashes, point
  counts, masks, and scenario schedules.

The `rail_straddle` scene is a stationary 0.4 x 0.6 x 0.31 m box across one rail at 24 m.
Its 12 frames are all generated with visible object returns. To form a gap variant, load the
matching object mask and remove those point rows from frames `[6, 6 + gap_frames)`, with
`gap_frames` in 0, 1, 2, or 3. This models missing target returns; object rays stay occluded
behind the object. Six visible frames precede the gap and three follow it.

`clear_tunnel` supplies empty-scene frames. `single_frame_transient` references clear frames
with one visible target frame between them. `range_edge_survey` contains individual 0.3 m and
0.5 m box scans at 50/75/100 m, varying center/edge placement, yaw, and seed. Those far samples
are for point-coverage probes; they are not guaranteed detections.

Regenerate from the repository root with:

```sh
python scripts/generate_synthetic_lidar_fixture.py --output tests/fixtures/synthetic_lidar_v1
```

The command only overwrites an existing output when its manifest has this fixture's schema.
The fixture itself can be loaded without Open3D; Open3D is only needed to regenerate it.
"""


if __name__ == "__main__":
    main()
