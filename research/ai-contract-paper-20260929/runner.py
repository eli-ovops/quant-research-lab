"""Public-input-only conditional futures ledger. Never connects to an account."""
import argparse, fcntl, hashlib, json, time
from decimal import Decimal as D, ROUND_FLOOR
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def now(): return int(time.time()*1000)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 t=p.with_suffix('.tmp'); t.write_text(json.dumps(x,ensure_ascii=False,indent=2));t.replace(p)
def sweep(levels,contracts,unit):
 left=D(contracts); value=D(0)
 for row in levels:
  price,size=map(D,row[:2])
  if price<=0 or size<0: raise ValueError('INVALID_LEVEL')
  take=min(left,size);value+=take*price*unit;left-=take
  if left==0: return value
 raise ValueError('INSUFFICIENT_DEPTH')
def validate(s,after=0):
 b=s['book'];m=s['mark'];t=s['received_ms']
 for ts in [int(b['ts']),int(m['ts'])]:
  if not -1000<=t-ts<=5000:raise ValueError('STALE_OR_FUTURE')
 if int(b['ts'])<=after:raise ValueError('QUOTE_BEFORE_DECISION')
 if D(b['asks'][0][0])<=D(b['bids'][0][0]):raise ValueError('CROSSED_BOOK')
 for side,reverse in [('asks',False),('bids',True)]:
  ps=[D(r[0]) for r in b[side]]
  if ps!=sorted(ps,reverse=reverse):raise ValueError('UNSORTED_BOOK')
 if D(m['markPx'])<=0:raise ValueError('INVALID_MARK')

def enter(s,spec,side,lever,fee,slip):
 unit=D(spec['ctVal'])*D(spec.get('ctMult') or '1');lot=D(spec['lotSz'])
 px=D(s['book']['asks' if side==1 else 'bids'][0][0])
 qty=(D(120)*lever/(px*unit)/lot).to_integral_value(rounding=ROUND_FLOOR)*lot
 if qty<D(spec['minSz']):raise ValueError('BELOW_MINIMUM')
 n=sweep(s['book']['asks' if side==1 else 'bids'],qty,unit)*(1+side*slip)
 # Bound margin budget after depth and adverse execution.
 while n/lever>D(120) and qty>=D(spec['minSz']):
  qty-=lot
  if qty<=0:break
  n=sweep(s['book']['asks' if side==1 else 'bids'],qty,unit)*(1+side*slip)
 if qty<D(spec['minSz']) or n/lever+n*fee>D(150):raise ValueError('MARGIN_BUDGET')
 return dict(side=side,leverage=lever,fee=str(fee),slip=str(slip),contracts=str(qty),unit=str(unit),entry_notional=str(n),entry_fee=str(n*fee),entry_ms=s['received_ms'],entry_book_ms=int(s['book']['ts']),conditional_equity=None,validated_equity=None,closed=False,funding_estimate='0',funding_times=[],observations=0,max_equity='150',max_drawdown='0')
def value(a,s):
 out=sweep(s['book']['bids' if a['side']==1 else 'asks'],a['contracts'],D(a['unit']))*(1-a['side']*D(a['slip']))
 pnl=a['side']*(out-D(a['entry_notional']))
 return D(150)+pnl-D(a['entry_fee'])-out*D(a['fee'])-D(a['funding_estimate'])
def charge(a,rate,mark):return a['side']*D(a['contracts'])*D(a['unit'])*D(mark)*D(rate)
def update(a,s,deadline):
 if a['closed']:return
 for f in s.get('funding_history',[]):
  ft=int(f['fundingTime'])
  if a['entry_ms']<ft<=s['received_ms'] and ft not in a['funding_times']:
   rate=f.get('realizedRate')
   if rate in (None,''):continue
   cost=charge(a,rate,s['mark']['markPx'])
   a['funding_estimate']=str(D(a['funding_estimate'])+cost);a['funding_times'].append(ft)
   a.setdefault('funding_evidence',[]).append(dict(time=ft,rate=rate,proxy_mark=s['mark']['markPx'],mark_ms=s['mark']['ts'],cost=str(cost)))
 eq=value(a,s);a['conditional_equity']=str(eq);a['observations']+=1
 a['max_equity']=str(max(eq,D(a['max_equity'])));a['max_drawdown']=str(max(D(a['max_drawdown']),D(a['max_equity'])-eq))
 if eq>=300 or eq<=75 or s['received_ms']>=deadline:
  a.update(closed=True,exit_ms=s['received_ms'],exit_reason='TARGET' if eq>=300 else 'LOSS_THRESHOLD' if eq<=75 else 'DEADLINE',deadline_censored=s['received_ms']>deadline+300000)

