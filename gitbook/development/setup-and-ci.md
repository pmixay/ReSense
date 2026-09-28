# Setup, tests and CI

## Local setup

```bash
git clone https://github.com/pmixay/ReSense && cd ReSense
pip install -e ".[dev]"          # Python ≥ 3.10; builds the C++ kernels when a compiler is present
pytest -q                        # the suite; "skipped" means open3d is missing
pipx run ruff==0.15.8 check .    # lint, pinned as in CI
./scripts/sync_params.sh --check # the ROS parameter copy equals configs/default.yaml
python scripts/detector_freeze.py verify   # the sealed detector files are unchanged
```

`RESENSE_REQUIRE_SYNTHETIC=1 pytest -q` makes a missing open3d a failure instead of a skip, as in
CI.

The dashboard tests need Playwright and a Chromium build:

```bash
pip install playwright
python -m pytest -q web/demo
```

## In Docker

```bash
WITH_TOOLS=1 ./scripts/build.sh
docker run --rm -w / -e RESENSE_REQUIRE_SYNTHETIC=1 resense python3 -m pytest -q /opt/resense/tests
docker run --rm resense bash -lc "python3 scripts/make_smoke_bag.py /tmp/b && scripts/smoke_test.sh /tmp/b"
```

## CI

[`.github/workflows/ci.yml`](https://github.com/pmixay/ReSense/blob/main/.github/workflows/ci.yml)
runs on every push, in two stages:

| stage | job | what it proves |
|---|---|---|
| 1 | `checks` | ruff, the parameter copy in sync, the detector seal |
| 2 | `pytest` | the suite and the dashboard tests in headless Chromium; no test may be skipped |
| 2 | `docker` | the tools image: the suite inside it, the node reached every way the jury can (another container, a uid-1000 player, stock Fast DDS, `scripts/play_bag.sh`, shared-memory mode, a remote Foxglove viewer); on `main` also the two original bags from a cold disk |
| 2 | `offline-build` | the jury's runtime archive: made, every image removed, loaded back, rebuilt with no internet, both synthetic bags played through it on an internal network; on `main` the archive is uploaded as the run artifact |

[`.github/workflows/pages.yml`](https://github.com/pmixay/ReSense/blob/main/.github/workflows/pages.yml)
builds this book and the hosted dashboard ([Editing this book](docs.md)).
[`release.yml`](https://github.com/pmixay/ReSense/blob/main/.github/workflows/release.yml) publishes
the image archive as a GitHub release when a `v1.0.0-rcN` / `v1.0.0` tag is pushed; no tag has been
pushed so far.

## Rules of the repository

* `main` changes only through a pull request with CI green; the captain merges.
* One parameter source (`configs/default.yaml`); numbers live only in `docs/EXPERIMENTS.md` and the
  README summary; other documents link to them.
* The status JSON and the topics are contracts: keys and topics are added, never renamed or
  removed.
* Who owns which files: [`docs/CAPTAIN.md` §8](https://github.com/pmixay/ReSense/blob/main/docs/CAPTAIN.md#8-ownership-map-a-file-not-listed-its-authors-lane-ask-p1).
