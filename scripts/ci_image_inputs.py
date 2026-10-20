#!/usr/bin/env python3
"""Does a push change anything that can enter the Docker image?  Prints ``image=true`` or ``image=false``.

    ci_image_inputs.py BEFORE AFTER      (the push's old and new commit, as ci.yml's `changes` job passes them)

The image holds only what docker/Dockerfile COPYs. A push whose changed files are all outside those paths
cannot change the image or the tests run in it, so ci.yml skips the jobs `docker` and `offline-build`
(about 20 runner-minutes) for it; `checks` and `pytest` always run. These always count as a change: the
workflows (.github/), docker/, scripts/ (the CI steps run them straight from the checkout), .dockerignore
and the bag metadata that the cold-bag cache key hashes. Everything unclear runs the jobs: a new branch
(BEFORE all zeros), a commit that cannot be fetched (a force-push) and a failed diff.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# read by CI steps from the checkout, or hashed into a cache key, whether or not the image copies them
ALWAYS_RELEVANT = (".github/", "docker/", "scripts/", "docs/evidence/bag_metadata/")
ALWAYS_RELEVANT_FILES = (".dockerignore",)


def copy_sources(dockerfile: str) -> list[str]:
    """Repository paths named as sources by the Dockerfile's COPY / ADD lines (flags and the destination dropped)."""
    sources: list[str] = []
    for raw in dockerfile.splitlines():
        parts = raw.split()
        if len(parts) < 3 or parts[0].upper() not in ("COPY", "ADD"):
            continue
        args = [p for p in parts[1:] if not p.startswith("--")]
        if any("--from" in p for p in parts[1:]):
            continue                                   # a file from another build stage, not from the repository
        sources.extend(a.removeprefix("./").rstrip("/") for a in args[:-1])
    return sources


def image_relevant(path: str, sources: list[str]) -> bool:
    """True if a change to ``path`` can reach the image build or the CI steps that run on it."""
    path = path.removeprefix("./")
    if path in ALWAYS_RELEVANT_FILES or path.startswith(ALWAYS_RELEVANT):
        return True
    return any(path == s or path.startswith(s + "/") for s in sources)


def decide(changed: list[str], dockerfile: str) -> bool:
    sources = copy_sources(dockerfile)
    return any(image_relevant(p, sources) for p in changed)


def changed_files(before: str, after: str) -> list[str] | None:
    """Paths that differ between two commits (renames count both sides); None if it cannot be told."""
    if not before or set(before) == {"0"}:
        return None                      # a new branch has no previous tip
    try:
        for ref in (before, after):
            have = subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"], cwd=ROOT, capture_output=True)
            if have.returncode != 0:
                fetch = subprocess.run(["git", "fetch", "--no-tags", "--depth=1", "origin", ref], cwd=ROOT,
                                       capture_output=True, text=True)
                if fetch.returncode != 0:
                    print(f"cannot fetch {ref}: {fetch.stderr.strip()[-200:]}", file=sys.stderr)
                    return None
        diff = subprocess.run(["git", "diff", "--name-only", "--no-renames", before, after], cwd=ROOT,
                              capture_output=True, text=True)
    except OSError as exc:
        print(f"git failed: {exc}", file=sys.stderr)
        return None
    if diff.returncode != 0:
        print(f"git diff failed: {diff.stderr.strip()[-200:]}", file=sys.stderr)
        return None
    return [p for p in diff.stdout.splitlines() if p]


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    changed = changed_files(argv[1], argv[2])
    if changed is None:
        print("image=true")
        print("no usable diff: running the image jobs", file=sys.stderr)
        return 0
    relevant = decide(changed, (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8"))
    print(f"image={'true' if relevant else 'false'}")
    print(f"{len(changed)} changed file(s); can reach the image: {relevant}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