def init(decision_file):
 if (ROOT/'run.json').exists():raise ValueError('EXISTING_RUN_NO_RESTART')
 d=json.loads(Path(decision_file).read_text())
 if d['input_sha256']!=sha(ROOT/'decision-input.json'):raise ValueError('INPUT_HASH')
 if d['action'] not in ['LONG','SHORT','WAIT']:raise ValueError('ACTION')
 if d['action']!='WAIT' and d['instrument'] not in ['BTC-USDT-SWAP','ETH-USDT-SWAP']:raise ValueError('INSTRUMENT')
 # WAIT keeps cash; BTC is fixed control instrument, not an AI recommendation.
 inst=d['instrument'] if d['action']!='WAIT' else 'BTC-USDT-SWAP'
 spec=json.loads((ROOT/'decision-input.json').read_text())['markets'][inst]['spec']
 if spec['ctType']!='linear' or spec['settleCcy']!='USDT':raise ValueError('UNSUPPORTED_CONTRACT')
 r=dict(schema=1,status='AWAITING_FIRST_SAMPLE',decision=d,commit_ms=now(),instrument=inst,spec=spec,code_hash=sha(Path(__file__)),protocol_hash=sha(ROOT/'PROTOCOL.md'),decision_hash=sha(Path(decision_file)),accounts={},samples=[],errors=[],validated_equity=None,liquidation='UNKNOWN',fee_verification='UNKNOWN',funding_method='REALIZED_RATE_TIMES_OBSERVATION_MARK_PROXY',funding_complete=False)
 save(ROOT/'run.json',r);return r

def ingest(path):
 r=json.loads((ROOT/'run.json').read_text())
 if r['code_hash']!=sha(Path(__file__)) or r['protocol_hash']!=sha(ROOT/'PROTOCOL.md'):raise ValueError('FROZEN_CODE_CHANGED')
 s=json.loads(Path(path).read_text());digest=sha(Path(path))
 if any(x['sha256']==digest for x in r['samples']):return r
 if r['status'] in ['COMPLETED_CONDITIONAL','ENDED_DATA_CENSORED','START_FAILED']:return r
 try:
  if s['instrument']!=r['instrument']:raise ValueError('WRONG_INSTRUMENT')
  if abs(now()-s['received_ms'])>120000:raise ValueError('INGEST_TOO_LATE')
  validate(s,r['commit_ms'])
  if r['samples'] and s['received_ms']<=r['samples'][-1]['received_ms']:raise ValueError('NON_MONOTONIC')
  if not r['accounts']:
   if s['received_ms']-r['commit_ms']>600000:
    r['status']='START_FAILED';raise ValueError('START_TIMEOUT')
   r['start_ms']=s['received_ms'];r['deadline_ms']=r['start_ms']+86400000
   for name,fee,slip in [('base',D('.0005'),D('.0005')),('stress',D('.001'),D('.001'))]:
    for leverage in [5,10,20]:
     for side in [1,-1]:
      key=f'{name}_{leverage}_{side}'
      r['accounts'][key]=enter(s,r['spec'],side,leverage,fee,slip)
   r['status']='RUNNING_CONDITIONAL'
  slot=min(96,(s['received_ms']-r['start_ms'])//900000)
  if any(x['slot']==slot for x in r['samples']):return r
  for a in r['accounts'].values():update(a,s,r['deadline_ms'])
  r['samples'].append(dict(path=str(Path(path).resolve()),sha256=digest,received_ms=s['received_ms'],slot=slot,book_ms=s['book']['ts'],mark_ms=s['mark']['ts']))
  expected=min(97,1+(s['received_ms']-r['start_ms'])//900000)
  r['missing_windows']=max(0,expected-len(r['samples']))
  r['updated_ms']=now()
  if s['received_ms']>=r['deadline_ms']:r['status']='COMPLETED_CONDITIONAL'
 except (ValueError,KeyError,IndexError) as e:
  r['errors'].append(dict(time=now(),error=str(e),path=str(path),sha256=digest))
 save(ROOT/'run.json',r);return r

def report(r):
 lines=['# 合约条件纸面观察状态',f"状态：{r['status']}；有效观察 {len(r['samples'])}；漏采窗口 {r.get('missing_windows',0)}。",'真实净收益、强平存活结果：UNKNOWN；以下仅含假设费用与资金费代理估算。不得选最好情景作为策略收益。']
 side={'LONG':1,'SHORT':-1}.get(r['decision']['action'])
 lines.append(f"AI决策：{r['decision']['action']} {r['decision'].get('instrument')}。")
 if side is None:lines.append('AI未开条件仓，现金基准150；下面仅对照。')
 lines+=['','|场景|角色|条件净值 USDT|退出原因|','|---|---|---:|---|']
 for k,a in r['accounts'].items():
  lines.append(f"|{k}|{'AI与同向对照' if a['side']==side else '固定方向对照'}|{a['conditional_equity']}|{a.get('exit_reason','未退出')}|")
 lines+=['','资金费数据/结算标记价未完整验收，15分钟间隔不能证明期间未强平。观察样本仅一轮，翻倍概率不可估计。','',f"错误记录：{len(r['errors'])}；账本和原始路径见run.json。"]
 (ROOT/'REPORT.md').write_text('\n'.join(lines))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['init','ingest','report','finalize']);p.add_argument('path',nargs='?');a=p.parse_args()
 with (ROOT/'ledger.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  r=init(a.path) if a.action=='init' else ingest(a.path) if a.action=='ingest' else json.loads((ROOT/'run.json').read_text())
  if a.action=='finalize':
   if now()<r.get('deadline_ms',r['commit_ms']+600000):raise ValueError('BEFORE_DEADLINE')
   if r['status'] not in ['COMPLETED_CONDITIONAL','START_FAILED']:r['status']='ENDED_DATA_CENSORED'
   r['finalized_ms']=now();save(ROOT/'run.json',r)
  report(r);print(json.dumps({k:r.get(k) for k in ['status','instrument','start_ms','deadline_ms','updated_ms','missing_windows']},ensure_ascii=False));print('observations',len(r['samples']),'errors',len(r['errors']))
