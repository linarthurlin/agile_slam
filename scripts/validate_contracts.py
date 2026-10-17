#!/usr/bin/env python3
"""Reject inconsistent reference geometry before starting the split runtime."""
import json
import math
import os
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]

def validate():
    for key in ('AGILE_SPAWN_X','AGILE_SPAWN_Y','AGILE_SPAWN_YAW'):
        if not math.isfinite(float(os.environ.get(key,'0'))):raise ValueError('Invalid finite spawn coordinate: '+key)
    simulation=json.loads((ROOT/'ros2_ws/src/gem_description/config/simulation.json').read_text())
    if not isinstance(simulation.get('auxiliary_cameras'),bool):raise ValueError('auxiliary_cameras must be a JSON boolean.')
    cfg=json.loads((ROOT/'ros2_ws/src/gem_description/config/vehicle.json').read_text())
    model=ET.parse(ROOT/'ros2_ws/src/gem_description/urdf/gem.urdf.xacro').getroot()
    def xyz(name):return [float(v) for v in model.find(f"joint[@name='{name}']/origin").get('xyz').split()]
    front=xyz('left_steering_hinge_joint');rear=xyz('rear_left_wheel_joint');right=xyz('right_steering_hinge_joint')
    radius=float(model.find("{http://www.ros.org/wiki/xacro}property[@name='tyre_radius']").get('value'))
    actual={'wheelbase':front[0]-rear[0],'track':front[1]-right[1],'wheel_radius':radius,'rear_axle_x':rear[0]}
    for key,value in actual.items():
        if not math.isclose(cfg[key],value,abs_tol=1e-6):raise ValueError(f'Geometry mismatch {key}: config={cfg[key]}, model={value}')
    if not math.isclose(xyz('base_rear_axle_joint')[0],cfg['rear_axle_x'],abs_tol=1e-6):raise ValueError('Rear control frame disagrees with geometry.')
    for key in ('wheelbase','track','wheel_radius','max_speed','max_steer','steering_ratio','steering_rate','command_timeout','report_timeout','backend_timeout','readiness_timeout'):
        if not math.isfinite(cfg[key]) or cfg[key]<=0:raise ValueError(f'Invalid positive vehicle parameter: {key}')
    contract=json.loads((ROOT/'config/interfaces/runtime.json').read_text())
    if contract['sim_private_actuation']!='/simulation/actuation':raise ValueError('Private actuation contract mismatch.')
    return cfg

if __name__=='__main__':
    validate();print('Reference geometry and interface contracts are consistent.')
