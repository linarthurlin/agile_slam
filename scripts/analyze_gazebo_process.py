"""Summarize renderer CPU activity around independently observed Gazebo gaps."""
import argparse
import json
from pathlib import Path


def summarize(stats_path):
    stats=[json.loads(line) for line in stats_path.read_text().splitlines()]
    process_path=stats_path.with_suffix('.process.jsonl')
    samples=[json.loads(line) for line in process_path.read_text().splitlines()]
    gaps=[]
    for before,after in zip(stats,stats[1:]):
        gap=after['monotonic_s']-before['monotonic_s']
        if gap<1:
            continue
        nearby=[s for s in samples if before['wall_unix_s']-0.5<=s['wall_unix_s']<=after['wall_unix_s']+0.5]
        activity=[]
        for a,b in zip(nearby,nearby[1:]):
            old={t['tid']:t for p in a['processes'] for t in p['threads']}
            for p in b['processes']:
                for t in p['threads']:
                    if t['tid'] in old:
                        delta=t['cpu_ticks']-old[t['tid']]['cpu_ticks']
                        if delta>0:
                            activity.append({'wall_unix_s':b['wall_unix_s'],'interval_s':b['monotonic_s']-a['monotonic_s'],'tid':t['tid'],'name':t['name'],'cpu_ticks_delta':delta,'wchan':t['wchan']})
        gaps.append({'end_wall_unix_s':after['wall_unix_s'],'wall_gap_s':gap,'sim_delta_s':after['sim_s']-before['sim_s'],'top_cpu_intervals':sorted(activity,key=lambda row:row['cpu_ticks_delta'],reverse=True)[:12]})
    return {'stats_file':stats_path.name,'process_samples':len(samples),'max_sample_gap_s':max((b['monotonic_s']-a['monotonic_s'] for a,b in zip(samples,samples[1:])),default=None),'gaps':gaps,'scope':'Correlated CPU activity and wait channels; no native stack trace or causal proof.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stats',type=Path)
    args=parser.parse_args()
    print(json.dumps(summarize(args.stats),indent=2))
