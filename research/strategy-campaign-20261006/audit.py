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


def compare_signals(actual,expected):
    compare(actual,expected,'signals')
    return {'ok':True,'errors':[],'coverage':'full_independent_signal_map'}


def prepare_signals(rows,rules):
    """Reconstruct every eligible boundary; no file or engine dependency."""
    one=isinstance(rules,dict);rules=[rules] if one else list(rules)
    p=rows if isinstance(rows,dict) and rows.get('independent_prepared') else prepare_rows(rows)
    d,bad=p['index'],p['bad'];out={}
    def rsi(c,n):
        delta=[c[i]-c[i-1] for i in range(len(c)-n,len(c))]
        gains=statistics.mean(max(x,0) for x in delta);losses=statistics.mean(max(-x,0) for x in delta)
        return 100. if losses==0 and gains>0 else 50. if gains==losses==0 else 100-100/(1+gains/losses)
    def er(c):
        changes=[abs(c[k]-c[k-1]) for k in range(len(c)-20,len(c))]
        path=sum(changes)
        return abs(c[-1]-c[-21])/path if path else 0.
    def band(c,n,z):
        v=c[-n:];avg,sd=statistics.mean(v),statistics.pstdev(v)
        return avg-z*sd,avg+z*sd
    for rule in rules:
        family=rule['family'];step=STEP if family=='scalp' else HOUR;warm=480 if family=='scalp' else 120
        features={};segment=[];cs=[];trs=[];fast=slow=ema48=None
        if not d or p['unlocatable']:out[rule['id']]={};continue
        for opening in range(min(d)//step*step,max(d)//step*step+step,step):
            keys=range(opening,opening+step,STEP)
            if any(t not in d or t in bad for t in keys):
                segment=[];cs=[];trs=[];fast=slow=ema48=None;continue
            rr=[d[t] for t in keys]
            b={'o':float(rr[0][1]),'h':max(float(r[2]) for r in rr),
               'l':min(float(r[3]) for r in rr),'c':float(rr[-1][4]),'v':sum(float(r[5]) for r in rr)}
            previous=cs[-1] if cs else b['c']
            trs.append(max(b['h']-b['l'],abs(b['h']-previous),abs(b['l']-previous)))
            segment.append(b);cs.append(b['c']);priorfast,priorslow=fast,slow
            if family=='trend':
                fast=b['c'] if fast is None else fast+2/(rule['fast']+1)*(b['c']-fast)
                slow=b['c'] if slow is None else slow+2/(rule['slow']+1)*(b['c']-slow)
            ema48=b['c'] if ema48 is None else ema48+2/49*(b['c']-ema48)
            if len(segment)<warm:continue
            c,previous=cs[-1],cs[-2];long=short=False;eff=er(cs)
            if family=='trend':
                long=priorfast<=priorslow and fast>slow and eff>=rule['er_min']
                short=priorfast>=priorslow and fast<slow and eff>=rule['er_min']
            elif family=='breakout':
                channel=segment[-rule['n']-1:-1]
                enough_volume=b['v']>=rule['volume_multiple']*statistics.mean(x['v'] for x in segment[-21:-1])
                long=c>max(x['h'] for x in channel) and enough_volume
                short=c<min(x['l'] for x in channel) and enough_volume
            elif family in ('range','martingale'):
                lo,hi=band(cs,rule['n'],rule['z']);oldlo,oldhi=band(cs[:-1],rule['n'],rule['z'])
                strength=rsi(cs,14)
                long=previous<oldlo and c>=lo and eff<=rule['er_max'] and strength<50
                short=previous>oldhi and c<=hi and eff<=rule['er_max'] and strength>50
            elif family=='pattern':
                old,older=segment[-2],segment[-3];shape=rule['shape']
                if shape=='engulf':
                    long=old['c']<old['o'] and c>b['o'] and b['o']<=old['c'] and c>=old['o']
                    short=old['c']>old['o'] and c<b['o'] and b['o']>=old['c'] and c<=old['o']
                elif shape=='pin':
                    body=abs(c-b['o']);lower=min(c,b['o'])-b['l'];upper=b['h']-max(c,b['o'])
                    long=body>0 and lower>=2*body and upper<=body
                    short=body>0 and upper>=2*body and lower<=body
                elif shape=='inside':
                    inside=old['h']<=older['h'] and old['l']>=older['l']
                    long=inside and c>old['h'];short=inside and c<old['l']
                elif shape=='three_run':
                    previous20=segment[-21:-1]
                    long=cs[-3]<cs[-2]<c and c>max(x['h'] for x in previous20)
                    short=cs[-3]>cs[-2]>c and c<min(x['l'] for x in previous20)
                elif shape=='failed_break':
                    previous20=segment[-21:-1];low=min(x['l'] for x in previous20);high=max(x['h'] for x in previous20)
                    long=b['l']<low and c>low;short=b['h']>high and c<high
                else:raise AuditError('unknown_pattern')
                if long and short:long=short=False
                long=long and c>ema48;short=short and c<ema48
            elif family=='scalp':
                now,old=rsi(cs,rule['rsi_n']),rsi(cs[:-1],rule['rsi_n'])
                last20=segment[-20:];weighted=sum(x['c']*x['v'] for x in last20)/sum(x['v'] for x in last20)
                threshold=rule['threshold']
                long=old<=threshold<now and eff<=.5 and c<weighted
                short=old>=100-threshold>now and eff<=.5 and c>weighted
            else:raise AuditError('unknown_family')
            direction=0 if long==short else 1 if long else -1
            features[opening+step]={'direction':direction,'atr_fraction':statistics.mean(trs[-14:])/c}
        out[rule['id']]=features
    return out[rules[0]['id']] if one else out

def verify(rows,spec,funding,config,start,end,signals,result,control=False):
    """Independent continuous-cash multi-trade audit; complete signal maps verified upstream."""
    product=config['product'];derivative=product=='CONDITIONAL_SWAP'
    if product not in ('SPOT','CONDITIONAL_SWAP'):raise AuditError('unknown_product')
    cost={('SPOT','base'):(.001,.0005),('SPOT','stress'):(.002,.001),
          ('CONDITIONAL_SWAP','base'):(.0005,.0005),('CONDITIONAL_SWAP','stress'):(.001,.001)}
    fee,slip=cost[product,config['cost']]
    unknown='UNKNOWN' if derivative else 'NOT_APPLICABLE'
    def invalid(reason,status='DATA_INVALID'):
        expected={'metrics':{'status':status,'target_hit':None,'final_equity':None,'return':None,
            'max_drawdown':None,'fees':None,'funding':None,'exit_reason':reason,
            'trade_count':0,'entry_count':0,'trade_pnls':[],
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
        coin=spec.get('baseCcy') or spec.get('ctValCcy') or spec['instId'].split('-')[0]
        identity=coin+'-USDT'+('-SWAP' if derivative else '')
        if spec['instId']!=identity or (config.get('coin') and config['coin']!=coin):return invalid('spec_identity','SPEC_INVALID')
        if derivative and (spec['instType']!='SWAP' or spec['ctType']!='linear' or spec['settleCcy']!='USDT'
                           or not math.isfinite(float(spec['ctVal'])) or float(spec['ctVal'])<=0):
            return invalid('nonlinear_or_missing_swap_spec','SPEC_INVALID')
        if not derivative and (spec['instType']!='SPOT' or spec.get('quoteCcy','USDT')!='USDT'):return invalid('nonspot_spec','SPEC_INVALID')
    except AuditError:raise
    except (ValueError,KeyError,TypeError):return invalid('missing_spec','SPEC_INVALID')
    if derivative:
        maximum=spec.get('lever')
        try:
            maximum=float(maximum)
        except (TypeError,ValueError):
            return invalid('current_leverage_unknown','SPEC_INVALID')
        if not math.isfinite(maximum) or maximum<=0:
            return invalid('current_leverage_unknown','SPEC_INVALID')
        if config['leverage']>maximum:
            return invalid('current_leverage_unsupported','SPEC_INVALID')
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
        except AuditError:raise
        except (ValueError,KeyError,TypeError):return invalid('missing_funding_coverage')
    family=config['rule']['family']
    stop_mult,target_mult,hold_limit={'trend':(2,4,96),'breakout':(2,4,96),
        'range':(2,1,48),'martingale':(2,1,48),'pattern':(1.5,3,48),'scalp':(0,0,8)}[family]
    hold_limit=int(config.get('hold_bars',hold_limit))
    pause=1 if family=='scalp' else 4
    entry_limit=8 if config['horizon_hours']==24 else 40
    balance=500.;dust=0.;position=None;entries=0;loss_run=0;halted=False
    pending=None;eligible_entry=start;trade_pnls=[];fee_total=funding_total=0.
    why='NO_SIGNAL';events=[];curve=[];peak=500.;dd=0.

    def base():return dust+(position['side']*position['qty'] if position else 0.)
    def contract_balance():return position['side']*position['contracts'] if position else 0.
    def event(t,kind,delta=0.,base_delta=0.,contract_delta=0.,**extra):
        events.append(dict(timestamp=t,type=kind,cash_delta=delta,base_delta=base_delta,
            contract_delta=contract_delta,cash_after=balance,base_after=base(),contracts_after=contract_balance(),**extra))
    def mark(reference):
        dusty=adverse_price(reference,-1,slip,spec['tickSz'])
        v=balance+dust*dusty*(1-fee)
        if position:
            q=position['qty'];side=position['side']
            p=adverse_price(reference,-side,slip,spec['tickSz'])
            v+=side*q*(p-position['price'])-q*p*fee if derivative else q*p*(1-fee)
        return v
    def funding_at(t,reference,terminal=False):
        nonlocal balance,funding_total
        if derivative and position and t in rates:
            amount=-position['side']*position['qty']*reference*rates[t]
            balance+=amount;funding_total+=amount;position['funding']+=amount
            event(t,'FUNDING',amount,trade_id=position['id'],rate=rates[t],reference_price=reference,
                  notional_proxy=position['qty']*reference,terminal_price_proxy=terminal)
    def liquidation_check(t,reference,phase):
        nonlocal balance,position,halted,why,pending,loss_run
        if not derivative or not position or halted:return False
        p=position;collateral=balance+p['side']*p['qty']*(reference-p['price'])
        maintenance=p['qty']*reference*.022
        if collateral>maintenance:return False
        amount=-balance;pnl=-p['initial_cash'];balance=0.;position=None;halted=True
        why='MAINTENANCE_PROXY_BREACH';pending=None;trade_pnls.append(pnl)
        loss_run=loss_run+1 if pnl<0 else 0
        event(t,'MAINTENANCE_PROXY_BREACH',amount,-p['side']*p['qty'],-p['side']*p['contracts'],
              trade_id=p['id'],trade_net_pnl=pnl,adverse_price=reference,modeled_collateral=collateral,
              maintenance_threshold=maintenance,model_equity=0.,phase=phase,true_liquidation='UNKNOWN')
        return True
    def close_position(t,reference,reason,terminal=False):
        nonlocal balance,position,dust,fee_total,why,pending,loss_run,eligible_entry,halted
        p=position;q=p['qty'];side=p['side'];px=adverse_price(reference,-side,slip,spec['tickSz'])
        if derivative:
            residual=0.;charge=q*px*fee;gross=side*q*(px-p['price']);amount=gross-charge
            pnl=p['cash_delta']+p['funding']+amount
        else:
            sold=quantize(q,spec['lotSz']);sold=0. if sold<float(spec['minSz']) else sold
            residual=q-sold;charge=sold*px*fee;gross=None;amount=sold*px*(1-fee)
            pnl=p['cash_delta']+amount+residual*px*(1-fee)
        balance+=amount;fee_total+=charge;dust+=residual;position=None;why=reason
        trade_pnls.append(pnl);loss_run=loss_run+1 if pnl<0 else 0;eligible_entry=t+pause*STEP
        if family=='martingale' and loss_run>=3:halted=True;why='MARTINGALE_THREE_LOSSES'
        event(t,'EXIT',amount,-side*(q-residual),-side*p['contracts'],price=px,
              reference_price=float(reference),fee=charge,realized_pnl=gross,trade_net_pnl=pnl,
              trade_id=p['id'],reason=reason,terminal_proxy=terminal,residual_base=residual,
              total_residual_base=dust,loss_streak=loss_run)
        pending=None
    def enter(t,reference,side,info,control_seed):
        nonlocal balance,position,fee_total,entries,why
        budget=min(.95*balance,.2*2**loss_run*mark(reference)) if family=='martingale' else .95*balance
        if derivative and config.get('risk_fraction'):
            atr=min(.05,max(.003,float(info['atr_fraction'])))
            loss_per_notional=2*atr+fee*2+slip*2+float(spec['tickSz'])*2/reference
            allowed_notional=balance*config['risk_fraction']/loss_per_notional
            budget=min(budget,allowed_notional/config['leverage']+allowed_notional*fee)
        fraction=budget/balance if balance>0 else 0.
        px=adverse_price(reference,side,slip,spec['tickSz'])
        if derivative:
            ct=float(spec['ctVal']);number=quantize(budget/(ct*px*(1/config['leverage']+fee)),spec['lotSz'])
            q=number*ct;contracts=number
        else:
            number=quantize(budget/px,spec['lotSz']);q=number*(1-fee);contracts=0.
        if number<=0 or number<float(spec['minSz']):
            event(t,'REJECTED',reason='MIN_SIZE_REJECTED',budget=budget,direction=side)
            why='MIN_SIZE_REJECTED';return
        entries+=1;charge=(q if derivative else number)*px*fee
        amount=-charge if derivative else -number*px
        position={'id':entries,'initial_cash':balance,'qty':q,'side':side,'contracts':contracts,
                  'price':px,'cash_delta':amount,'funding':0.,'bars':0,
                  'atr':min(.05,max(.003,float(info['atr_fraction'])))}
        balance+=amount;fee_total+=charge
        event(t,'ENTRY',amount,side*q,side*contracts,trade_id=entries,direction=side,
              signal_timestamp=t,price=px,reference_price=reference,quantity=number,fee=charge,
              fee_asset=number*fee if not derivative else 0.,budget=budget,allocation_fraction=fraction,
              margin=q*px/config['leverage'] if derivative else 0.,atr_fraction=position['atr'],
              loss_streak=loss_run,control_seed=control_seed)
    for t in range(start,end,STEP):
        o,h,l,c=map(float,d[t][1:5]);closed_here=False
        funding_at(t,o);liquidation_check(t,o,'OPEN_BEFORE_EXIT')
        if pending and not halted:
            reason,terminate=pending
            if position:close_position(t,o,reason);closed_here=True
            else:pending=None
            if terminate:halted=True;why=reason
        info=signals.get(t);seed=None
        if control and (t-start)%(8*HOUR)==0 and info is not None:
            material=['50020261006b',product,config['leverage'],config['horizon_hours'],coin,int(start),int(t)]
            digest=hashlib.sha256(json.dumps(material,separators=(',',':'),ensure_ascii=True).encode()).digest()
            side=1 if not derivative or digest[-1]&1 else -1;seed=digest.hex()
        else:side=0 if control or info is None else int(info['direction'])
        if (not halted and position is None and not closed_here and t>=eligible_entry and entries<entry_limit
            and side in (-1,1) and (derivative or side==1)):
            enter(t,o,side,info,seed)
        if position and not halted:liquidation_check(t+STEP,l if position['side']>0 else h,'INTRABAR_ADVERSE')
        value=mark(c);peak=max(peak,value);dd=max(dd,1-value/peak)
        curve.append(dict(timestamp=t+STEP,cash=balance,base=base(),contracts=contract_balance(),
                          equity=value,exit_cost_included=True))
        if not halted:
            if value>=650:pending=('ACCOUNT_TARGET',True)
            elif value<=0:pending=('ACCOUNT_STOP',True)
            elif position and pending is None:
                position['bars']+=1;movement=position['side']*(c/position['price']-1)
                sl,tp=(.004,.006) if family=='scalp' else (stop_mult*position['atr'],target_mult*position['atr'])
                if movement<=-sl:pending=('TRADE_STOP',False)
                elif movement>=tp:pending=('TRADE_TARGET',False)
                elif position['bars']>=hold_limit:pending=('TRADE_TIMEOUT',False)
    last=float(d[end-STEP][4])
    if position and not halted:
        funding_at(end,last,True);liquidation_check(end,last,'TERMINAL_AFTER_FUNDING')
        if position:close_position(end,last,'HORIZON_TERMINAL',True)
    final=mark(last);peak=max(peak,final);dd=max(dd,1-final/peak)
    curve[-1].update(cash=balance,base=base(),contracts=contract_balance(),equity=final)
    expected={'metrics':dict(status='VALID' if entries else 'NO_TRADE',target_hit=final>=650,
        final_equity=final,**{'return':final/500-1},max_drawdown=dd,fees=fee_total,funding=funding_total,
        exit_reason=why,initial=500.,trade_count=len(trade_pnls),entry_count=entries,trade_pnls=trade_pnls,
        loss_streak=loss_run,halted=halted,terminal_residual_base=dust,true_target=unknown,
        true_liquidation=unknown,real_execution_validation='UNKNOWN',current_specs_historical_validity='UNKNOWN'),
        'events':events,'equity':curve}
    compare(result,expected)
    return {'ok':True,'errors':[],'status':'PASS','coverage':'independent_multi_trade_15m_full_ledger',
            'entry_count':entries,'trade_count':len(trade_pnls),'independent_final_equity':final,
            'true_target':unknown,'true_liquidation':unknown}
