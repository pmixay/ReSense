"""scripts/ci_changes.py: which pushes can change the Docker image or affect the web checks (ci.yml's `checks` job).

Most cases use a small inline Dockerfile so that they run where docker/ is absent (the image's own test
run). The case that reads the repository's Dockerfile carries ``realdata`` on the docker/ folder and is
deselected there, like the other tests that need files the image does not carry.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ci_changes", ROOT / "scripts" / "ci_changes.py")
cii = importlib.util.module_from_spec(spec)
sys.modules["ci_changes"] = cii
spec.loader.exec_module(cii)

DOCKERFILE = """
FROM ros:humble-ros-base-jammy
COPY pyproject.toml setup.py README.md ./
COPY native ./native
COPY resense ./resense
RUN pip install .
COPY docs/evidence/results/residual_events_2026-09-28.json ./docs/evidence/results/residual_events_2026-09-28.json
COPY docs/evidence/a/probe.py docs/evidence/a/runner.py ./docs/evidence/a/
COPY --chown=1000:1000 webapp/backend/resense_web/__init__.py ./webapp/backend/resense_web/
COPY --from=builder /build/out /opt/out
COPY ros2_ws/src /opt/resense/ros2_ws/src
COPY docker/entrypoint.sh /entrypoint.sh
"""


def relevant(*paths: str) -> bool:
    return cii.decide(list(paths), DOCKERFILE)


def test_copy_sources_are_read_without_flags_destinations_or_other_stages():
    sources = cii.copy_sources(DOCKERFILE)
    assert {"pyproject.toml", "setup.py", "README.md", "native", "resense", "ros2_ws/src", "docker/entrypoint.sh",
            "docs/evidence/a/probe.py", "docs/evidence/a/runner.py", "webapp/backend/resense_web/__init__.py"} <= set(sources)
    assert "/build/out" not in sources and "/opt/out" not in sources            # --from=builder: not from the repository
    assert "./native" not in sources and "/entrypoint.sh" not in sources        # destinations are not sources
    assert not any(s.startswith("--") for s in sources)


@pytest.mark.parametrize("path", [
    "docs/BACKLOG.md", "docs/evidence/p4_dust_markers_final_2026-10-20/README.md", "gitbook/faq.md", "CHANGELOG.md",
    "web/index.html", "webapp/frontend/src/App.tsx", "webapp/e2e/conftest.py", "labels/other.json", "DESIGN.md",
    "docs/evidence/a/other_file.py",
])
def test_changes_to_files_the_image_does_not_copy_cannot_reach_it(path):
    assert relevant(path) is False


@pytest.mark.parametrize("path", [
    "resense/detector.py", "native/rs.c", "ros2_ws/src/resense_ros/setup.py", "README.md", "pyproject.toml", "setup.py",
    "docs/evidence/results/residual_events_2026-09-28.json", "docs/evidence/a/probe.py",
    "webapp/backend/resense_web/__init__.py",
])
def test_changes_to_what_the_dockerfile_copies_reach_the_image(path):
    assert relevant(path) is True


@pytest.mark.parametrize("path", [
    ".github/workflows/ci.yml", "./.github/workflows/ci.yml", "docker/Dockerfile", "docker/fastdds_udp.xml",
    "scripts/console_test.sh", "scripts/build_deck.py", ".dockerignore", "docs/evidence/bag_metadata/x_metadata.yaml",
])
def test_things_the_ci_steps_read_from_the_checkout_always_run_the_image_jobs(path):
    assert relevant(path) is True


def test_a_name_that_only_starts_like_a_copied_folder_is_not_inside_it():
    assert relevant("resense_notes/readme.txt") is False and relevant("nativefoo/x") is False


def test_one_relevant_file_among_many_irrelevant_ones_decides():
    assert relevant("docs/a.md", "docs/b.md", "gitbook/c.md") is False
    assert relevant("docs/a.md", "docs/b.md", "resense/tracking.py") is True


def test_no_changed_files_cannot_reach_the_image():
    assert relevant() is False


@pytest.mark.realdata(str(ROOT / "docker"))
def test_the_repository_dockerfile_copies_its_code_and_not_its_documents():
    text = (ROOT / "docker" / "Dockerfile").read_text(encoding="utf-8")
    assert cii.decide(["docs/BACKLOG.md", "CHANGELOG.md", "gitbook/faq.md", "web/README.md", "webapp/e2e/conftest.py"], text) is False
    assert cii.decide(["resense/tracking.py", "configs/default.yaml", "tests/test_algorithm.py", "README.md"], text) is True
    # every source the Dockerfile copies must itself count as an image input
    for src in cii.copy_sources(text):
        assert cii.decide([src], text) is True, src


@pytest.mark.parametrize("before", ["", "0" * 40])
def test_a_new_branch_has_no_previous_tip(before):
    assert cii.changed_files(before, "HEAD") is None


# ----------------------------------------------------------------------------------------- the web rule


def web(*paths: str) -> bool:
    return cii.decide_web(list(paths))


@pytest.mark.parametrize("path", [
    "webapp/frontend/src/App.tsx", "webapp/e2e/conftest.py", "webapp/backend/resense_web/api.py", "web/demo/test_web.py",
    "resense/tracking.py", "native/rs.c", "configs/default.yaml", "labels/doubleT_obstacle.json",
    "ros2_ws/src/resense_ros/resense_ros/decision_policy.py", "scripts/check_webapp_wheels.py", "scripts/hero_view.py",
    "pyproject.toml", "setup.py", ".github/workflows/ci.yml", "./.github/workflows/ci.yml",
    "docs/evidence/docker_2026-09-23/obstacle_status.jsonl.gz",
])
def test_changes_the_web_checks_import_read_or_run_run_them(path):
    assert web(path) is True


@pytest.mark.parametrize("path", [
    "docs/BACKLOG.md", "docs/evidence/p4_dust_markers_final_2026-10-20/README.md", "gitbook/faq.md", "CHANGELOG.md",
    "README.md", "tests/test_algorithm.py", "docker/Dockerfile", "docs/images/player/overview.png",
])
def test_documents_evidence_and_the_rest_do_not_run_the_web_checks(path):
    assert web(path) is False


def test_a_name_that_only_starts_like_a_web_folder_is_not_inside_it():
    assert web("webapp_notes.md") is False and web("website/x") is False and web("resense_notes/x") is False


def test_one_web_file_among_documents_decides():
    assert web("docs/a.md", "gitbook/b.md") is False
    assert web("docs/a.md", "webapp/frontend/src/App.tsx") is True
    assert web() is False


def test_a_docs_only_push_runs_neither_the_image_jobs_nor_the_web_checks():
    paths = ["docs/BACKLOG.md", "docs/CAPTAIN.md", "CHANGELOG.md", "gitbook/development/setup-and-ci.md"]
    assert relevant(*paths) is False and web(*paths) is False


@pytest.mark.realdata(str(ROOT / "webapp"))
def test_the_web_suites_read_no_document_contents():
    """The rule leaves documents out of the web checks: nothing under web/ or webapp/ may read a docs/ file other than
    the frozen recording named in WEB_PREFIXES (the web code only builds links to documents)."""
    import re
    readers = []
    for base in ("web", "webapp/backend", "webapp/e2e"):
        for f in (ROOT / base).rglob("*.py"):
            if "node_modules" in f.parts:
                continue
            for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(r"(ROOT|REPO|root|repo)[A-Za-z_]*\s*/\s*['\"]docs['\"]", line) and "docker_2026-09-23" not in line \
                        and "docs/evidence" not in line and "images" not in line:
                    readers.append(f"{f.relative_to(ROOT)}:{n}: {line.strip()[:90]}")
    # the dashboard's own manual scripts (capture_gallery, check_status_compatibility) read evidence and write images;
    # they are not part of the CI steps. Any other reader would make the rule unsafe.
    assert readers == [], readers
