"""scripts/ci_image_inputs.py: which pushes can change the Docker image (ci.yml's `changes` job).

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
spec = importlib.util.spec_from_file_location("ci_image_inputs", ROOT / "scripts" / "ci_image_inputs.py")
cii = importlib.util.module_from_spec(spec)
sys.modules["ci_image_inputs"] = cii
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
