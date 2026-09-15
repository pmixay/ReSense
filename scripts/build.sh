#!/usr/bin/env bash
# Build the Docker image.
set -euo pipefail
cd "$(dirname "$0")/.."
docker build -t resense:latest -f docker/Dockerfile .
