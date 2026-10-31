#!/usr/bin/env python3
"""Load, configure, and activate the simulated vehicle controllers."""
import argparse
import sys
import time

import rclpy
from controller_manager_msgs.srv import ConfigureController, ListControllers, LoadController, SwitchController
from rclpy.node import Node
from rclpy.utilities import remove_ros_args


CONTROLLERS = (
    'joint_state_broadcaster',
    'left_steering_controller',
    'right_steering_controller',
    'left_front_wheel_controller',
    'right_front_wheel_controller',
    'left_rear_wheel_controller',
    'right_rear_wheel_controller',
)


def call(node, client, request, service_name, timeout):
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
    if not future.done():
        raise RuntimeError(f'{service_name} did not respond within {timeout:g} seconds.')
    exception = future.exception()
    if exception is not None:
        raise RuntimeError(f'{service_name} failed: {exception}')
    response = future.result()
    if response is None:
        raise RuntimeError(f'{service_name} returned no response.')
    return response


def wait_for_service(node, client, service_name, timeout):
    deadline = time.monotonic() + timeout
    while rclpy.ok() and time.monotonic() < deadline:
        if client.wait_for_service(timeout_sec=0.5):
            return
        rclpy.spin_once(node, timeout_sec=0.05)
    raise RuntimeError(f'{service_name} did not become available within {timeout:g} seconds.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--controller-manager', default='/controller_manager')
    parser.add_argument('--controller-manager-timeout', type=float, default=180.0)
    parser.add_argument('--service-call-timeout', type=float, default=180.0)
    parser.add_argument('--switch-timeout', type=float, default=120.0)
    args = parser.parse_args(remove_ros_args(args=sys.argv)[1:])

    rclpy.init()
    node = Node('sim_controller_startup')
    root = args.controller_manager.rstrip('/')
    list_name = f'{root}/list_controllers'
    load_name = f'{root}/load_controller'
    configure_name = f'{root}/configure_controller'
    switch_name = f'{root}/switch_controller'
    list_client = node.create_client(ListControllers, list_name)
    load_client = node.create_client(LoadController, load_name)
    configure_client = node.create_client(ConfigureController, configure_name)
    switch_client = node.create_client(SwitchController, switch_name)
    try:
        for client, name in (
            (list_client, list_name),
            (load_client, load_name),
            (configure_client, configure_name),
            (switch_client, switch_name),
        ):
            wait_for_service(node, client, name, args.controller_manager_timeout)

        def states():
            response = call(
                node, list_client, ListControllers.Request(), list_name,
                args.service_call_timeout,
            )
            return {controller.name: controller.state for controller in response.controller}

        for name in CONTROLLERS:
            current = states().get(name)
            if current is None:
                request = LoadController.Request()
                request.name = name
                response = call(node, load_client, request, load_name, args.service_call_timeout)
                if not response.ok:
                    raise RuntimeError(f'Controller manager rejected loading {name}.')
                node.get_logger().info(f'Loaded {name}.')
                current = states().get(name)

            if current == 'unconfigured':
                request = ConfigureController.Request()
                request.name = name
                response = call(
                    node, configure_client, request, configure_name,
                    args.service_call_timeout,
                )
                if not response.ok:
                    raise RuntimeError(f'Controller manager rejected configuring {name}.')
                current = states().get(name)
                node.get_logger().info(f'Configured {name}.')

            if current != 'active':
                request = SwitchController.Request()
                request.activate_controllers = [name]
                request.deactivate_controllers = []
                request.strictness = SwitchController.Request.STRICT
                request.activate_asap = True
                request.timeout.sec = int(args.switch_timeout)
                request.timeout.nanosec = int((args.switch_timeout % 1.0) * 1_000_000_000)
                response = call(node, switch_client, request, switch_name, args.service_call_timeout)
                if not response.ok:
                    raise RuntimeError(f'Controller manager rejected activating {name}.')
                node.get_logger().info(f'Activated {name}.')

            final_state = states().get(name)
            if final_state != 'active':
                raise RuntimeError(f'{name} ended in state {final_state!r}, expected active.')

        node.get_logger().info('All simulated vehicle controllers are active.')
        return 0
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
