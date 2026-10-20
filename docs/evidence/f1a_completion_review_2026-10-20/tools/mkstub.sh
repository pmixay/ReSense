#!/bin/bash
# Build a stub libEGL.so.1 (the container has no libEGL; open3d needs it only for offscreen rendering,
# which the repo's synthetic tests do not use). Symbols are taken from open3d's own undefined list.
S=/tmp/claude-0/-home-user-ReSense/2f98805c-ba30-5c4f-b1a6-a591bfc61cdc/scratchpad/f1a_review
cd $S/stublib || exit 1
nm -D -u $S/venv/lib/python3.12/site-packages/open3d/libOpen3D.so.0.20 | grep -i " egl" | awk '{print $2}' | sed 's/@.*//' | sort -u > syms.txt
wc -l syms.txt
: > e.c
for s in $(cat syms.txt); do echo "void* $s(){return 0;}" >> e.c; done
gcc -shared -fPIC -o libEGL.so.1 e.c -Wl,-soname,libEGL.so.1
LD_LIBRARY_PATH=$S/stublib $S/venv/bin/python -c "import open3d as o3d; import numpy as np; p=o3d.geometry.PointCloud(); p.points=o3d.utility.Vector3dVector(np.random.rand(100,3)); print(o3d.__version__, len(p.cluster_dbscan(0.2,3)))" 2>&1 | tail -3
