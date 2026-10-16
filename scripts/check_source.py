#!/usr/bin/env python3
"""Validate parseable source/configuration without a ROS installation."""
import ast
import json
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for path in (root / 'ros2_ws/src').rglob('*'):
    if path.suffix == '.py':
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    elif path.suffix in ('.xml', '.xacro', '.gazebo', '.sdf'):
        ET.parse(path)
for path in (root / 'scripts').glob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
for path in (root / 'config').rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8-sig'))
json.loads((root / 'third_party/source_manifest.json').read_text(encoding='utf-8'))
for path in list((root / 'ros2_ws/src').rglob('*.py')) + list((root / 'scripts').rglob('*.sh')) + list((root / 'containers').rglob('*.sh')):
    if b'\r\n' in path.read_bytes():
        raise SystemExit(f'Linux executable has CRLF line endings: {path.relative_to(root)}')
from validate_contracts import validate
validate()
print('Source and configuration checks passed.')
