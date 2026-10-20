"""The node publishes clear_distance 0.0 when a result is stale: the signature of the transient test_node failure.

Copy next to tests/test_node.py (it imports that module's fixtures) and run
    PYTHONPATH=<checkout> python -m pytest -q -s node_delay_test.py -k delay_signature
Feeds the 40 m box scene for 5 frames, then one frame whose processing takes ``delay`` seconds (max_result_age is 0.5 s).
"""
import sys
import time

import pytest

sys.path.insert(0, "tests")
import test_node as tn
from test_node import box_scene, node_cls


@pytest.mark.parametrize("delay", [0.0, 0.3, 0.7])
def test_delay_signature(node_cls, box_scene, delay):  # noqa: F811 (pytest fixtures)
    frame, _ = box_scene
    node = node_cls()
    tn._feed(node, frame.xyz, 5)
    process = node.detector.process

    def slow(*a, **k):
        r = process(*a, **k)
        time.sleep(delay)
        return r
    node.detector.process = slow
    tn._feed(node, frame.xyz, 1, t0=0.5)
    pub = node.published
    print("DELAY", delay, "decision", pub["/resense/decision"][-1].data, "nearest",
          round(pub["/resense/nearest_distance"][-1].data, 2), "clear", pub["/resense/clear_distance"][-1].data)
