#!/usr/bin/env python3
"""Operate the isolated Humble runtime; unimplemented hardware modes fail closed."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
COMPOSE=['docker','compose','-f',str(ROOT/'compose.yaml')]

def wsl_gui_command(distro,path):
    pose=[f'{key}={os.environ.get(key,"0")}' for key in ('AGILE_SPAWN_X','AGILE_SPAWN_Y','AGILE_SPAWN_YAW')]
    return ['wsl','-d',distro,'--','env',*pose,'python3',path,'up','--gui']


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=('build','up','down','status','check','test','enable','disable'))
    parser.add_argument('--mode',choices=('sim','vehicle','vehicle-readonly','replay'),default='sim')
    parser.add_argument('--gui',action='store_true')
    args=parser.parse_args()
    if args.mode!='sim':parser.error('Only simulation is implemented; hardware and replay deployment are unavailable.')
    if args.gui and args.action!='up':parser.error('--gui is supported with up only.')
    if args.gui and os.name=='nt':
        distro=os.environ.get('AGILE_WSL_DISTRO','Ubuntu-22.04')
        path=subprocess.check_output(['wsl','-d',distro,'--','wslpath','-a',Path(__file__).resolve().as_posix()],text=True).strip()
        return subprocess.call(wsl_gui_command(distro,path))
    if args.action in ('build','up') and not (ROOT/'assets/small_city/worlds/small_city.sdf').is_file():
        parser.error('Prepare small_city assets before building/starting this profile.')
    if args.action in ('build','up'):
        from validate_contracts import validate
        validate()
    command=COMPOSE[:]
    if args.action=='build':command+=['build','core']
    elif args.action=='up':
        if args.gui:
            if not Path('/mnt/wslg/.X11-unix/X0').is_socket():parser.error('WSLg is unavailable.')
            command+=['--profile','gui']
        command+=['up','-d']
    elif args.action=='down':command+=['--profile','gui','down']
    elif args.action=='status':command+=['--profile','gui','ps','-a']
    else:
        command+=['exec','-T','vehicle-control','/agile_slam_entrypoint.sh','ros2','run','agile_vehicle']
        if args.action=='test':command+=['check_pacmod_runtime.py']
        else:command+=['runtime_probe.py','ready' if args.action=='check' else args.action]
    return subprocess.call(command,cwd=ROOT)

if __name__=='__main__':raise SystemExit(main())
