"""Independent offline formulas. No network, file loading, or engine imports."""
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import hashlib
import json
import math
import statistics

STEP = 900_000
HOUR = 4*STEP


class AuditError(ValueError):
    pass


def near(x, y, name):
    x, y = float(x), float(y)
    if not math.isfinite(x) or not math.isfinite(y) or abs(x-y) > 1e-7+1e-9*max(abs(x),abs(y)):
        raise AuditError(f"{name}: {x!r} != {y!r}")


def quantize(x, step, up=False):
    d, s = Decimal(str(x)), Decimal(str(step))
    if s <= 0:
        raise AuditError("invalid_precision")
    return float((d/s).to_integral_value(rounding=ROUND_CEILING if up else ROUND_FLOOR)*s)


def adverse_price(reference, side, slip, tick):
    return quantize(Decimal(str(reference))*(1+Decimal(str(slip)) if side==1
                    else 1-Decimal(str(slip))), tick, up=side==1)


def raw_index(rows):
    d = {}
    for r in rows:
        if len(r)!=9 or int(r[0])%STEP or str(r[8])!="1":
            raise AuditError("invalid_or_unconfirmed_bar")
        o,h,l,c = map(float,r[1:5])
        if not all(math.isfinite(v) for v in (o,h,l,c)) or not 0<l<=min(o,c)<=max(o,c)<=h:
            raise AuditError("invalid_OHLC")
        t=int(r[0])
        if t in d and tuple(d[t])!=tuple(r):
            raise AuditError("conflicting_duplicate")
        d[t]=r
    return d


