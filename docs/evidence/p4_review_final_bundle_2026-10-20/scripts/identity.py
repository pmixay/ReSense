"""Archive integrity and source identity.

    python identity.py hashes <extracted dir> <raw-manifest.json>      # every member's sha256 and size
    python identity.py source <extracted dir> <git rev> [<git rev> ...]  # every *-source.tar.gz member vs the git blob

``source`` reports, per tarball and per revision, how many text members are byte-equal to ``git show <rev>:<path>``.
The reference tarballs (the base the candidate was compared with) are the positive control: they must differ from the
final revision in exactly the files the patch changed. The compiled native library is not in git and is only listed.
Run it from inside the repository checkout.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys
import tarfile


def hashes(root, manifest):
    m = json.load(open(manifest))
    if isinstance(m, dict) and "members" in m:
        m = m["members"]
    items = [(e["path"], e["sha256"], e["bytes"]) for e in m] if isinstance(m, list) else \
        [(p, v["sha256"], v["bytes"]) for p, v in m.items()]
    bad = miss = 0
    for p, sha, size in items:
        f = os.path.join(root, p)
        if not os.path.exists(f):
            miss += 1
            print("MISSING", p)
            continue
        if hashlib.sha256(open(f, "rb").read()).hexdigest() != sha or os.path.getsize(f) != size:
            bad += 1
            print("BAD", p)
    print(f"{manifest}: members {len(items)} missing {miss} bad {bad}")


def blob(rev, path):
    r = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, check=False)
    return r.stdout if r.returncode == 0 else None


def source(root, revs):
    for tp in sorted(glob.glob(os.path.join(root, "*source.tar.gz"))):
        t = tarfile.open(tp)
        members = [m for m in t.getmembers() if m.isfile()]
        data = {m.name: t.extractfile(m).read() for m in members}
        for rev in revs:
            eq, ne, ng, diff = 0, 0, [], []
            for name, d in data.items():
                b = blob(rev, name)
                if b is None:
                    ng.append(name)
                elif b == d:
                    eq += 1
                else:
                    ne += 1
                    diff.append(name)
            print(f"{os.path.basename(tp):42s} {rev:8s} members {len(data)} equal {eq} differ {ne} {diff} not in git {ng}")


if __name__ == "__main__":
    if sys.argv[1] == "hashes":
        hashes(sys.argv[2], sys.argv[3])
    else:
        source(sys.argv[2], sys.argv[3:])
