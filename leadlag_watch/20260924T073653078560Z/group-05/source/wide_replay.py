"""Independent replay adapter for explicitly mapped public market identifiers."""
import argparse
import json
from pathlib import Path
import replay as core


def canonical_frame(row, native_symbols):
    if row.get('kind')!='frame' or row.get('raw')=='pong':return row
    venue=row['venue'];mapping={native:canonical for canonical,native in native_symbols[venue].items()}
    msg=json.loads(row['raw'])
    if venue=='gate' and msg.get('channel')=='spot.order_book' and msg.get('event')=='update':
        native=msg['result']['s'].replace('_','');canonical=mapping.get(native,native)
        msg['result']['s']=canonical[:-4]+'_USDT'
    elif venue=='okx' and 'arg' in msg and 'data' in msg:
        native=msg['arg']['instId'].replace('-','');canonical=mapping.get(native,native)
        msg['arg']['instId']=canonical[:-4]+'-USDT'
    return dict(row,raw=json.dumps(msg))


def replay_group(run):
    config=json.loads((Path(run)/'config.json').read_text());original=core.reduce_frame
    def reduce(books,row):
        try:row=canonical_frame(row,config['native_symbols'])
        except (ValueError,KeyError,TypeError):pass
        original(books,row)
    try:
        core.reduce_frame=reduce
        return core.replay(run)
    finally:core.reduce_frame=original


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True,type=Path);a=p.parse_args()
    groups=sorted(a.run_dir.glob('group-*')) or [a.run_dir]
    passed=True
    for group in groups:
        result=replay_group(group)
        (group/'replay-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        ok=result['passed'] and result['complete'];passed=passed and ok
        print(json.dumps({'group':group.name,'passed':ok,'errors':result['errors'],'decisions':result['decisions'],'estimates':result['estimates_compared'],'delays':result['delays_compared']}),flush=True)
    raise SystemExit(0 if passed else 1)
