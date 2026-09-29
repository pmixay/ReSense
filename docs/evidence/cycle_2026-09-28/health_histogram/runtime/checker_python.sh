#!/bin/sh
# Run the host replay wrapper's checker with the declared analysis environment.
exec /usr/bin/docker exec -e PYTHONPATH=/workspace/ReSense-p3-sync -w /workspace/ReSense-p3-sync resense-cycle-dev /usr/bin/python3 "$@"
