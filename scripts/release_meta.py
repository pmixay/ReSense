#!/usr/bin/env python3
"""Release metadata: the package version, the release tag, the release notes.

Used by .github/workflows/release.yml and scripts/release.sh, so that the CI release and the
manual fallback check the same things and publish the same text. Needs nothing but python3.

    scripts/release_meta.py version              # the version, once all four declarations agree
    scripts/release_meta.py check-tag v1.0.0-rc1 # tag=, version=, prerelease= lines (GITHUB_OUTPUT)
    scripts/release_meta.py notes --tag v1.0.0-rc1 --commit <sha> --sha256 <hex> --bytes <n> \\
        [--repo pmixay/ReSense] [--image-id sha256:...] [--base-digest ros@sha256:...] [--docker 24.0.7] \\
        [--ci-run https://github.com/<repo>/actions/runs/<id>]

The version is declared in four places that must agree: pyproject.toml, resense/__init__.py,
ros2_ws/src/resense_ros/package.xml and ros2_ws/src/resense_ros/setup.py. A release tag is
``v<version>`` (the final release) or ``v<version>-<suffix>`` (a pre-release: ``v1.0.0-rc1``,
``-rc2``, ...); release candidates and the final tag share the version. Any suffix makes a
GitHub pre-release (semver), so a test tag never becomes the "latest" release.

Exit codes: 0 ok, 1 the declarations disagree, 2 a bad tag or argument.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPO = "pmixay/ReSense"
# the declarations: file (relative to the repository root) and the regex whose group 1 is the version
SOURCES = [
    ("pyproject.toml", r'(?m)^version\s*=\s*"([^"]+)"'),
    ("resense/__init__.py", r'(?m)^__version__\s*=\s*"([^"]+)"'),
    ("ros2_ws/src/resense_ros/package.xml", r"<version>\s*([^<\s]+)\s*</version>"),
    ("ros2_ws/src/resense_ros/setup.py", r'(?m)^\s*version\s*=\s*"([^"]+)"'),
]
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
# v<major>.<minor>.<patch>[-<suffix>] (whole string: fullmatch); the suffix is a semver pre-release,
# dot-separated identifiers of letters, digits and hyphens
TAG_RE = re.compile(r"v([0-9]+\.[0-9]+\.[0-9]+)(?:-([0-9A-Za-z][0-9A-Za-z-]*(?:\.[0-9A-Za-z][0-9A-Za-z-]*)*))?")


def declared_versions(root: Path = ROOT) -> dict[str, str | None]:
    """{file: version or None when the file or the declaration is missing}."""
    out: dict[str, str | None] = {}
    for rel, pattern in SOURCES:
        path = root / rel
        try:
            m = re.search(pattern, path.read_text(encoding="utf-8"))
        except OSError:
            m = None
        out[rel] = m.group(1) if m else None
    return out


def package_version(root: Path = ROOT) -> str:
    """The one version all declarations agree on; ValueError naming the disagreement otherwise."""
    found = declared_versions(root)
    missing = [f for f, v in found.items() if v is None]
    if missing:
        raise ValueError("no version declaration found in " + ", ".join(missing))
    values = set(found.values())
    if len(values) != 1:
        raise ValueError("the version declarations disagree: "
                         + ", ".join(f"{f} {v}" for f, v in found.items()))
    version = values.pop()
    assert version is not None
    if not VERSION_RE.fullmatch(version):
        raise ValueError(f"version {version!r} is not <major>.<minor>.<patch>")
    return version


def parse_tag(tag: str, version: str) -> dict[str, str]:
    """{'tag', 'version', 'prerelease': 'true' | 'false'} for a tag of ``version``; ValueError
    with the reason for any other tag."""
    m = TAG_RE.fullmatch(tag)
    if not m:
        raise ValueError(f"tag {tag!r} is not a release tag: v<major>.<minor>.<patch> or "
                         f"v<major>.<minor>.<patch>-<suffix> (e.g. v{version}-rc1, v{version})")
    if m.group(1) != version:
        raise ValueError(f"tag {tag!r} names version {m.group(1)}, but the package is {version} "
                         f"(pyproject.toml and the three other declarations): tag v{version}-rcN / "
                         f"v{version}, or bump the version first")
    return {"tag": tag, "version": version, "prerelease": "true" if m.group(2) else "false"}


def human_bytes(n: int) -> str:
    return f"{n / 1073741824:.2f} GiB" if n >= 1073741824 // 10 else f"{n / 1048576:.1f} MiB"


def release_notes(tag: str, commit: str, sha256: str, size_bytes: int, repo: str = DEFAULT_REPO,
                  version: str | None = None, image_id: str | None = None,
                  base_digest: str | None = None, docker_version: str | None = None,
                  ci_run: str | None = None) -> str:
    """The GitHub release body (Markdown): the jury's commands first, then what identifies the build."""
    archive = f"resense-image-{tag}.tar.gz"
    web = f"https://github.com/{repo}"
    dl = f"{web}/releases/download/{tag}"
    pre = "-" in tag
    commands = [
        (f"sha256sum -c {archive}.sha256", "0. optional: the archive is intact (both files in one folder)"),
        (f"docker load -i {archive}", "1. once, no internet needed"),
        ("docker run --rm -it --net=host --ipc=host resense", "2. console 1: the node, no arguments"),
        ("ros2 bag play <bag> --delay 3", "3. console 2: any user, ROS 2 Humble"),
        ("ros2 topic echo /resense/decision --field data", "4. console 3: GO | CAUTION | STOP | FAULT"),
        ("ros2 topic echo /resense/nearest_distance --field data", "5. distance to the obstacle, m; -1 = none"),
    ]
    width = max(len(c) for c, _ in commands) + 2
    lines = [
        f"**ReSense {tag}**: LCT-2026, case 05, LiDAR obstacle detection in the metro clearance gauge "
        f"(ROS 2 Humble node in Docker)" + (" · release candidate" if pre else "") + ".",
        "",
        "The test stand has no internet, so the image comes built: "
        f"`{archive}` below is `docker save` of the runtime image, gzip, loaded with `docker load` "
        "on any Docker. Nothing in the node needs the network at run time.",
        "",
        "## Jury commands",
        "",
        "```bash",
        *(f"{c.ljust(width)}# {comment}" for c, comment in commands),
        "```",
        "",
        "`--net=host` is required (the image runs Fast DDS over UDP). No ROS 2 on the host: play from the image, "
        "`docker run --rm --net=host -v <bag folder>:/data:ro resense ros2 bag play /data/<bag> --delay 3`. "
        f"Details, expected output and parameters: [README]({web}/blob/{tag}/README.md) "
        "(section «Кратко для жюри»); what changed: "
        f"[CHANGELOG]({web}/blob/{tag}/CHANGELOG.md).",
        "",
        "## Identity",
        "",
        "| | |",
        "|---|---|",
        f"| archive | [`{archive}`]({dl}/{archive}), {size_bytes} bytes ({human_bytes(size_bytes)}) |",
        f"| sha256 | `{sha256}` |",
        f"| tag / commit | [`{tag}`]({web}/tree/{tag}) / [`{commit}`]({web}/commit/{commit}) |",
        f"| version | {version or tag.lstrip('v').split('-', 1)[0]} (`pyproject.toml`, the image label "
        "`org.opencontainers.image.version` carries the tag) |",
        "| image tags inside | `resense:" + tag + "`, `resense:latest` (+ the base image's tag, "
        "for an offline `docker build --cache-from`, best effort) |",
    ]
    if image_id:
        lines.append(f"| image ID | `{image_id}` |")
    if base_digest:
        lines.append(f"| base image | `{base_digest}` |")
    if docker_version:
        lines.append(f"| built with | Docker {docker_version}, `scripts/export_image.sh` from a clean checkout of the tag |")
    lines += [
        "",
        "Check a download without Docker: `scripts/verify_release.sh " + tag + "` (curl + sha256). "
        "Check and load with a no-network run of the image: `scripts/load_image.sh " + archive + "`. "
        "`SHA256SUMS` lists the same sum.",
        "",
    ]
    if ci_run:
        lines.append(f"Built and checked by `.github/workflows/release.yml` ([run]({ci_run})): the image was "
                     "removed after the export and loaded back from this archive; two synthetic bags (both "
                     "topic / frame pairs) were played through the loaded image with no internet (an "
                     "`--internal` Docker network, the player as uid 1000 in its own container) and in the "
                     "jury's form (`--net=host --ipc=host`, a stock Fast DDS player as uid 1000): STOP in "
                     "both recordings.")
    else:
        lines.append("Built with `scripts/release.sh` (the manual fallback of `.github/workflows/release.yml`): "
                     "the image was removed after the export, loaded back from this archive and run with no "
                     "network (`scripts/load_image.sh`).")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("version", help="print the package version (all four declarations must agree)")
    c = sub.add_parser("check-tag", help="validate a release tag against the package version")
    c.add_argument("tag")
    n = sub.add_parser("notes", help="print the release notes (Markdown)")
    n.add_argument("--tag", required=True)
    n.add_argument("--commit", required=True)
    n.add_argument("--sha256", required=True)
    n.add_argument("--bytes", type=int, required=True, dest="size_bytes")
    n.add_argument("--repo", default=DEFAULT_REPO)
    n.add_argument("--image-id", default=None)
    n.add_argument("--base-digest", default=None)
    n.add_argument("--docker", default=None, dest="docker_version")
    n.add_argument("--ci-run", default=None, help="URL of the workflow run that built and checked the archive")
    args = p.parse_args(argv)

    try:
        version = package_version()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    if args.cmd == "version":
        print(version)
        return 0
    try:
        info = parse_tag(args.tag, version)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    if args.cmd == "check-tag":
        for k, v in info.items():
            print(f"{k}={v}")
        return 0
    if not re.fullmatch(r"[0-9a-f]{64}", args.sha256):
        print(f"ERROR: --sha256 {args.sha256!r} is not 64 lowercase hex digits", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[0-9a-f]{7,40}", args.commit):
        print(f"ERROR: --commit {args.commit!r} is not a git commit hash", file=sys.stderr)
        return 2
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
        print(f"ERROR: --repo {args.repo!r} is not owner/name", file=sys.stderr)
        return 2
    sys.stdout.write(release_notes(args.tag, args.commit, args.sha256, args.size_bytes, repo=args.repo,
                                   version=version, image_id=args.image_id, base_digest=args.base_digest,
                                   docker_version=args.docker_version, ci_run=args.ci_run))
    return 0


if __name__ == "__main__":
    sys.exit(main())
