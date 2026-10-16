"""Bounded, read-only Linux process sampler used inside the simulator container."""
import json
from pathlib import Path
import sys
import time


def sample():
    processes=[]
    for path in Path('/proc').glob('[0-9]*/cmdline'):
        try:
            command=path.read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if not command.startswith('ign gazebo -r -s '):
                continue
            threads=[]
            for task in path.parent.joinpath('task').iterdir():
                try:
                    raw=task.joinpath('stat').read_text()
                    fields=raw[raw.rfind(')')+2:].split()
                    threads.append({'tid':int(task.name),'name':task.joinpath('comm').read_text().strip(),'state':fields[0],'cpu_ticks':int(fields[11])+int(fields[12]),'wchan':task.joinpath('wchan').read_text().strip(),'schedstat':task.joinpath('schedstat').read_text().strip()})
                except (OSError,ValueError):
                    continue
            processes.append({'pid':int(path.parent.name),'threads':threads})
        except OSError:
            continue
    return {'wall_unix_s':time.time(),'monotonic_s':time.monotonic(),'processes':processes,'loadavg':Path('/proc/loadavg').read_text().strip(),'cpu_pressure':Path('/proc/pressure/cpu').read_text().strip(),'memory_pressure':Path('/proc/pressure/memory').read_text().strip()}


if __name__=='__main__':
    marker=Path(sys.argv[1])
    deadline=time.monotonic()+450
    time.sleep(1)
    while marker.exists() and time.monotonic()<deadline:
        print(json.dumps(sample()),flush=True)
        time.sleep(0.25)
