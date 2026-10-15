#!/usr/bin/env python3
"""Report development prerequisites without changing host configuration."""
import json
import platform
import subprocess
from pathlib import Path

def probe(args):
    try:
        result = subprocess.run(args, capture_output=True, timeout=30)
        encoding = 'utf-16' if b'\x00' in result.stdout else 'utf-8'
        return {'exit_code': result.returncode, 'stdout': result.stdout.decode(encoding, errors='replace').strip(), 'stderr': result.stderr.decode('utf-8', errors='replace').strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'error': str(exc)}

def main():
    report = {'platform': platform.platform(), 'docker_context': probe(['docker', 'context', 'show']), 'docker_version': probe(['docker', 'version', '--format', '{{json .}}']), 'base_image': probe(['docker', 'image', 'inspect', 'agile_control_ros2:baseline-20261014', '--format', '{{.Id}}']), 'wsl': probe(['wsl', '--list', '--verbose'])}
    output = Path(__file__).resolve().parents[1] / 'artifacts'
    output.mkdir(exist_ok=True)
    (output / 'doctor.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return int('error' in report['docker_version'] or report['docker_version'].get('exit_code') != 0)

if __name__ == '__main__':
    raise SystemExit(main())
