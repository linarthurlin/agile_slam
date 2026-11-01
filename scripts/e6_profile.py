"""Load, validate, and render the GEM e6 sensor-frame profile."""
from dataclasses import dataclass
import csv
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INVENTORY = ROOT / "config/e6/sensor_inventory.csv"
DEFAULT_CALIBRATION = ROOT / "config/e6/sensors_calibration.yaml"
DEFAULT_DRIVER_MATRIX = ROOT / "config/e6/driver_matrix.yaml"

FRAME_PARENTS = {
    "base_link": None,
    "livox_mount_link": "base_link",
    "livox_fl_link": "livox_mount_link",
    "livox_fc_link": "livox_mount_link",
    "livox_fr_link": "livox_mount_link",
    "top_sensor_rig_link": "base_link",
    "avt_cam_fl_link": "top_sensor_rig_link",
    "avt_cam_fl_optical_frame": "avt_cam_fl_link",
    "avt_cam_fr_link": "top_sensor_rig_link",
    "avt_cam_fr_optical_frame": "avt_cam_fr_link",
    "avt_cam_cl_link": "top_sensor_rig_link",
    "avt_cam_cl_optical_frame": "avt_cam_cl_link",
    "avt_cam_cr_link": "top_sensor_rig_link",
    "avt_cam_cr_optical_frame": "avt_cam_cr_link",
    "avt_cam_rl_link": "top_sensor_rig_link",
    "avt_cam_rl_optical_frame": "avt_cam_rl_link",
    "avt_cam_rr_link": "top_sensor_rig_link",
    "avt_cam_rr_optical_frame": "avt_cam_rr_link",
    "velodyne_link": "top_sensor_rig_link",
    "gnss_main_link": "top_sensor_rig_link",
    "gnss_slave_link": "top_sensor_rig_link",
    "realsense_link": "base_link",
    "realsense_wrapper_children": "realsense_link",
}

INVENTORY_CONTRACT = {
    "livox_fl": ("livox_fl_link", "livox_fl_link", "livox_mount_link"),
    "livox_fc": ("livox_fc_link", "livox_fc_link", "livox_mount_link"),
    "livox_fr": ("livox_fr_link", "livox_fr_link", "livox_mount_link"),
    "velodyne_vlp16": ("velodyne_link", "velodyne_link", "top_sensor_rig_link"),
    "avt_cam_fl": ("avt_cam_fl_link", "avt_cam_fl_optical_frame", "top_sensor_rig_link"),
    "avt_cam_fr": ("avt_cam_fr_link", "avt_cam_fr_optical_frame", "top_sensor_rig_link"),
    "avt_cam_cl": ("avt_cam_cl_link", "avt_cam_cl_optical_frame", "top_sensor_rig_link"),
    "avt_cam_cr": ("avt_cam_cr_link", "avt_cam_cr_optical_frame", "top_sensor_rig_link"),
    "avt_cam_rl": ("avt_cam_rl_link", "avt_cam_rl_optical_frame", "top_sensor_rig_link"),
    "avt_cam_rr": ("avt_cam_rr_link", "avt_cam_rr_optical_frame", "top_sensor_rig_link"),
    "realsense": ("realsense_link", None, "base_link"),
    "gnss_receiver": ("none", "gnss_main_link", "none"),
    "gnss_main": ("gnss_main_link", "gnss_main_link", "top_sensor_rig_link"),
    "gnss_slave": ("gnss_slave_link", "gnss_slave_link", "top_sensor_rig_link"),
}

