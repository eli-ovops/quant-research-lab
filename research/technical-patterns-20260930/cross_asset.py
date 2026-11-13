"""Fixed multi-asset event audit; input completeness is a hard gate."""
from pathlib import Path
import json,hashlib,datetime,math,collections
import study as s,regime as g,robustness as b
P=Path(__file__).resolve().parent;O=P/'cross-asset-01'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gate(rows,start,end):
 d={}
 for r in rows:
  t=int(r[0])
  if not start<=t<end:continue
  if len(r)!=9 or r[8]!='1' or t%s.H:raise ValueError('fields_confirmation_alignment')
  v=list(map(float,r[1:8]));o,hi,lo,c=v[:4]
  if not all(math.isfinite(x) for x in v) or not 0<lo<=min(o,c)<=max(o,c)<=hi or v[4]<=0 or min(v[5:])<0:raise ValueError('OHLCV_invalid_or_zero')
  if t in d and d[t]!=r:raise ValueError('conflicting_duplicate')
  d[t]=r
 missing=sorted(set(range(start,end,s.H))-set(d))
 if missing:raise ValueError(f'missing_hours={len(missing)} first={missing[0]}')
 return d

def main():
 proto=json.loads((O/'protocol.json').read_text());start=int(datetime.datetime.fromisoformat(proto['start_including_warmup']).timestamp()*1000);end=int(datetime.datetime.fromisoformat(proto['end_exclusive']).timestamp()*1000)
 for n,h in proto['code_hashes'].items():assert sha(P/n)==h
 freeze={'analysis_code_sha256':sha(Path(__file__)),'protocol_sha256':sha(O/'protocol.json'),'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 with (O/'analysis_freeze.json').open('x') as f:json.dump(freeze,f,indent=2)
 raw,proof=s.system.source_gate.load();results=[];gates={};manifest=[];audits=[]
 for coin in proto['reference_assets']+proto['new_assets']:
  try:
   if coin in raw:rows=list(raw[coin].values())
   else:
    rows=[]
    for p in sorted((O/'raw').glob(coin+'_[0-9][0-9][0-9].json')):
     x=json.loads(p.read_text());assert x['ok'] and x['request']['instId']==coin+'-USDT' and x['request']['bar']=='1H'
     manifest.append({'path':str(p.resolve()),'sha256':sha(p)});rows.extend(x['data']['data'])
   d=gate(rows,start,end);gates[coin]={'status':'PASS','hours':len(d)}
   ordered=[d[t] for t in sorted(d)];bars=s.features(ordered);rs=g.records(bars,72);screen,events=g.evaluate(rs,'down');second=b.independent_events(ordered)
   assert [(r['t'],r['exit_t']) for r in events]==[(r['t'],r['exit_t']) for r in second]
   assert all(abs(x['gross']-y['gross'])<1e-12 for x,y in zip(events,second))
   audits.append({'coin':coin,'independent_event_rebuild':'PASS','events':len(events)})
   for lag in [0,1,4]:
    ev=[];censored=0
    for e in events:
     t=e['t']+lag*s.H;z=e['exit_t']+lag*s.H
     if t not in d or z not in d:censored+=1;continue
     buy=float(d[t][1]);sell=float(d[z][1]);gross=sell/buy-1
     base=(sell*(1-.0005)*(.999**2)/(buy*(1+.0005))-1)*10000
     stress=(sell*(1-.001)*(.998**2)/(buy*(1+.001))-1)*10000
     assert abs(base-s.net(gross))<1e-8 and abs(stress-s.net(gross,.002,.001))<1e-8
     ev.append(dict(t=t,exit_t=z,base_bps=base,stress_bps=stress))
    kept=g.nonoverlap(ev)
    yearly={str(y):b.summary([r for r in kept if datetime.datetime.fromtimestamp(r['t']/1000,datetime.timezone.utc).year==y]) for y in [2023,2024,2025,2026]}
    result={'coin':coin,'delay_hours':lag,'censored':censored,'all':b.summary(ev),'nonoverlap':b.summary(kept),'yearly':yearly,
     'zero_delay_matched_support':screen['matched_support'],'zero_delay_matched_excess_bps':screen['matched_excess_bps'],'zero_delay_screen_failures':screen['screen_failures']}
    results.append(result);s.system.engine.dump(O/f'{coin}_{lag}_events.json',{'all':ev,'nonoverlap':kept})
  except (ValueError,AssertionError,KeyError) as e:
   gates[coin]={'status':'BLOCKED','reason':str(e)}
   results=[r for r in results if r['coin']!=coin]
 assert freeze['analysis_code_sha256']==sha(Path(__file__))
 s.system.engine.dump(O/'results.json',{'classification':'EXPLORATORY_CROSS_ASSET_EXTENSION','input_gates':gates,'results':results,'independent_events':audits,'validated_profitability':None})
 s.system.engine.dump(O/'manifest.json',{'reference_source_proof':proof,'files':manifest})
 def fmt(v):return 'N/A' if v is None else f'{v/100:.3f}%'
 lines=['# 跨币种布林反弹测试','', '固定原规则：下跌ER20≥0.30、布林20/2下轨回归，持有72h；不逐币优化。',
 '现货1h构造4h；测试2023至2026上半年，统一130根4h预热。基础每边10bps费用+5bps滑点；压力每边20+10bps。延迟同时顺延入场与退出。', '',
 '|币|延迟h|不重叠样本|基础均值|压力均值|压力中位数|去最好5次后压力均值|最差一次|', '|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in results:
  v=r['nonoverlap'];lines.append(f"|{r['coin']}|{r['delay_hours']}|{v['n']}|{fmt(v['base_mean_bps'])}|{fmt(v['stress_mean_bps'])}|{fmt(v['stress_median_bps'])}|{fmt(v['without_top5_stress_mean_bps'])}|{fmt(v['worst_bps'])}|")
 lines+=['','## 数据门槛','',json.dumps(gates,ensure_ascii=False),'','## 零延迟分年压力均值与原筛选门槛','']
 for r in results:
  if r['delay_hours']!=0:continue
  ys='；'.join(f"{y}: n={v['n']} {fmt(v['stress_mean_bps'])}" for y,v in r['yearly'].items())
  lines.append(f"- {r['coin']}：{ys}。对照支持率{r['zero_delay_matched_support']:.1%}；失败项{r['zero_delay_screen_failures']}。")
 lines+=['','## 解释限制','',
 '均值是独立情景的事件收益，不是账户收益；跨币相关性、资金共享及容量未模拟，不得相加。',
 'BTC/ETH按统一预热期重算，可能与旧80小时预热后再丢弃130根4h的数据起点不同；没有为获得有利结果选择时期。',
 '新币种仍来自当前存续交易对，有幸存者及人工选币偏差；同一历史宏观行情不是独立时间留出集。',
 '完整时间戳、闭合K线、OHLCV与双实现事件重建核验通过只说明数据/计算条件成立；未核验全部小时与日线交叉源、历史订单规格或可成交性。',
 '匹配对照仅按原零延迟计算，不冒充延迟后重新匹配。去最好/最差5次为敏感性诊断，不是可执行规则。',
 '无强平/资金费模拟，不是合约验证；无样本外验证或显著性验收，不凭最佳币种宣布策略成功。不重启轮询。']
 (O/'REPORT.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'gates':gates,'scenarios':len(results),'zero_delay':[{ 'coin':r['coin'],**r['nonoverlap']} for r in results if r['delay_hours']==0]},ensure_ascii=False))
if __name__=='__main__':main()