def prepare_rows(rows):
    """Independent immutable-input index plus O(1) missing/bad-window gate."""
    d={};bad=set();unlocatable=False
    for r in rows:
        try:
            t=int(r[0]);v=list(map(float,r[1:8]));o,h,l,c=v[:4]
            if (len(r)!=9 or t%STEP or str(r[8])!='1' or not all(math.isfinite(x) for x in v)
                or not 0<l<=min(o,c)<=max(o,c)<=h or v[4]<=0 or min(v[5:])<0):bad.add(t)
            if t in d and tuple(d[t])!=tuple(r):bad.add(t)
            d[t]=tuple(r)
        except (TypeError,ValueError,IndexError):unlocatable=True
    first=min(d)//STEP*STEP if d else 0
    last=(max(d)//STEP+1)*STEP if d else 0
    prefix=[0]
    for t in range(first,last,STEP):prefix.append(prefix[-1]+int(t not in d or t in bad))
    return {'independent_prepared':True,'index':d,'bad':bad,'first':first,'last':last,
            'prefix':prefix,'unlocatable':unlocatable}


def prepare_signals(rows, rules):
    """Independent full signal maps; missing/invalid hours reset EMA history."""
    single=isinstance(rules,dict)
    rules=[rules] if single else list(rules)
    d={};bad=set()
    for r in rows:
        try:
            t=int(r[0]);v=list(map(float,r[1:8]));o,h,l,c=v[:4]
            if (len(r)!=9 or t%STEP or str(r[8])!='1' or
                not all(math.isfinite(x) for x in v) or
                not 0<l<=min(o,c)<=max(o,c)<=h or v[4]<=0 or min(v[5:])<0):
                bad.add(t)
            if t in d and tuple(d[t])!=tuple(r):bad.add(t)
            d[t]=r
        except (TypeError,ValueError,IndexError):
            return {} if single else {rule['id']:{} for rule in rules}
    if not d:return {} if single else {rule['id']:{} for rule in rules}
    bars=[]
    for t in range(min(d)//HOUR*HOUR,max(d)//HOUR*HOUR+HOUR,HOUR):
        keys=[t+k*STEP for k in range(4)]
        if any(k not in d or k in bad for k in keys):bars.append(None);continue
        rr=[d[k] for k in keys]
        bars.append((t+HOUR,max(float(r[2]) for r in rr),min(float(r[3]) for r in rr),float(rr[-1][4])))
    out={}
    for rule in rules:
        fam=rule['family'];sig={};segment=[];fast=slow=None;diffs=[];trs=[];cs=[];osc=[]
        for b in bars:
            if b is None:
                segment=[];fast=slow=None;diffs=[];trs=[];cs=[];osc=[];continue
            t,h,l,c=b;segment.append(b);i=len(segment)-1;cs.append(c)
            trs.append(h-l if i==0 else max(h-l,abs(h-cs[i-1]),abs(l-cs[i-1])))
            if fam=='ema':
                fast=c if fast is None else fast+2/(rule['fast']+1)*(c-fast)
                slow=c if slow is None else slow+2/(rule['slow']+1)*(c-slow)
                diffs.append(fast-slow)
            if fam=='rsi':
                n=rule['n'];delta=[cs[k]-cs[k-1] for k in range(max(1,i-n+1),i+1)]
                gains=sum(max(0,v) for v in delta);losses=sum(max(0,-v) for v in delta)
                osc.append(100. if losses==0 and gains>0 else 50. if gains==losses==0 else 100-100/(1+gains/losses))
            if i<119:continue
            side=0
            if fam=='donchian':
                n=rule['n'];hi=max(z[1] for z in segment[i-n:i]);lo=min(z[2] for z in segment[i-n:i])
                phi=max(z[1] for z in segment[i-n-1:i-1]);plo=min(z[2] for z in segment[i-n-1:i-1])
                side=1 if c>hi and cs[i-1]<=phi else -1 if c<lo and cs[i-1]>=plo else 0
            elif fam=='ema':side=1 if diffs[i-1]<=0<diffs[i] else -1 if diffs[i-1]>=0>diffs[i] else 0
            elif fam=='momentum':
                n=rule['n'];q=rule['threshold'];now=c/cs[i-n]-1;prev=cs[i-1]/cs[i-n-1]-1
                side=1 if prev<=q<now else -1 if prev>=-q>now else 0
            elif fam=='boll':
                n,z=rule['n'],rule['z'];v=cs[i-n+1:i+1];p=cs[i-n:i]
                avg,sd=statistics.mean(v),statistics.pstdev(v);pavg,psd=statistics.mean(p),statistics.pstdev(p)
                side=1 if cs[i-1]<pavg-z*psd and c>=avg-z*sd else -1 if cs[i-1]>pavg+z*psd and c<=avg+z*sd else 0
            elif fam=='rsi':side=1 if osc[i-1]<=rule['low']<osc[i] else -1 if osc[i-1]>=rule['high']>osc[i] else 0
            elif fam=='atr_break':
                n,a,z=rule['n'],rule['atr_n'],rule['atr_multiple']
                hi=max(v[1] for v in segment[i-n:i])+z*statistics.mean(trs[i-a:i])
                lo=min(v[2] for v in segment[i-n:i])-z*statistics.mean(trs[i-a:i])
                side=1 if c>hi else -1 if c<lo else 0
            else:raise AuditError('unknown_signal_family')
            if side:sig[t]=side
        out[rule['id']]=sig
    return out[rules[0]['id']] if single else out


def verify_signals(rows, rule, signals):
    if prepare_signals(rows,rule)!=signals:
        raise AuditError("signal_map_mismatch")
    return {"status":"PASS","coverage":"full_closed_hour_signal_reconstruction"}


def compare(actual, expected, path="result"):
    if isinstance(expected,dict):
        if not isinstance(actual,dict) or set(actual)!=set(expected):raise AuditError(path+"_keys")
        for k in expected:compare(actual[k],expected[k],path+"."+str(k))
    elif isinstance(expected,list):
        if not isinstance(actual,list) or len(actual)!=len(expected):raise AuditError(path+"_length")
        for i,(a,b) in enumerate(zip(actual,expected)):compare(a,b,path+f"[{i}]")
    elif isinstance(expected,bool) or expected is None or isinstance(expected,str):
        if actual!=expected:raise AuditError(path)
    else:near(actual,expected,path)


def verify(rows,spec,funding,config,start,end,signals,result,control=False):
    """Rebuild one episode ledger; full signal maps must pass verify_signals upstream.

    Caller slices rows to [start-120h,end), keeping full-history prepared signals.
    Every first entry/no-entry and every event is independently derived here.
    """
    product=config['product'];derivative=product=='CONDITIONAL_SWAP'
    if product not in ('SPOT','CONDITIONAL_SWAP'):raise AuditError('unknown_product')
    cost={('SPOT','base'):(.001,.0005),('SPOT','stress'):(.002,.001),
          ('CONDITIONAL_SWAP','base'):(.0005,.0005),('CONDITIONAL_SWAP','stress'):(.001,.001)}
    fee,slip=cost[product,config['cost']]
    unknown='UNKNOWN' if derivative else 'NOT_APPLICABLE'
    def invalid(reason,status='DATA_INVALID'):
        expected={'metrics':{'status':status,'target_hit':None,'final_equity':None,'return':None,
            'max_drawdown':None,'fees':None,'funding':None,'exit_reason':reason,
            'true_target':unknown,'true_liquidation':unknown,'real_execution_validation':'UNKNOWN','initial':500.},
            'events':[],'equity':[]}
        compare(result,expected)
        return {'ok':True,'errors':[],'status':'PASS','coverage':'independent_invalid_episode_gate','episode_status':status}
    if start%HOUR or end%STEP or end<=start or end-start!=config['horizon_hours']*HOUR:
        return invalid('invalid_episode_bounds')
    prepared=rows if isinstance(rows,dict) and rows.get('independent_prepared') else prepare_rows(rows)
    d=prepared['index'];left=start-120*HOUR
    if (prepared['unlocatable'] or left<prepared['first'] or end>prepared['last'] or
        prepared['prefix'][(end-prepared['first'])//STEP]!=prepared['prefix'][(left-prepared['first'])//STEP]):
        return invalid('missing_zero_unconfirmed_or_invalid_candle')
    try:
        for field in ('tickSz','lotSz','minSz'):
            if not math.isfinite(float(spec[field])) or float(spec[field])<=0:
                return invalid('invalid_'+field,'SPEC_INVALID')
        if derivative and (spec['instType']!='SWAP' or spec['ctType']!='linear' or spec['settleCcy']!='USDT'
                           or not math.isfinite(float(spec['ctVal'])) or float(spec['ctVal'])<=0):
            return invalid('nonlinear_or_missing_swap_spec','SPEC_INVALID')
        if not derivative and spec.get('instType','SPOT')!='SPOT':return invalid('nonspot_spec','SPEC_INVALID')
    except (ValueError,KeyError,TypeError):return invalid('missing_spec','SPEC_INVALID')
    rates={}
    if derivative:
        try:
            for f in funding:
                t=int(f['fundingTime'])
                if not start-8*HOUR<=t<=end+8*HOUR:continue
                r=float(f['realizedRate'])
                if t%STEP or not math.isfinite(r):return invalid('invalid_funding')
                if t in rates and rates[t]!=r:return invalid('conflicting_funding')
                rates[t]=r
            times=sorted(rates);left=max(t for t in times if t<=start);right=min(t for t in times if t>=end)
            section=[t for t in times if left<=t<=right]
            if any(b-a>8*HOUR for a,b in zip(section,section[1:])):return invalid('funding_gap')
        except (ValueError,KeyError,TypeError):return invalid('missing_funding_coverage')
    if control:
        coin=spec.get('baseCcy') or spec.get('ctValCcy') or spec.get('instId','UNKNOWN').split('-')[0]
        material=[50020261006,product,config['leverage'],config['horizon_hours'],config['cost'],coin,int(start)]
        digest=hashlib.sha256(json.dumps(material,separators=(',',':'),ensure_ascii=True).encode()).digest()
        entry_t=start+int.from_bytes(digest[:8],'big')%(config['horizon_hours']//2)*HOUR
        entry_side=1 if not derivative or digest[-1]&1 else -1
        seed=digest.hex();entries={entry_t:entry_side}
    else:seed=None;entries=signals
    cash=500.;q=contracts=0.;side=0;entry_price=None;attempted=done=False
    pending=None;fees=fund=0.;reason='NO_SIGNAL';events=[];curve=[];values=[]
    def event(t,kind,delta=0.,base_delta=0.,contract_delta=0.,**extra):
        events.append(dict(timestamp=t,type=kind,cash_delta=delta,base_delta=base_delta,
            contract_delta=contract_delta,cash_after=cash,base_after=side*q,
            contracts_after=side*contracts,**extra))
    def mark(reference):
        if q==0:return cash
        p=adverse_price(reference,-side,slip,spec['tickSz'])
        return cash+side*q*(p-entry_price)-q*p*fee if derivative else cash+q*p*(1-fee)
    def exit_position(t,reference,why,terminal=False):
        nonlocal cash,q,contracts,side,done,fees,reason
        old_q,old_contracts,old_side=q,contracts,side
        p=adverse_price(reference,-side,slip,spec['tickSz'])
        if derivative:
            charge=q*p*fee;pnl=side*q*(p-entry_price);delta=pnl-charge;residual=0.
        else:
            sold=quantize(q,spec['lotSz']);sold=0. if sold<float(spec['minSz']) else sold
            residual=q-sold;charge=sold*p*fee;delta=sold*p*(1-fee);pnl=None
        cash+=delta;fees+=charge;q=residual;contracts=0.;side=1 if residual else 0
        done=True;reason=why
        event(t,'EXIT',delta,-old_side*(old_q-q),-old_side*old_contracts,price=p,
              reference_price=float(reference),fee=charge,realized_pnl=pnl,
              reason=why,terminal_proxy=terminal,residual_base=q)
    def funding_event(t,reference,terminal=False):
        nonlocal cash,fund
        if derivative and q and t in rates:
            delta=-side*q*reference*rates[t];cash+=delta;fund+=delta
            event(t,'FUNDING',delta,rate=rates[t],reference_price=reference,
                  notional_proxy=q*reference,terminal_price_proxy=terminal)
    def breach(t,adverse,phase):
        nonlocal cash,q,contracts,side,done,reason
        if derivative and q and not done:
            collateral=cash+side*q*(adverse-entry_price);threshold=q*adverse*.022
            if collateral<=threshold:
                old_q,old_n,old_s=q,contracts,side;delta=-cash
                cash=0.;q=contracts=0.;side=0;done=True;reason='MAINTENANCE_PROXY_BREACH'
                event(t,'MAINTENANCE_PROXY_BREACH',delta,-old_s*old_q,-old_s*old_n,
                      adverse_price=adverse,modeled_collateral=collateral,
                      maintenance_threshold=threshold,model_equity=0.,true_liquidation='UNKNOWN',
                      realized_pnl=None,phase=phase)
    for t in range(start,end,STEP):
        o,h,l,c=map(float,d[t][1:5]);funding_event(t,o)
        # Held-before timestamp funding and opening gap breach precede an exit.
        breach(t,o,'OPEN_BEFORE_EXIT')
        if pending and not done and q:
            if not done:exit_position(t,o,pending)
            pending=None
        if not attempted and not done and t in entries:
            sign=int(entries[t])
            if sign not in (-1,1):raise AuditError('invalid_signal_side')
            if derivative or sign==1:
                attempted=True;side=sign;p=adverse_price(o,side,slip,spec['tickSz']);budget=475.
                if derivative:
                    contracts=quantize(budget/(float(spec['ctVal'])*p*(1/config['leverage']+fee)),spec['lotSz'])
                    q=contracts*float(spec['ctVal']);quantity=contracts
                else:quantity=quantize(budget/p,spec['lotSz']);q=quantity*(1-fee)
                if quantity<=0 or quantity<float(spec['minSz']):
                    q=contracts=0.;side=0;done=True;reason='MIN_SIZE_REJECTED'
                    event(t,'REJECTED',reason=reason,budget=budget)
                else:
                    entry_price=p;charge=(q if derivative else quantity)*p*fee
                    delta=-charge if derivative else -quantity*p;cash+=delta;fees+=charge
                    event(t,'ENTRY',delta,side*q,side*contracts,price=p,reference_price=o,
                          fee=charge,fee_asset=quantity*fee if not derivative else 0.,budget=budget,
                          margin=q*p/config['leverage'] if derivative else 0.,direction=side,
                          signal_timestamp=t,quantity=quantity)
        if derivative and q and not done:breach(t+STEP,l if side>0 else h,'INTRABAR_ADVERSE')
        value=mark(c);values.append(value)
        curve.append(dict(timestamp=t+STEP,cash=cash,base=side*q,contracts=side*contracts,
                          equity=value,exit_cost_included=True))
        if q and not done and pending is None:
            pending='TARGET_CLOSE_SIGNAL' if value>=650 else 'STOP_CLOSE_SIGNAL' if value<=250 else None
    last=float(d[end-STEP][4])
    if q and not done:
        funding_event(end,last,True)
        breach(end,last,'TERMINAL_AFTER_FUNDING')
        if not done:exit_position(end,last,'HORIZON_TERMINAL',True)
    final=mark(last)
    curve[-1].update(cash=cash,base=side*q,contracts=side*contracts,equity=final)
    peak=500.;dd=0.
    for value in values+[final]:peak=max(peak,value);dd=max(dd,1-value/peak)
    status='ORDER_REJECTED' if reason=='MIN_SIZE_REJECTED' else 'NO_TRADE' if not attempted else 'VALID'
    expected={'metrics':dict(status=status,target_hit=final>=650,final_equity=final,**{'return':final/500-1},
        max_drawdown=dd,fees=fees,funding=fund,exit_reason=reason,initial=500.,true_target=unknown,
        true_liquidation=unknown,real_execution_validation='UNKNOWN',control_seed=seed,
        terminal_residual_base=q,current_specs_historical_validity='UNKNOWN'),'events':events,'equity':curve}
    compare(result,expected)
    return {'ok':True,'errors':[],'status':'PASS','coverage':'independent_first_entry_and_full_15m_ledger',
            'signal_requirement':'full signal map separately verified before evaluation',
            'episode_status':status,'events':len(events),'equity_points':len(curve),
            'independent_final_equity':final,'independent_target_hit':final>=650,
            'real_execution_validation':'UNKNOWN','true_target':unknown,'true_liquidation':unknown}
