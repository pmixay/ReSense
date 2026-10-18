"""Deterministic N2 input-format and sampling probes; no detector or truth modification."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np


def field_message(
    xyz, intensity, ring, *, coordinate_dtype="f4", intensity_dtype="f4", padded=False
):
    """Encode equivalent points in PCL-style or float64 PointCloud2 layouts.

    An odd point count gets one zero-return slot in an organized two-row message.
    Padding uses nonzero bytes to expose readers that mistake row padding for points.
    """
    wide = coordinate_dtype == "f8"
    step = 48 if wide else 32
    offsets = [0, 8, 16] if wide else [0, 4, 8]
    names, formats = (
        ["x", "y", "z", "intensity"],
        [coordinate_dtype] * 3 + [intensity_dtype],
    )
    offsets.append(24 if wide else 16)
    if ring is not None:
        names.append("ring")
        formats.append("u2")
        offsets.append(30 if wide else 20)
    dtype = np.dtype(
        {"names": names, "formats": formats, "offsets": offsets, "itemsize": step}
    )
    count = len(xyz) + int(padded and len(xyz) % 2)
    array = np.zeros(count, dtype=dtype)
    for axis, name in enumerate(("x", "y", "z")):
        array[name][: len(xyz)] = xyz[:, axis]
    array["intensity"][: len(xyz)] = intensity
    if ring is not None:
        array["ring"][: len(xyz)] = ring
    height = 2 if padded else 1
    width = count // height
    row_step = width * step + (37 if padded else 0)
    data = (
        array[:width].tobytes()
        + bytes([0x7F]) * 37
        + array[width:].tobytes()
        + bytes([0x7F]) * 37
        if padded
        else array.tobytes()
    )
    field_types = {"f4": 7, "f8": 8, "u1": 2, "u2": 4}
    fields = [
        SimpleNamespace(name=n, offset=o, datatype=field_types[f], count=1)
        for n, o, f in zip(names, offsets, formats)
    ]
    return SimpleNamespace(
        fields=fields,
        point_step=step,
        row_step=row_step,
        width=width,
        height=height,
        is_bigendian=False,
        is_dense=False,
        data=data,
        header=SimpleNamespace(
            stamp=SimpleNamespace(sec=0, nanosec=0), frame_id="n2_probe"
        ),
    )


def falcon_proxy_indices(vehicle_xyz):
    """Nearest unique return per documented Falcon angular cell, with a centred ROI.

    This only removes real Pandar samples; it cannot synthesize Falcon's denser ROI
    rays or its curved raster, different wavelength/noise or object reflectivity.
    The proxy is therefore a documented stress transform, not a sensor simulator.
    """
    points = np.asarray(vehicle_xyz)
    distance = np.linalg.norm(points, axis=1)
    azimuth = np.degrees(np.arctan2(points[:, 1], points[:, 0]))
    elevation = np.degrees(
        np.arctan2(points[:, 2], np.linalg.norm(points[:, :2], axis=1))
    )
    keep = np.flatnonzero(
        np.isfinite(points).all(axis=1)
        & (distance >= 1.5)
        & (points[:, 0] > 0)
        & (np.abs(azimuth) <= 60)
        & (elevation >= -13)
        & (elevation <= 12)
    )
    if not keep.size:
        return keep
    roi = (np.abs(azimuth[keep]) <= 20) & (np.abs(elevation[keep]) <= 2.4)
    hstep, vstep = np.where(roi, 0.09, 0.18), np.where(roi, 0.08, 0.24)
    hbin = np.floor((azimuth[keep] + 60) / hstep).astype(np.int64)
    vbin = np.floor((elevation[keep] + 13) / vstep).astype(np.int64)
    order = np.lexsort((keep, distance[keep], hbin, vbin, roi))
    keys = np.column_stack((roi, vbin, hbin))[order]
    first = np.r_[True, np.any(keys[1:] != keys[:-1], axis=1)]
    return np.sort(keep[order[first]])