TOPIC_CONTRACT = {
    "livox_fl": {"/sensors/lidars/livox_fl/points"},
    "livox_fc": {"/sensors/lidars/livox_fc/points"},
    "livox_fr": {"/sensors/lidars/livox_fr/points"},
    "velodyne_vlp16": {
        "/sensors/lidars/velodyne_vlp16/points",
        "/sensors/lidars/velodyne_vlp16/packets",
    },
    "avt_cam_fl": {"/sensors/cameras/avt_cam_fl/image_raw", "/sensors/cameras/avt_cam_fl/camera_info"},
    "avt_cam_fr": {"/sensors/cameras/avt_cam_fr/image_raw", "/sensors/cameras/avt_cam_fr/camera_info"},
    "avt_cam_cl": {"/sensors/cameras/avt_cam_cl/image_raw", "/sensors/cameras/avt_cam_cl/camera_info"},
    "avt_cam_cr": {"/sensors/cameras/avt_cam_cr/image_raw", "/sensors/cameras/avt_cam_cr/camera_info"},
    "avt_cam_rl": {"/sensors/cameras/avt_cam_rl/image_raw", "/sensors/cameras/avt_cam_rl/camera_info"},
    "avt_cam_rr": {"/sensors/cameras/avt_cam_rr/image_raw", "/sensors/cameras/avt_cam_rr/camera_info"},
    "realsense": {
        "/sensors/realsense/color/image_raw",
        "/sensors/realsense/color/camera_info",
        "/sensors/realsense/depth/image_rect_raw",
        "/sensors/realsense/depth/camera_info",
        "/sensors/realsense/gyro/sample",
        "/sensors/realsense/accel/sample",
        "/sensors/realsense/imu",
    },
    "gnss_receiver": {
        "/sensors/gnss/rtk/fix",
        "/sensors/gnss/rtk/heading",
        "/sensors/gnss/rtk/status",
    },
    "gnss_main": set(),
    "gnss_slave": set(),
}

OPTICAL_RPY = [-math.pi / 2.0, 0.0, -math.pi / 2.0]
PSEUDO_FRAMES = {"realsense_wrapper_children"}
CONVENTION_FRAMES = {
    "avt_cam_fl_optical_frame",
    "avt_cam_fr_optical_frame",
    "avt_cam_cl_optical_frame",
    "avt_cam_cr_optical_frame",
    "avt_cam_rl_optical_frame",
    "avt_cam_rr_optical_frame",
}


@dataclass
class ProfileReport:
    contract_errors: list
    calibration_issues: list
    integration_issues: list

    @property
    def structurally_valid(self):
        return not self.contract_errors

    @property
    def calibration_ready(self):
        return self.structurally_valid and not self.calibration_issues

    @property
    def integration_ready(self):
        return self.calibration_ready and not self.integration_issues


def load_profile(inventory_path=DEFAULT_INVENTORY, calibration_path=DEFAULT_CALIBRATION,
                 driver_matrix_path=DEFAULT_DRIVER_MATRIX):
    with Path(inventory_path).open(newline="", encoding="utf-8-sig") as stream:
        inventory = list(csv.DictReader(stream))
    with Path(calibration_path).open(encoding="utf-8") as stream:
        calibration = yaml.safe_load(stream)
    with Path(driver_matrix_path).open(encoding="utf-8") as stream:
        driver_matrix = yaml.safe_load(stream)
    return inventory, calibration, driver_matrix


def _finite_vector(value, length=3):
    return (
        isinstance(value, list)
        and len(value) == length
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) and math.isfinite(item)
                for item in value)
    )


def _placeholder(value):
    return not value or value.strip().lower() in {"tbd", "none", "null", "unknown"} or value.strip().lower().startswith("tbd ")


def _parse_frame_map(value):
    mapping = {}
    for item in value.split(";"):
        if not item.strip():
            continue
        if "=" not in item:
            return {}
        topic, frame = (part.strip() for part in item.split("=", 1))
        if not topic or not frame or topic in mapping:
            return {}
        mapping[topic] = frame
    return mapping


