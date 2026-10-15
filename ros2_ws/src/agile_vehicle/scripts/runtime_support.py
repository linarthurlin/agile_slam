"""Shared immutable reference settings and clean ROS node execution."""
import json
from pathlib import Path
from ament_index_python.packages import get_package_share_directory
import rclpy


def config():
    return json.loads((Path(get_package_share_directory('gem_description'))/'config/vehicle.json').read_text())


def run(kind):
    rclpy.init()
    node=kind()
    try:rclpy.spin(node)
    except (KeyboardInterrupt,rclpy.executors.ExternalShutdownException):pass
    finally:
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()
