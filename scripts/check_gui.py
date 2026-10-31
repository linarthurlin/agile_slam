#!/usr/bin/env python3
"""Require both live GUI containers and their nontrivial X11 client windows."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
NAMES=('0025-gazebo','0025-rviz')


def windows_present(tree):
    patterns={'gazebo':r'"Gazebo":.*? (\d+)x(\d+)\+',
              'rviz':r'"[^"\n]* - RViz":.*? (\d+)x(\d+)\+'}
    return {name:any(int(w)>=640 and int(h)>=400 for w,h in re.findall(pattern,tree)) for name,pattern in patterns.items()}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    deadline=time.monotonic()+20
    report={'passed':False}
    while time.monotonic()<deadline:
        state=subprocess.run(['docker','inspect',*NAMES],capture_output=True,text=True,timeout=10)
        containers=json.loads(state.stdout) if state.returncode==0 else []
        live=len(containers)==2 and all(c['State']['Running'] and not c['State']['Restarting'] for c in containers)
        result=subprocess.run(['docker','exec',NAMES[0],'xwininfo','-root','-tree'],capture_output=True,text=True,timeout=10)
        windows=windows_present(result.stdout)
        report={'passed':live and result.returncode==0 and all(windows.values()),'containers_running':live,'windows':windows,'scope':'X11 client existence and container liveness; visual content requires separate inspection.'}
        if report['passed']:break
        time.sleep(.5)
    data=json.dumps(report,indent=2)+'\n'
    if args.output:args.output.write_text(data,encoding='utf-8')
    print(data,end='')
    return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
