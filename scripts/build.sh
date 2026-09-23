#!/usr/bin/env bash
# Build the Docker image.
#   ./scripts/build.sh              # runtime image (node + RViz + Foxglove bridge)
#   WITH_TOOLS=1 ./scripts/build.sh # + offline tools (rosbags, matplotlib, open3d) and pytest
#   PULL=1 ./scripts/build.sh       # refresh the ros:humble base image first: an old cached base
#                                   # (from before the 2025 ROS apt key rotation) fails apt-get update
set -euo pipefail
cd "$(dirname "$0")/.."
args=(-t resense:latest --build-arg "WITH_TOOLS=${WITH_TOOLS:-0}" -f docker/Dockerfile)
if [ "${PULL:-0}" = "1" ]; then
  args+=(--pull)
fi
docker build "${args[@]}" .
