#!/usr/bin/env python3
"""Operate the simulation profile; hardware and replay deployments fail closed."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    'docker', 'compose',
    '-f', str(ROOT / 'compose.yaml'),
    '-f', str(ROOT / 'compose.sim.yaml'),
    '--profile', 'sim',
]


def wsl_up_command(distro, path, gui=False, rendering='software'):
    pose = [f'{key}={os.environ.get(key, "0")}' for key in (
        'AGILE_SPAWN_X', 'AGILE_SPAWN_Y', 'AGILE_SPAWN_YAW'
    )]
    command = ['wsl', '-d', distro, '--', 'env', *pose, 'python3', path, 'up']
    if gui:
        command.append('--gui')
    if rendering == 'gpu':
        command += ['--rendering', 'gpu']
    return command


def wsl_gui_command(distro, path):
    return wsl_up_command(distro, path, gui=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'action',
        choices=('build', 'up', 'down', 'status', 'check', 'test', 'enable', 'disable'),
    )
    parser.add_argument(
        '--mode',
        choices=('sim', 'vehicle', 'vehicle-readonly', 'replay'),
        default='sim',
    )
    parser.add_argument('--gui', action='store_true', help='Open Gazebo in the Gazebo container and start RViz.')
    parser.add_argument('--rendering', choices=('software', 'gpu'), default='software')
    args = parser.parse_args()

    if args.mode != 'sim':
        parser.error('Only simulation is implemented; vehicle and replay modes are unavailable.')
    if args.gui and args.action != 'up':
        parser.error('--gui is supported with up only.')

    if args.action == 'up' and os.name == 'nt' and (args.gui or args.rendering == 'gpu'):
        distro = os.environ.get('AGILE_WSL_DISTRO', 'Ubuntu-22.04')
        path = subprocess.check_output(
            ['wsl', '-d', distro, '--', 'wslpath', '-a', Path(__file__).resolve().as_posix()],
            text=True,
        ).strip()
        return subprocess.call(wsl_up_command(distro, path, args.gui, args.rendering))

    if args.action in ('build', 'up') and not (ROOT / 'assets/small_city/worlds/small_city.sdf').is_file():
        parser.error('Prepare small_city assets before building or starting this profile.')
    if args.action in ('build', 'up'):
        from validate_contracts import validate
        validate()

    command = COMPOSE[:]
    if args.action == 'build':
        subprocess.run([sys.executable, str(ROOT / 'scripts/prepare_base.py')], check=True)
        command += ['build', 'autonomy']
    elif args.action == 'up':
        if args.rendering == 'gpu':
            subprocess.run(
                [sys.executable, str(ROOT / 'scripts/check_renderer.py'), '--rendering', 'gpu'],
                check=True,
            )
            command += ['-f', str(ROOT / 'deploy/desktop-gpu.yaml')]
        environment = os.environ.copy()
        environment['AGILE_GAZEBO_GUI'] = '1' if args.gui else '0'
        if args.gui:
            if not Path('/mnt/wslg/.X11-unix/X0').is_socket():
                parser.error('WSLg is unavailable.')
            command += ['-f', str(ROOT / 'deploy/desktop-wslg.yaml'), '--profile', 'visualization']
        subprocess.run(
            COMPOSE + ['--profile', 'visualization', 'down', '--remove-orphans'],
            cwd=ROOT,
            check=True,
        )
        command += ['up', '-d']
        return subprocess.call(command, cwd=ROOT, env=environment)
    elif args.action == 'down':
        command += ['--profile', 'visualization', 'down', '--remove-orphans']
    elif args.action == 'status':
        command += ['--profile', 'visualization', 'ps', '-a']
    else:
        command += [
            'exec', '-T', 'vehicle-control',
            '/agile_slam_entrypoint.sh', 'ros2', 'run', 'agile_vehicle',
        ]
        if args.action == 'test':
            command += ['check_pacmod_runtime.py']
        else:
            command += ['runtime_probe.py', 'ready' if args.action == 'check' else args.action]

    return subprocess.call(command, cwd=ROOT)


if __name__ == '__main__':
    raise SystemExit(main())
