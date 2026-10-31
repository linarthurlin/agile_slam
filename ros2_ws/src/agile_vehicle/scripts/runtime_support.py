"""Shared immutable reference settings and clean ROS node execution."""
import json
import math
import os
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
import rclpy


def config():
    settings = json.loads(
        (Path(get_package_share_directory('gem_description')) / 'config/vehicle.json').read_text()
    )
    sim_timeout = os.environ.get('AGILE_SIM_COMMAND_TIMEOUT')
    if sim_timeout is not None:
        try:
            timeout = float(sim_timeout)
        except ValueError as exc:
            raise ValueError('AGILE_SIM_COMMAND_TIMEOUT must be a positive finite number.') from exc
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('AGILE_SIM_COMMAND_TIMEOUT must be a positive finite number.')
        settings['command_timeout'] = timeout
    return settings


def run(kind):
    rclpy.init()
    node=kind()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
