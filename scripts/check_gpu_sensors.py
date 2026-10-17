#!/usr/bin/env python3
"""Run camera-only, LiDAR-only and combined GPU tests in one canonical project."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def main():
    if os.name=='nt':
        distro=os.environ.get('AGILE_WSL_DISTRO','Ubuntu-22.04')
        path=subprocess.check_output(['wsl','-d',distro,'--','wslpath','-a',Path(__file__).resolve().as_posix()],text=True).strip()
        return subprocess.call(['wsl','-d',distro,'--','python3',path])
    subprocess.run([sys.executable,str(ROOT/'scripts/check_renderer.py'),'--rendering','gpu'],check=True)
    folder=ROOT/'artifacts/gpu_primitives'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder.mkdir(parents=True)
    source=(ROOT/'ros2_ws/src/gem_description/urdf/gem.urdf.xacro').read_text()
    base=['docker','compose','-f',str(ROOT/'compose.yaml'),'-f',str(ROOT/'deploy/desktop-gpu.yaml')]
    manifest={'image_id':subprocess.check_output(['docker','image','inspect','agile_slam:humble','--format','{{.Id}}'],text=True).strip(),'results':[],'passed':False}
    environment=os.environ.copy()
    environment.update(AGILE_SPAWN_X='0',AGILE_SPAWN_Y='0',AGILE_SPAWN_YAW='0')
    try:
        for sensor in ('camera','lidar','both'):
            model=source
            if sensor=='camera':model,count=re.subn(r'<sensor\s+name="velodyne_lidar".*?</sensor>','',model,flags=re.S);assert count==1
            if sensor=='lidar':model,count=re.subn(r'<sensor type="camera" name="front_camera">.*?</sensor>','',model,flags=re.S);assert count==1
            path=folder/(sensor+'.xacro');path.write_text(model)
            override={'services':{'core':{'volumes':[str(path)+':/opt/agile_slam_ws/install/gem_description/share/gem_description/urdf/gem.urdf.xacro:ro']},'backend-sim':{'command':['ros2','launch','avl_bringup','backend_sim.launch.py','world:=/opt/agile_slam_ws/install/gem_gazebo/share/gem_gazebo/worlds/baseline.sdf']}}}
            config=folder/(sensor+'.yaml');config.write_text(json.dumps(override,indent=2))
            compose=base+['-f',str(config)]
            subprocess.run(base+['--profile','gui','down'],check=True,env=environment)
            subprocess.run(compose+['up','-d'],check=True,env=environment)
            result=subprocess.run(compose+['exec','-T','core','/agile_slam_entrypoint.sh','ros2','run','agile_navigation','check_primitive_sensors.py',sensor,'--output-image','/artifacts/'+(folder/(sensor+'.png')).relative_to(ROOT/'artifacts').as_posix()],capture_output=True,text=True,timeout=100)
            (folder/(sensor+'.stdout.log')).write_text(result.stdout)
            (folder/(sensor+'.stderr.log')).write_text(result.stderr)
            report=json.JSONDecoder().raw_decode(result.stdout.lstrip())[0]
            (folder/(sensor+'.json')).write_text(json.dumps(report,indent=2))
            logs=subprocess.run(compose+['logs','--no-color','backend-sim'],capture_output=True,text=True,timeout=15)
            (folder/(sensor+'.runtime.log')).write_text(logs.stdout)
            manifest['results'].append({'sensor':sensor,'passed':bool(report['passed'] and result.returncode==0),'xacro_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'report':report})
            print(sensor,report['passed'],flush=True)
            if not manifest['results'][-1]['passed']:raise RuntimeError('Primitive test failed: '+sensor)
        manifest['passed']=True
    except Exception as exc:
        manifest['error']=str(exc)
    finally:
        subprocess.run(base+['--profile','gui','down'],check=True,env=environment)
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(folder/'manifest.json',flush=True)
    return 0 if manifest['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