def inspect_profile(inventory, calibration, driver_matrix):
    errors = []
    calibration_issues = []
    integration_issues = []

    if not isinstance(calibration, dict) or calibration.get("profile") != "gem_e6_hardware":
        return ProfileReport(["Calibration registry must describe profile gem_e6_hardware."], [], [])
    if not isinstance(driver_matrix, dict) or driver_matrix.get("profile") != "gem_e6_hardware":
        return ProfileReport(["Driver matrix must describe profile gem_e6_hardware."], [], [])

    frames = calibration.get("frames")
    if not isinstance(frames, dict):
        return ProfileReport(["Calibration registry is missing the frames mapping."], [], [])
    if set(frames) != set(FRAME_PARENTS):
        missing = sorted(set(FRAME_PARENTS) - set(frames))
        extra = sorted(set(frames) - set(FRAME_PARENTS))
        if missing:
            errors.append("Missing frame entries: " + ", ".join(missing))
        if extra:
            errors.append("Unexpected frame entries: " + ", ".join(extra))

    for frame_name, expected_parent in FRAME_PARENTS.items():
        entry = frames.get(frame_name)
        if not isinstance(entry, dict):
            errors.append(f"Frame {frame_name} must have a mapping entry.")
            continue
        if entry.get("parent") != expected_parent:
            errors.append(f"Frame {frame_name} must have parent {expected_parent!r}; got {entry.get('parent')!r}.")
    if "imu_link" in frames or "avt_camera_rig_link" in frames:
        errors.append("Legacy standalone imu_link/avt_camera_rig_link must not appear in the e6 contract.")

    rows_by_id = {}
    for row in inventory:
        sensor_id = row.get("sensor_id", "").strip()
        if not sensor_id:
            errors.append("Inventory row has an empty sensor_id.")
        elif sensor_id in rows_by_id:
            errors.append(f"Duplicate inventory sensor_id: {sensor_id}.")
        else:
            rows_by_id[sensor_id] = row
    if set(rows_by_id) != set(INVENTORY_CONTRACT):
        missing = sorted(set(INVENTORY_CONTRACT) - set(rows_by_id))
        extra = sorted(set(rows_by_id) - set(INVENTORY_CONTRACT))
        if missing:
            errors.append("Missing inventory IDs: " + ", ".join(missing))
        if extra:
            errors.append("Unexpected inventory IDs: " + ", ".join(extra))

    for sensor_id, (sensor_link, message_frame, parent_frame) in INVENTORY_CONTRACT.items():
        row = rows_by_id.get(sensor_id)
        if row is None:
            continue
        expected_values = {
            "sensor_link": sensor_link,
            "tf_parent_frame": parent_frame,
        }
        if message_frame is not None:
            expected_values["message_frame_id"] = message_frame
        for field, expected in expected_values.items():
            if row.get(field, "").strip() != expected:
                errors.append(f"Inventory {sensor_id} field {field} must be {expected!r}.")
        topics = {topic.strip() for topic in row.get("topics", "").split(";") if topic.strip()}
        if not TOPIC_CONTRACT[sensor_id].issubset(topics):
            missing_topics = sorted(TOPIC_CONTRACT[sensor_id] - topics)
            errors.append(f"Inventory {sensor_id} is missing canonical topics: {', '.join(missing_topics)}.")
        if sensor_id == "realsense":
            message_map_text = row.get("message_frame_id", "").strip()
            if not _placeholder(message_map_text):
                frame_map = _parse_frame_map(message_map_text)
                if set(frame_map) != TOPIC_CONTRACT["realsense"]:
                    errors.append("RealSense message_frame_id must map every canonical stream topic to its wrapper frame.")
                wrapper_entry = frames.get("realsense_wrapper_children", {})
                known_wrapper_frames = wrapper_entry.get("frame_ids")
                if isinstance(known_wrapper_frames, list) and not set(frame_map.values()).issubset(set(known_wrapper_frames)):
                    errors.append("RealSense topic frame mapping references a frame absent from wrapper frame_ids.")
        if sensor_link not in {"none", ""} and sensor_link in frames:
            expected_calibration_id = frames[sensor_link].get("calibration_id")
            if row.get("calibration_id") != expected_calibration_id:
                errors.append(f"Inventory {sensor_id} calibration_id does not match frame {sensor_link}.")

    # Ensure every physical frame reaches base_link and that the declared tree has no cycle.
    for frame_name in FRAME_PARENTS:
        if frame_name == "base_link":
            continue
        visited = set()
        current = frame_name
        while current != "base_link":
            if current in visited:
                errors.append(f"Cycle detected in frame chain at {current}.")
                break
            visited.add(current)
            entry = frames.get(current)
            if not isinstance(entry, dict):
                break
            current = entry.get("parent")
            if current not in frames:
                errors.append(f"Frame chain for {frame_name} terminates at unknown parent {current!r}.")
                break

    # Fixed REP-103 camera optical rotations and the AVT common-height constraint are contract invariants.
    for frame_name in CONVENTION_FRAMES:
        entry = frames.get(frame_name, {})
        if entry.get("translation_m") != [0.0, 0.0, 0.0]:
            errors.append(f"{frame_name} must have zero translation from its camera body frame.")
        if entry.get("rotation_rpy_rad") != OPTICAL_RPY:
            errors.append(f"{frame_name} must use the REP-103 camera optical rotation.")
    for frame_name in [name for name in FRAME_PARENTS if name.startswith("avt_cam_") and name.endswith("_link")]:
        translation = frames.get(frame_name, {}).get("translation_m")
        if not isinstance(translation, list) or len(translation) != 3 or translation[2] != 0.0:
            errors.append(f"{frame_name} must keep z=0 relative to top_sensor_rig_link.")

    if errors:
        return ProfileReport(errors, [], [])

    if calibration.get("status") != "validated":
        calibration_issues.append("Calibration registry status is not validated.")
    base_status = frames["base_link"].get("geometry_status")
    if base_status != "validated":
        calibration_issues.append("base_link vehicle datum has not been validated.")

    slave_row = rows_by_id["gnss_slave"]
    slave_not_installed = slave_row.get("hardware_status") == "not_installed"
    for frame_name, entry in frames.items():
        if frame_name == "base_link":
            continue
        if frame_name in PSEUDO_FRAMES:
            if entry.get("status") != "validated":
                calibration_issues.append("RealSense wrapper child frame IDs have not been discovered and recorded.")
            elif not isinstance(entry.get("frame_ids"), list) or not entry["frame_ids"]:
                calibration_issues.append("RealSense wrapper frame_ids must be a non-empty list after discovery.")
            continue
        if frame_name == "gnss_slave_link" and slave_not_installed:
            if entry.get("status") != "not_installed":
                calibration_issues.append("Uninstalled GNSS slave must be marked not_installed in the calibration registry.")
            continue
        expected_status = "defined_by_convention" if frame_name in CONVENTION_FRAMES else "validated"
        if entry.get("status") != expected_status:
            calibration_issues.append(f"Frame {frame_name} status must be {expected_status}.")
        if not _finite_vector(entry.get("translation_m")):
            calibration_issues.append(f"Frame {frame_name} needs three finite translation_m values.")
        if not _finite_vector(entry.get("rotation_rpy_rad")):
            calibration_issues.append(f"Frame {frame_name} needs three finite rotation_rpy_rad values.")

    for sensor_id, row in rows_by_id.items():
        is_optional_slave = sensor_id == "gnss_slave"
        if is_optional_slave and row.get("hardware_status") == "not_installed":
            continue
        if row.get("hardware_status") != "validated":
            calibration_issues.append(f"Inventory {sensor_id} hardware identity is not validated.")
        for field in ("manufacturer", "model", "firmware", "network_or_port"):
            if _placeholder(row.get(field, "")):
                calibration_issues.append(f"Inventory {sensor_id} {field} is missing.")
        if _placeholder(row.get("serial", "")):
            calibration_issues.append(f"Inventory {sensor_id} serial is missing (use N/A only if that hardware has no serial).")
        if row.get("serial", "").strip().lower() == "n/a":
            # N/A is valid when the physical device genuinely has no serial; retain an explicit inventory status.
            if row.get("hardware_status") != "validated":
                calibration_issues.append(f"Inventory {sensor_id} must justify N/A serial before validation.")
        if row.get("extrinsic_status") not in {"validated", "not_applicable"}:
            calibration_issues.append(f"Inventory {sensor_id} extrinsic status is not validated.")
        if sensor_id == "realsense":
            frame_map = _parse_frame_map(row.get("message_frame_id", ""))
            if set(frame_map) != TOPIC_CONTRACT["realsense"]:
                calibration_issues.append("RealSense per-topic message frame IDs must be discovered from the selected wrapper.")

    livox_points = [frames[name]["translation_m"] for name in ("livox_fl_link", "livox_fc_link", "livox_fr_link")]
    if all(_finite_vector(value) for value in livox_points):
        if not all(math.isclose(livox_points[0][axis], point[axis], abs_tol=1e-9) for point in livox_points[1:] for axis in (0, 2)):
            calibration_issues.append("Livox Horizon mounts must share x and z relative to livox_mount_link.")
    camera_z = [frames[name]["translation_m"][2] for name in FRAME_PARENTS if name.startswith("avt_cam_") and name.endswith("_link")]
    if any(not math.isclose(z, 0.0, abs_tol=1e-12) for z in camera_z):
        calibration_issues.append("All AVT camera mount z values must remain zero relative to top_sensor_rig_link.")

    driver_entries = driver_matrix.get("drivers", [])
    if not isinstance(driver_entries, list):
        driver_entries = []
        integration_issues.append("Driver matrix drivers must be a list of sensor-family entries.")
    expected_families = {"livox_horizon", "velodyne_vlp16", "avt_area_scan", "realsense", "rtk_gnss"}
    found_families = {entry.get("sensor_family") for entry in driver_entries if isinstance(entry, dict)}
    if found_families != expected_families:
        integration_issues.append("Driver matrix sensor_family entries do not match the e6 sensor profile.")
    if driver_matrix.get("status") != "validated":
        integration_issues.append("Driver matrix Humble compatibility spikes are pending.")
    for entry in driver_entries:
        if not isinstance(entry, dict):
            integration_issues.append("Driver matrix contains a non-mapping driver entry.")
            continue
        family = entry.get("sensor_family", "unknown")
        if entry.get("status") != "validated" or _placeholder(str(entry.get("version_or_commit") or "")):
            integration_issues.append(f"Driver compatibility/version is pending for {family}.")
    clocks = driver_matrix.get("clock_sources", {})
    if not isinstance(clocks, dict):
        clocks = {}
        integration_issues.append("Driver matrix clock_sources must be a mapping.")
    for name, entry in clocks.items():
        if not isinstance(entry, dict) or entry.get("status") != "validated":
            integration_issues.append(f"Clock source validation is pending for {name}.")
    bandwidth = driver_matrix.get("bandwidth", {})
    if not isinstance(bandwidth, dict):
        bandwidth = {}
        integration_issues.append("Driver matrix bandwidth must be a mapping.")
    for name, entry in bandwidth.items():
        if not isinstance(entry, dict) or entry.get("status") != "validated":
            integration_issues.append(f"Bandwidth validation is pending for {name}.")
    for row in inventory:
        if row.get("hardware_status") == "not_installed":
            continue
        if row.get("driver_status") not in {"validated", "not_applicable"}:
            integration_issues.append(f"Inventory {row.get('sensor_id', 'unknown')} driver status is pending.")

    return ProfileReport([], calibration_issues, integration_issues)


