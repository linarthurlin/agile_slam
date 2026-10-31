#!/usr/bin/env python3
"""Run isolated simulation scenarios and retain versioned acceptance reports."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import math
from pathlib import Path
import subprocess
import sys
import time
from monitor_gazebo import GazeboMonitor

ROOT=Path(__file__).resolve().parents[1]
COMPOSE=['docker','compose','-f',str(ROOT/'compose.yaml'),'-f',str(ROOT/'compose.sim.yaml'),'--profile','sim']
ENTRY=['/agile_slam_entrypoint.sh']


def execute(command, output=None, timeout=180):
    result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    if output:
        output.with_suffix('.stdout.log').write_text(result.stdout,encoding='utf-8')
        try:report=json.JSONDecoder().raw_decode(result.stdout.lstrip())[0]
        except (ValueError,TypeError):report={'passed':False,'exit_code':result.returncode,'error':'No JSON report; inspect stdout/stderr logs.'}
        output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        output.with_suffix('.stderr.log').write_text(result.stderr,encoding='utf-8')
    if result.returncode:
        raise RuntimeError(f'Command exited {result.returncode}: {command}; {result.stderr[-1500:]}')
    return result.stdout


def deploy(action,output=None,gui=False,rendering='software'):
    command=[sys.executable,str(ROOT/'scripts/deploy.py'),action]
    if gui:command.append('--gui')
    if action=='up':command+=['--rendering',rendering]
    return execute(command,output)


def reset(gui=False,rendering='software',output=None):
    deploy('down');deploy('up',gui=gui,rendering=rendering);deploy('check')
    pose=[os.environ.get(key,'0') for key in ('AGILE_SPAWN_X','AGILE_SPAWN_Y','AGILE_SPAWN_YAW')]
    execute(COMPOSE+['exec','-T','autonomy']+ENTRY+['ros2','run','agile_navigation','check_start_pose.py',*pose],output,timeout=25)
    if gui:execute([sys.executable,str(ROOT/'scripts/check_gui.py')],output.with_suffix('.gui.json') if output else None,timeout=40)
    deploy('enable')


def signal_readiness(name, pid=None):
    # Match the installed node path, not a broad process-name pattern.
    code = """import os,signal,sys
from pathlib import Path
if sys.argv[2] == 'discover':
    candidates=[]
    for entry in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            if any(arg.endswith(b'/agile_navigation/readiness.py') for arg in entry.read_bytes().split(b'\\0')):
                candidates.append(int(entry.parent.name))
        except OSError: pass
    if len(candidates)!=1: raise RuntimeError('Expected one readiness process')
    pid=candidates[0]
