"""Independent Gazebo statistics probe for host-orchestrated navigation tests."""
import hashlib
import json
from pathlib import Path
import subprocess
import threading
import time


class GazeboMonitor:
    def __init__(self, compose, output):
        self.compose=compose;self.output=Path(output);self.records=[];self.error=None
        self.pidfile='/tmp/agile-stats-'+hashlib.sha256(str(self.output).encode()).hexdigest()[:16]+'.pid'

    def network_snapshot(self):
        snapshot={}
        code="import json, os; from pathlib import Path; lines=Path('/proc/net/snmp').read_text().splitlines(); names=lines[0].split()[1:]; values=lines[1].split()[1:]; fields=dict(zip(names,map(int,values))); print(json.dumps({'render_environment':{k:os.environ.get(k) for k in ('LIBGL_ALWAYS_SOFTWARE','LP_NUM_THREADS','LP_NATIVE_VECTOR_WIDTH','GALLIUM_DRIVER')},'mtu':int(Path('/sys/class/net/eth0/mtu').read_text()),'ip':{k:fields[k] for k in ('ReasmReqds','ReasmOKs','ReasmFails','ReasmTimeout','FragOKs','FragFails','FragCreates')}}))"
        for service in ('core','backend-sim'):
            try:
                result=subprocess.run(self.compose+['exec','-T',service,'python3','-c',code],capture_output=True,text=True,encoding='utf-8',timeout=10)
                snapshot[service]=json.loads(result.stdout) if result.returncode==0 else {'error':result.stderr}
            except Exception as exc:snapshot[service]={'error':str(exc)}
        return snapshot

    def __enter__(self):
        self.network_before=self.network_snapshot()
        self.stream=self.output.open('w',encoding='utf-8')
        self.errors=self.output.with_suffix('.stderr.log').open('w',encoding='utf-8')
        command=self.compose+['exec','-T','backend-sim','sh','-c','echo $$ > "$1"; exec timeout --signal=INT 450 ign topic -e -t /world/small_city/stats --json-output','sh',self.pidfile]
        self.process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=self.errors,text=True,encoding='utf-8',bufsize=1)
        self.thread=threading.Thread(target=self.read,daemon=True);self.thread.start()
        self.resources=self.output.with_suffix(".process.jsonl").open("w",encoding="utf-8")
        sampler=Path(__file__).with_name("sample_gazebo_process.py").read_text(encoding="utf-8-sig")
        self.resource_process=subprocess.Popen(self.compose+["exec","-T","backend-sim","python3","-u","-c",sampler,self.pidfile],stdout=self.resources,stderr=self.errors)
        return self

    def read(self):
        try:
            for line in self.process.stdout:
                if not line.strip():continue
                data=json.loads(line)
                stamp=data.get('simTime',{})
                record={'wall_unix_s':time.time(),'monotonic_s':time.monotonic(),'sim_s':int(stamp.get('sec',0))+int(stamp.get('nsec',0))*1e-9,'iterations':int(data.get('iterations',0)),'rtf':data.get('realTimeFactor',0),'paused':data.get('paused',False)}
                self.records.append(record);self.stream.write(json.dumps(record)+'\n');self.stream.flush()
        except Exception as exc:self.error=str(exc)

    def __exit__(self, kind, value, traceback):
        network_after=self.network_snapshot()
        # Stop only the probe's bounded timeout process, never the Gazebo server.
        cleanup='if [ -r "$1" ]; then pid=$(cat "$1"); case "$pid" in *[!0-9]*|"") ;; *) if [ -r "/proc/$pid/cmdline" ] && tr "\\000" " " < "/proc/$pid/cmdline" | grep -q "^timeout --signal=INT 450 ign topic"; then kill -TERM "$pid"; fi ;; esac; rm -f -- "$1"; fi'
        try:subprocess.run(self.compose+['exec','-T','backend-sim','sh','-c',cleanup,'sh',self.pidfile],capture_output=True,timeout=10)
        except Exception as exc:self.error=str(exc)
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.terminate();self.process.wait(timeout=5)
        self.thread.join(timeout=3)
        try:self.resource_process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.resource_process.terminate();self.resource_process.wait(timeout=5)
        self.resources.close()
        self.stream.close();self.errors.close()
        gaps=[{'wall_unix_s':b['wall_unix_s'],'wall_gap_s':b['monotonic_s']-a['monotonic_s'],'sim_delta_s':b['sim_s']-a['sim_s'],'iteration_delta':b['iterations']-a['iterations']} for a,b in zip(self.records,self.records[1:])]
        summary={'source':'Gazebo Transport /world/small_city/stats, independent of ROS bridge','samples':len(self.records),'capture_error':self.error,'max_wall_gap_s':max((g['wall_gap_s'] for g in gaps),default=None),'gaps_over_one_second':[g for g in gaps if g['wall_gap_s']>1.0],'first':self.records[0] if self.records else None,'last':self.records[-1] if self.records else None}
        summary['process_samples_file']=self.output.with_suffix('.process.jsonl').name
        summary['network_before']=self.network_before;summary['network_after']=network_after
        summary['ip_counter_delta']={service:{key:network_after[service]['ip'][key]-before['ip'][key] for key in before['ip']} for service,before in self.network_before.items() if 'ip' in before and 'ip' in network_after[service]}
        self.output.with_suffix('.summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
        try:
            logs=subprocess.run(self.compose+['logs','--no-color','--timestamps','backend-sim','core'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=15)
            self.output.with_suffix('.runtime.log').write_text(logs.stdout,encoding='utf-8')
        except Exception as exc:self.output.with_suffix('.runtime.log').write_text('Log collection failed: '+str(exc),encoding='utf-8')
        return False
