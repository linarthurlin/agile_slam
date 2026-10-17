#!/usr/bin/env python3
"""Measure renderer capabilities from the selected image before GPU bringup."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def capabilities(output):
    def field(label):
        match = re.search(r'^'+re.escape(label)+r'\s*(.+)$',output,re.MULTILINE)
        return match.group(1).strip() if match else None
    renderer = field('OpenGL renderer string:')
    return {'renderer':renderer,'core_version':field('OpenGL core profile version string:'),
            'accelerated':bool(re.search(r'Accelerated:\s+yes',output)),
            'arb_copy_image':bool(re.search(r'\bGL_ARB_copy_image\b',output)),
            'nv_copy_image':bool(re.search(r'\bGL_NV_copy_image\b',output))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rendering',choices=('software','gpu'),default='gpu')
    args = parser.parse_args()
    if args.rendering=='gpu' and os.name=='nt':
        distro=os.environ.get('AGILE_WSL_DISTRO','Ubuntu-22.04')
        path=subprocess.check_output(['wsl','-d',distro,'--','wslpath','-a',Path(__file__).resolve().as_posix()],text=True).strip()
        return subprocess.call(['wsl','-d',distro,'--','python3',path,'--rendering','gpu'])
    command=['docker','run','--rm','--network','none']
    if args.rendering=='gpu':
        if not Path('/dev/dxg').exists():parser.error('WSL GPU device is unavailable.')
        command+=['--device','/dev/dxg:/dev/dxg','--mount','type=bind,source=/usr/lib/wsl,target=/usr/lib/wsl,readonly','--mount','type=bind,source=/mnt/wslg/.X11-unix,target=/tmp/.X11-unix,readonly']
        for value in ('DISPLAY=:0','LIBGL_ALWAYS_SOFTWARE=0','GALLIUM_DRIVER=d3d12','MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA','LD_LIBRARY_PATH=/usr/lib/wsl/lib'):
            command+=['-e',value]
        command+=['--entrypoint','glxinfo','agile_slam:humble']
    else:
        command+=['-e','LIBGL_ALWAYS_SOFTWARE=1','-e','LP_NATIVE_VECTOR_WIDTH=128','--entrypoint','xvfb-run','agile_slam:humble','-a','glxinfo']
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    report=capabilities(result.stdout)
    report.update(rendering=args.rendering,exit_code=result.returncode,stderr=result.stderr)
    report['passed']=result.returncode==0 and bool(report['renderer'])
    if args.rendering=='gpu':
        report['passed']=report['passed'] and report['accelerated'] and 'NVIDIA' in (report['renderer'] or '') and (report['arb_copy_image'] or report['nv_copy_image'])
        code="import hashlib,json; from pathlib import Path; p=Path('/usr/lib/x86_64-linux-gnu/OGRE-Next/RenderSystem_GL3Plus.so'); m=json.loads(Path('/opt/agile_slam_metadata/renderer.json').read_text()); assert hashlib.sha256(p.read_bytes()).hexdigest()==m['plugin_sha256']; print(json.dumps(m))"
        metadata=subprocess.run(['docker','run','--rm','--network','none','--entrypoint','python3','agile_slam:humble','-c',code],capture_output=True,text=True,timeout=15)
        report['patched_plugin_verified']=metadata.returncode==0
        report['passed']=report['passed'] and report['patched_plugin_verified']
        if metadata.returncode==0:report['renderer_build']=json.loads(metadata.stdout)
        else:report['metadata_error']=metadata.stderr
    folder=ROOT/'artifacts';folder.mkdir(exist_ok=True)
    (folder/('renderer_capabilities_'+args.rendering+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
