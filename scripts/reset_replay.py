#!/usr/bin/env python3
"""Atomically select an explicit sensor profile, then reset between stopped bag players."""

import argparse
import time

import rclpy
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParametersAtomically
from std_srvs.srv import Trigger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("manual", "pandar128", "falcon_ros", "falcon_native"),
        default="manual",
    )
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    rclpy.init()
    node = rclpy.create_node("resense_replay_boundary")
    deadline = time.monotonic() + args.timeout

    def remaining():
        return max(0.0, deadline - time.monotonic())

    def result(future):
        rclpy.spin_until_future_complete(node, future, timeout_sec=remaining())
        if not future.done() or future.exception():
            raise RuntimeError("replay boundary request timed out or failed")
        return future.result()

    try:
        parameters = node.create_client(
            SetParametersAtomically, "/resense_detector/set_parameters_atomically"
        )
        if not parameters.wait_for_service(timeout_sec=remaining()):
            raise RuntimeError("detector parameter service unavailable")
        response = result(
            parameters.call_async(
                SetParametersAtomically.Request(
                    parameters=[
                        Parameter(
                            "sensor_profile", value=args.profile
                        ).to_parameter_msg()
                    ]
                )
            )
        )
        if not response.result.successful:
            raise RuntimeError(response.result.reason)
        reset = node.create_client(Trigger, "/resense/reset_input")
        if not reset.wait_for_service(timeout_sec=remaining()):
            raise RuntimeError("detector reset service unavailable")
        response = result(reset.call_async(Trigger.Request()))
        if not response.success:
            raise RuntimeError(response.message)
        print(
            f"recording boundary confirmed; sensor_profile={args.profile}", flush=True
        )
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
