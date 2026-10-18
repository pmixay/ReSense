"""Offline dust placement in a frozen clean calibrated frame.

These helpers are for single-threaded evaluation only. No reference, source index
or augmentation truth is passed to the detector. The reference is a flat cloud
height anchored at clean rail_z(20 m), not a surveyed or graded rail plane.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def source_frame_sha256(frame):
    digest = hashlib.sha256()
    for name in ("xyz", "intensity", "ring"):
        value = getattr(frame, name)
        digest.update(name.encode())
        if value is None:
            digest.update(b"None")
        else:
            value = np.asarray(value)
            digest.update(str((value.dtype.str, value.shape)).encode())
            digest.update(value.tobytes(order="C"))
    digest.update(_digest({"stamp": frame.stamp, "frame_id": frame.frame_id,
                           "meta": frame.meta}).encode())
    return digest.hexdigest()


def process_clean_reference(detector, frame):
    """Process clean input and capture its actual final applied rotation.

    Observing the class method also catches a fresh calibrator created by startup
    replay. Recording the applied matrix handles identity shortcuts and changes
    below the calibrator's update threshold. The original method is always restored.
    """
    cls = type(detector.calib)
    original = cls.apply
    applied = {}

    def observe(calibrator, xyz):
        rotation = calibrator.R.copy()
        result = original(calibrator, xyz)
        applied[id(calibrator)] = (np.eye(3, dtype=np.float32) if result is xyz
                                    else rotation.astype(np.float32))
        return result

    source_hash = source_frame_sha256(frame)
    try:
        cls.apply = observe
        result = detector.process(frame)
    finally:
        cls.apply = original
    if id(detector.calib) not in applied:
        raise ValueError("clean process did not apply its final calibrator")
    reference = {"schema": "dust-clean-reference-v1",
                 "input_to_model_rotation": applied[id(detector.calib)].tolist(),
                 "rail_z_at20": float(result.track.rail_z(np.array([20.]))[0]),
                 "source_frame_sha256": source_hash}
    reference["reference_sha256"] = _digest(reference)
    _validated_rotation(reference)
    return result, reference


def _validated_rotation(reference):
    payload = {k: v for k, v in reference.items() if k != "reference_sha256"}
    if reference.get("schema") != "dust-clean-reference-v1" or _digest(payload) != reference.get("reference_sha256"):
        raise ValueError("invalid clean reference identity")
    rotation = np.asarray(reference["input_to_model_rotation"], dtype=np.float32)
    if (rotation.shape != (3, 3) or not np.isfinite(rotation).all()
            or not np.allclose(rotation @ rotation.T, np.eye(3), atol=3e-7, rtol=0)
            or not np.isclose(np.linalg.det(rotation), 1, atol=3e-7, rtol=0)
            or not np.isfinite(reference["rail_z_at20"])):
        raise ValueError("clean reference must contain a finite proper rotation and rail height")
    return rotation


def augment_in_reference(frame, spec, reference, *, seed=0, frame_index=0, augment=None):
    """Generate/attenuate in clean model axes, return input axes with exact real points."""
    from resense.frame import Frame
    if augment is None:
        from resense.dust import augment_dust
        augment = augment_dust
    rotation = _validated_rotation(reference)
    if source_frame_sha256(frame) != reference["source_frame_sha256"]:
        raise ValueError("source input differs from the frozen clean reference")
    identity = np.array_equal(rotation, np.eye(3, dtype=np.float32))
    aligned = Frame(frame.xyz if identity else frame.xyz @ rotation.T,
                    frame.intensity, frame.ring, frame.stamp, frame.frame_id, dict(frame.meta))
    result, audit, indices = augment(aligned, spec, rail_z=reference["rail_z_at20"],
                                     seed=seed, frame_index=frame_index)
    retained = indices >= 0
    # Invert only generated returns. Restoring originals avoids round-trip drift
    # in obstacle/rail points and preserves clean intensities/rings byte for byte.
    if not identity:
        inverse = np.linalg.inv(rotation.astype(np.float64)).astype(np.float32)
        result.xyz[~retained] = result.xyz[~retained] @ inverse.T
    result.xyz[retained] = frame.xyz[indices[retained]]
    result.intensity[retained] = frame.intensity[indices[retained]]
    if result.ring is not None:
        result.ring[retained] = frame.ring[indices[retained]]
    audit = {**audit, "placement_reference": reference}
    return result, audit, indices