def _fmt_vector(values):
    return " ".join(format(float(value), ".15g") for value in values)


def render_sensor_xacro(inventory, calibration, driver_matrix):
    report = inspect_profile(inventory, calibration, driver_matrix)
    if report.contract_errors:
        raise ValueError("Sensor-frame contract is invalid: " + " ".join(report.contract_errors))
    if report.calibration_issues:
        raise ValueError("Refusing to generate uncalibrated sensor frames: " + " ".join(report.calibration_issues))
    if report.integration_issues:
        raise ValueError("Refusing to generate hardware sensor frames before driver/clock/bandwidth gates pass: " + " ".join(report.integration_issues))

    frames = calibration["frames"]
    slave_not_installed = next(row for row in inventory if row["sensor_id"] == "gnss_slave")["hardware_status"] == "not_installed"
    omitted = {"base_link", "realsense_wrapper_children"}
    if slave_not_installed:
        omitted.add("gnss_slave_link")

    robot = ET.Element("robot", {"name": "gem_e6_sensor_frames"})
    robot.append(ET.Comment("Generated from config/e6/sensors_calibration.yaml. Do not edit by hand."))
    remaining = [name for name in frames if name not in omitted]
    emitted = {"base_link"}
    while remaining:
        ready = [name for name in remaining if frames[name].get("parent") in emitted]
        if not ready:
            raise ValueError("Cannot order sensor frames: parent graph is disconnected or cyclic.")
        for name in ready:
            entry = frames[name]
            link = ET.SubElement(robot, "link", {"name": name})
            joint = ET.SubElement(robot, "joint", {"name": f"{name}_fixed_joint", "type": "fixed"})
            ET.SubElement(joint, "parent", {"link": entry["parent"]})
            ET.SubElement(joint, "child", {"link": name})
            ET.SubElement(joint, "origin", {
                "xyz": _fmt_vector(entry["translation_m"]),
                "rpy": _fmt_vector(entry["rotation_rpy_rad"]),
            })
            emitted.add(name)
            remaining.remove(name)
    ET.indent(robot, space="  ")
    return ET.tostring(robot, encoding="unicode", xml_declaration=True) + "\n"
