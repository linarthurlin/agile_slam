#!/usr/bin/env python3
"""Pin the supplied local base image without overwriting an unrelated tag."""
import json
import subprocess

IMAGE_ID = 'sha256:a6acca67607edcb48e66adfec152714ad480b0b0854587c6dcca72034f2084ca'
TAG = 'agile_control_ros2:baseline-20261014'

def main():
    info = json.loads(subprocess.check_output(['docker', 'image', 'inspect', IMAGE_ID]))[0]
    if info['Os'] != 'linux' or info['Architecture'] != 'amd64':
        raise SystemExit('The baseline requires the supplied linux/amd64 image.')
    current = subprocess.run(['docker', 'image', 'inspect', TAG], capture_output=True, text=True)
    if current.returncode == 0 and json.loads(current.stdout)[0]['Id'] != IMAGE_ID:
        raise SystemExit(f'Refusing to replace unrelated tag: {TAG}')
    subprocess.run(['docker', 'tag', IMAGE_ID, TAG], check=True)
    print(f'{TAG} -> {IMAGE_ID}')

if __name__ == '__main__':
    main()