else: pid=int(sys.argv[2])
args=Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(b'\\0')
if not any(arg.endswith(b'/agile_navigation/readiness.py') for arg in args): raise RuntimeError('Readiness PID changed')
os.kill(pid,getattr(signal,sys.argv[1]));print(pid)
"""
    output=execute(COMPOSE+['exec','-T','autonomy','python3','-c',code,name,'discover' if pid is None else str(pid)])
    return int(output.strip())


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('suite',choices=('curves','intersection-left','intersection-right','faults','all'))
    parser.add_argument('--start-x',type=float,help='Override route body spawn x; zero reproduces the long intersection approach.')
    parser.add_argument('--repeat',type=int,default=1)
    parser.add_argument('--rendering',choices=('software','gpu'),default='software')
    parser.add_argument('--gui',action='store_true',help='Keep Gazebo and RViz open during each scenario.')
    args=parser.parse_args()
    if args.repeat<1 or args.repeat>10:parser.error('--repeat must be between 1 and 10')
    config_path=ROOT/'config/scenarios/small_city.json'
    config=json.loads(config_path.read_text(encoding='utf-8-sig'))
    if args.suite=='faults' and args.start_x is not None:parser.error('--start-x applies to navigation routes; fault fixtures start at zero.')
    if args.start_x is not None:
        if not math.isfinite(args.start_x):parser.error('--start-x must be finite')
        for route in config['starts']:config['starts'][route][0]=args.start_x
    from validate_scenarios import validate_routes
    selected=list(config['routes']) if args.suite=='all' else ([args.suite] if args.suite!='faults' else [])
    try:validate_routes(config,selected)
    except (ValueError,FileNotFoundError,ImportError) as exc:parser.error(str(exc))
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'artifacts/scenarios'/run_id;folder.mkdir(parents=True)
    manifest={'schema_version':1,'run_id':run_id,'suite':args.suite,'repeat':args.repeat,'gui':args.gui,'rendering':args.rendering,'starts':config['starts'],'fault_start':[0.0,0.0,0.0],'started_utc':datetime.now(timezone.utc).isoformat(),'git_commit':execute(['git','rev-parse','HEAD']).strip(),'git_status':execute(['git','status','--porcelain']),'image_id':execute(['docker','image','inspect','agile_slam:humble','--format','{{.Id}}']).strip(),'config_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (config_path,ROOT/'compose.yaml',ROOT/'ros2_ws/src/gem_description/config/vehicle.json')},'results':[],'passed':False}
    manifest['source_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for base in ('scripts','ros2_ws/src','config','deploy','containers') for p in (ROOT/base).rglob('*') if p.is_file() and (p.suffix in ('.py','.json','.yaml','.xml','.sdf','.xacro','.sh','.txt') or p.name=='Dockerfile') and '__pycache__' not in p.parts}
    manifest['asset_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'assets/small_city/worlds/small_city.sdf',ROOT/'assets/small_city/maps/small_city.yaml',ROOT/'assets/small_city/maps/small_city.pgm',ROOT/'assets/small_city/maps/small_city_scene.json')}
    manifest['runtime_asset_sha256']={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for directory in ('models','generated') for p in (ROOT/'assets/small_city'/directory).rglob('*') if p.is_file()}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    try:
        routes=list(config['routes']) if args.suite=='all' else ([args.suite] if args.suite!='faults' else [])
        for repeat in range(args.repeat):
            for route in routes:
                print(f'Cold-start route {route}, repeat {repeat+1}',flush=True)
                for key,value in zip(('AGILE_SPAWN_X','AGILE_SPAWN_Y','AGILE_SPAWN_YAW'),config['starts'][route]):os.environ[key]=str(value)
                reset(args.gui,args.rendering,folder/f'{repeat+1}_{route}.start.json')
                turn_counts={'positive':0,'negative':0}
                for goal_index,goal in enumerate(config['routes'][route]):
                    output=folder/f'{repeat+1}_{goal["name"]}.json'
                    command=COMPOSE+['exec','-T','autonomy']+ENTRY+['ros2','run','agile_navigation','check_navigation.py','--ros-args','-p',f'goal_x:={goal["x"]}','-p',f'goal_y:={goal["y"]}','-p',f'goal_yaw:={goal["yaw"]}','-p','timeout:=360.0','-p','sim_timeout:=120.0','-p',f'scene_file:={config["scene_file"]}']
                    with GazeboMonitor(COMPOSE,output.with_suffix('.gazebo.jsonl')):
                        execute(command,output,timeout=450)
                    if args.gui:execute([sys.executable,str(ROOT/'scripts/check_gui.py')],output.with_suffix('.gui.json'),timeout=40)
                    report=json.loads(output.read_text(encoding='utf-8'))
                    start=config['starts'][route]
                    rear=json.loads((ROOT/'ros2_ws/src/gem_description/config/vehicle.json').read_text())['rear_axle_x']
                    expected=[start[0]+rear*math.cos(start[2]),start[1]+rear*math.sin(start[2])]
                    start_error=math.dist(report['initial_odom'],expected) if goal_index==0 else None
                    passed=report['passed'] and (start_error is None or start_error<0.05)
                    manifest['results'].append({'file':output.name,'passed':passed,'initial_odom_error_m':start_error})
                    if not passed:raise RuntimeError(f'Route failed: {goal["name"]}')
                    turn_counts['positive']+=report['positive_turn_commands']
                    turn_counts['negative']+=report['negative_turn_commands']
                    print(f'{goal["name"]}: passed',flush=True)
                if route=='curves':
                    turns=all(count>10 for count in turn_counts.values())
                    manifest['results'].append({'route':route,'repeat':repeat+1,'passed':turns,'turn_commands':turn_counts})
                    if not turns:raise RuntimeError('Curve route did not exercise both steering directions')
            if args.suite in ('faults','all'):
                for fault in ('controller-stop','backend-pause','readiness-pause'):
                    print(f'Cold-start moving fault {fault}, repeat {repeat+1}',flush=True)
                    for key in ('AGILE_SPAWN_X','AGILE_SPAWN_Y','AGILE_SPAWN_YAW'):os.environ[key]='0'
                    reset(args.gui,args.rendering,folder/f'{repeat+1}_{fault}.start.json')
                    event_file=folder/f'{repeat+1}_{fault}.event.json'
                    output=folder/f'{repeat+1}_{fault}.json'
                    relative=event_file.relative_to(ROOT/'artifacts').as_posix()
                    command=COMPOSE+['exec','-T','localization' if fault=='readiness-pause' else 'autonomy']+ENTRY+['ros2','run','agile_vehicle','check_dynamic_fault.py',fault,'/artifacts/'+relative]
                    with output.open('w',encoding='utf-8') as stream,output.with_suffix('.stderr.log').open('w',encoding='utf-8') as errors:
                        process=subprocess.Popen(command,cwd=ROOT,stdout=stream,stderr=errors)
                        injected=False;recovered=False;readiness_resumed=False;readiness_pid=None;deadline=time.monotonic()+150
                        try:
                            while process.poll() is None and time.monotonic()<deadline:
                                if event_file.exists():
                                    event=json.loads(event_file.read_text(encoding='utf-8'));phase=event['phase']
                                    if phase=='moving' and not injected:
                                        if fault=='readiness-pause':readiness_pid=signal_readiness('SIGSTOP')
                                        else:execute(COMPOSE+(['stop','vehicle-control'] if fault=='controller-stop' else ['pause','gazebo']))
                                        injected=True
                                    if phase in ('stopped','inhibited') and injected and not recovered:
                                        if fault=='readiness-pause':
                                            signal_readiness('SIGCONT',readiness_pid)
                                            readiness_resumed=True
                                            execute(COMPOSE+['restart','autonomy'])
                                        else:execute(COMPOSE+(['start','vehicle-control'] if fault=='controller-stop' else ['unpause','gazebo']))
                                        recovered=True
                                time.sleep(.1)
                            if process.poll() is None:raise RuntimeError('Fault observer timeout')
                            if process.returncode:raise RuntimeError(f'Fault observer failed; see {output}')
                        finally:
                            if fault=='readiness-pause' and injected and not readiness_resumed:signal_readiness('SIGCONT',readiness_pid)
                            if fault=='backend-pause' and injected and not recovered:execute(COMPOSE+['unpause','gazebo'])
                            if fault=='controller-stop' and injected and not recovered:execute(COMPOSE+['start','vehicle-control'])
                            if process.poll() is None:process.terminate();process.wait(timeout=10)
                    if args.gui:execute([sys.executable,str(ROOT/'scripts/check_gui.py')],output.with_suffix('.gui.json'),timeout=40)
                    report=json.loads(output.read_text(encoding='utf-8'))
                    passed=report['passed'] and injected and recovered
                    manifest['results'].append({'file':output.name,'passed':passed})
                    if not passed:raise RuntimeError(f'Fault failed: {fault}')
                    print(f'{fault}: passed',flush=True)
        manifest['passed']=bool(manifest['results']) and all(row['passed'] for row in manifest['results'])
    except Exception as exc:
        manifest['error']=str(exc)
        print(str(exc),file=sys.stderr)
    finally:
        try:deploy('disable',folder/'final_disabled.json')
        except Exception as exc:manifest['cleanup_error']=str(exc);manifest['passed']=False
        manifest['finished_utc']=datetime.now(timezone.utc).isoformat()
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        print(str(folder/'manifest.json'),flush=True)
    return 0 if manifest['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
