#!/usr/bin/env python3
"""Collect reviewed scenario runs without dropping failed or stress trials."""
import argparse
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('run_ids',nargs='+')
    parser.add_argument('--output',default='artifacts/scenario_summary.json')
    args=parser.parse_args()
    summary={'scope':'Initial simulation evidence including negative/stress trials; no real vehicle or repeated-trial acceptance.','runs':[]}
    base=(ROOT/'artifacts/scenarios').resolve()
    for run_id in args.run_ids:
        folder=(base/run_id).resolve()
        if folder.parent!=base:parser.error('Run IDs must name a direct child of artifacts/scenarios.')
        manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8-sig'))
        if 'finished_utc' not in manifest:parser.error('Run is still active: '+run_id)
        fields=('run_id','suite','repeat','gui','rendering','starts','fault_start','git_commit','git_status','image_id','config_sha256','source_sha256','asset_sha256','runtime_asset_sha256','started_utc','finished_utc','passed','results','error','cleanup_error')
        evidence={key:manifest[key] for key in fields if key in manifest}
        evidence['reports']={}
        for path in sorted(folder.glob('[0-9]*.json')):
            if path.name.endswith('.event.json'):continue
            try:data=json.JSONDecoder().raw_decode(path.read_text(encoding='utf-8-sig').lstrip())[0]
            except ValueError:data={'passed':False,'error':'Non-JSON output; inspect the raw run logs.'}
            evidence['reports'][path.name]=data
        evidence['final_disabled']=json.loads((folder/'final_disabled.json').read_text(encoding='utf-8-sig'))
        summary['runs'].append(evidence)
    summary['all_runs_passed']=all(run['passed'] for run in summary['runs'])
    output=(ROOT/args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(output)
    return 0

if __name__=='__main__':raise SystemExit(main())
