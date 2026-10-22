"""Compress a .npy frame cache in place to .npy.zst (level 3), checking each frame decodes to the same array."""
import glob, os, sys
import numpy as np, zstandard, io
d = sys.argv[1]; c = zstandard.ZstdCompressor(level=3); dz = zstandard.ZstdDecompressor()
n = 0
for f in sorted(glob.glob(os.path.join(d, "*.npy"))):
    raw = open(f, "rb").read(); z = c.compress(raw)
    a = np.load(io.BytesIO(raw)); b = np.load(io.BytesIO(dz.decompress(z)))
    assert a.dtype == b.dtype and a.shape == b.shape and np.array_equal(a, b), f
    tmp = f + ".zst.tmp"; open(tmp, "wb").write(z); os.replace(tmp, f + ".zst"); os.remove(f); n += 1
print(f"{d}: {n} frames compressed, every one decoded equal")
