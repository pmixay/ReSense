#!/usr/bin/env bash
# Build the Docker image.
#   ./scripts/build.sh              # runtime image (node + RViz + Foxglove bridge)
#   WITH_TOOLS=1 ./scripts/build.sh # + offline tools (rosbags, matplotlib, open3d) and pytest
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t resense:latest --build-arg "WITH_TOOLS=${WITH_TOOLS:-0}" -f docker/Dockerfile .
