"""Frozen multi-trade independent 500-USDT account research. No network or orders.

Events expose cash and base/contract changes for independent replay. SWAP is
linear contract accounting with explicit realized funding, not scaled spot PnL.
OHLC maintenance breach and terminal liquidation remain research proxies.
"""
import hashlib
import json
import math
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from statistics import mean, pstdev

QUARTER = 900_000
HOUR = 3_600_000
INITIAL = 500.0
TARGET = 650.0
STOP = 0.0
WARMUP = 120
COSTS = {'SPOT': {'base': (.001, .0005), 'stress': (.002, .001)},
         'CONDITIONAL_SWAP': {'base': (.0005, .0005), 'stress': (.001, .001)}}


def rounded(value, increment, upward=False):
    step = Decimal(str(increment))
    if not step.is_finite() or step <= 0:
        raise ValueError('invalid_increment')
    n = (Decimal(str(value)) / step).to_integral_value(
        rounding=ROUND_CEILING if upward else ROUND_FLOOR)
    return float(n * step)


def adverse_price(reference, side, slip, tick):
    adjusted = Decimal(str(reference)) * (1 + Decimal(str(slip)) if side == 'buy' else 1 - Decimal(str(slip)))
    return rounded(adjusted, tick, side == 'buy')


def prepare_rows(rows):
    """Snapshot and validate once per instrument; reuse across episode calls."""
    indexed, invalid = _indexed(rows)
    first=min(indexed)//QUARTER*QUARTER if indexed else 0
    last=(max(indexed)//QUARTER+1)*QUARTER if indexed else 0
    prefix=[0]
    for t in range(first,last,QUARTER):
        prefix.append(prefix[-1]+int(t not in indexed or t in invalid))
    return {'kind':'prepared_15m','indexed':indexed,'invalid':invalid,
            'first':first,'last':last,'prefix':prefix}


def _indexed(rows):
    if isinstance(rows, dict) and rows.get('kind') == 'prepared_15m':
        return rows['indexed'], rows['invalid']
    indexed, invalid = {}, set()
    for r in rows:
        try:
            t = int(r[0])
            valid = len(r) == 9 and str(r[8]) == '1' and t % QUARTER == 0
            values = list(map(float, r[1:8]))
            o,h,l,c,v = values[:5]
            valid = valid and all(math.isfinite(x) for x in values)
            valid = valid and 0 < l <= min(o,c) <= max(o,c) <= h and v > 0 and min(values[5:]) >= 0
            if t in indexed and indexed[t] != list(r):
                valid = False
            indexed[t] = list(r)
            if not valid:
                invalid.add(t)
        except (ValueError, TypeError, IndexError):
            # Unlocatable malformed rows make the dataset unsafe, not silently
            # ignored. Sentinel is recognized by both signal and episode gates.
            invalid.add(None)
    return indexed, invalid


def _hourly(rows):
    indexed, invalid = _indexed(rows)
    if None in invalid:
        return []
    if not indexed:
        return []
    bars = []
    for t in range(min(indexed)//HOUR*HOUR, max(indexed)//HOUR*HOUR+HOUR, HOUR):
        keys = [t+k*QUARTER for k in range(4)]
        if any(k not in indexed or k in invalid for k in keys):
            bars.append({'t':t+HOUR, 'valid':False})
            continue
        rs = [indexed[k] for k in keys]
        bars.append({'t':t+HOUR, 'valid':True, 'o':float(rs[0][1]),
                     'h':max(float(r[2]) for r in rs), 'l':min(float(r[3]) for r in rs),
                     'c':float(rs[-1][4]),'v':sum(float(r[5]) for r in rs)})
    return bars


def _rsi(closes, n):
    differences = [b-a for a,b in zip(closes[-n-1:], closes[-n:])]
    gains = mean(max(d,0) for d in differences)
    losses = mean(max(-d,0) for d in differences)
    return 100.0 if losses == 0 and gains > 0 else 50.0 if gains == losses == 0 else 100-100/(1+gains/losses)


def _band(closes, n, z):
    v = closes[-n:]
    mu, sigma = mean(v), pstdev(v)
    return mu-z*sigma, mu+z*sigma


def _er(closes, n=20):
    values=closes[-n-1:]
    path=sum(abs(b-a) for a,b in zip(values,values[1:]))
    return abs(values[-1]-values[0])/path if path else 0.0


def prepare_signals(rows,rule):
    """All eligible boundaries -> direction(-1/0/+1), closed-bar ATR fraction.

    Zero directions are retained for scheduled controls. Non-scalp uses UTC
    hourly closes, scalp uses 15m closes, each with 120h valid warmup including
    current closed bar. No future open/close influences a feature.
    """
    family=rule['family']
    if family=='scalp':
        d,bad=_indexed(rows)
        if not d or None in bad:return {}
        bars=[]
        for t in range(min(d)//QUARTER*QUARTER,max(d)//QUARTER*QUARTER+QUARTER,QUARTER):
            if t not in d or t in bad:bars.append({'t':t+QUARTER,'valid':False});continue
            r=d[t]
            bars.append(dict(t=t+QUARTER,valid=True,o=float(r[1]),h=float(r[2]),l=float(r[3]),c=float(r[4]),v=float(r[5])))
        warmup=480
    else:
        bars=_hourly(rows);warmup=120
    output={};segment=[];closes=[];ranges=[];fast=slow=ema48=None
    for bar in bars:
        if not bar['valid']:
            segment=[];closes=[];ranges=[];fast=slow=ema48=None
            continue
        previous_close=closes[-1] if closes else bar['c']
        ranges.append(max(bar['h']-bar['l'],abs(bar['h']-previous_close),abs(bar['l']-previous_close)))
        segment.append(bar);closes.append(bar['c'])
        pf,ps=fast,slow
        if family=='trend':
            fast=bar['c'] if fast is None else fast+2/(rule['fast']+1)*(bar['c']-fast)
            slow=bar['c'] if slow is None else slow+2/(rule['slow']+1)*(bar['c']-slow)
        ema48=bar['c'] if ema48 is None else ema48+2/49*(bar['c']-ema48)
        if len(segment)<warmup:continue
        c,p=closes[-1],closes[-2];long=short=False
        er=_er(closes)
        if family=='trend':
            long=pf<=ps and fast>slow and er>=rule['er_min']
            short=pf>=ps and fast<slow and er>=rule['er_min']
        elif family=='breakout':
            prev=segment[-rule['n']-1:-1]
            volume_ok=bar['v']>=rule['volume_multiple']*mean(b['v'] for b in segment[-21:-1])
            long=c>max(b['h'] for b in prev) and volume_ok
            short=c<min(b['l'] for b in prev) and volume_ok
        elif family in ('range','martingale'):
            lower,upper=_band(closes,rule['n'],rule['z'])
            plower,pupper=_band(closes[:-1],rule['n'],rule['z'])
            rsi=_rsi(closes,14)
            long=p<plower and c>=lower and er<=rule['er_max'] and rsi<50
            short=p>pupper and c<=upper and er<=rule['er_max'] and rsi>50
        elif family=='pattern':
            old,older=segment[-2],segment[-3];shape=rule['shape']
            if shape=='engulf':
                long=old['c']<old['o'] and c>bar['o'] and bar['o']<=old['c'] and c>=old['o']
                short=old['c']>old['o'] and c<bar['o'] and bar['o']>=old['c'] and c<=old['o']
            elif shape=='pin':
                body=abs(c-bar['o']);low_wick=min(c,bar['o'])-bar['l'];high_wick=bar['h']-max(c,bar['o'])
                long=body>0 and low_wick>=2*body and high_wick<=body
                short=body>0 and high_wick>=2*body and low_wick<=body
            elif shape=='inside':
                inside=old['h']<=older['h'] and old['l']>=older['l']
                long=inside and c>old['h'];short=inside and c<old['l']
            elif shape=='three_run':
                prior=segment[-21:-1]
                long=closes[-3]<closes[-2]<c and c>max(b['h'] for b in prior)
                short=closes[-3]>closes[-2]>c and c<min(b['l'] for b in prior)
            elif shape=='failed_break':
                prior=segment[-21:-1];low=min(b['l'] for b in prior);high=max(b['h'] for b in prior)
                long=bar['l']<low and c>low;short=bar['h']>high and c<high
            else:raise ValueError('unknown_pattern')
            # Simultaneous raw pattern sides never become a signal via filtering.
            if long and short:long=short=False
            long=long and c>ema48;short=short and c<ema48
        elif family=='scalp':
            rsi,old_rsi=_rsi(closes,rule['rsi_n']),_rsi(closes[:-1],rule['rsi_n'])
            window=segment[-20:];vw=sum(b['c']*b['v'] for b in window)/sum(b['v'] for b in window)
            threshold=rule['threshold']
            long=old_rsi<=threshold<rsi and er<=.5 and c<vw
            short=old_rsi>=100-threshold>rsi and er<=.5 and c>vw
        else:raise ValueError('unknown_rule_family')
        direction=0 if long==short else 1 if long else -1
        output[bar['t']]={'direction':direction,'atr_fraction':mean(ranges[-14:])/c}
    return output


def _control_direction(spec,config,start,t):
    coin=spec.get('baseCcy') or spec.get('ctValCcy') or spec['instId'].split('-')[0]
    material=['50020261006b',config['product'],config['leverage'],config['horizon_hours'],coin,int(start),int(t)]
    digest=hashlib.sha256(json.dumps(material,separators=(',',':'),ensure_ascii=True).encode()).digest()
    return (1 if config['product']=='SPOT' or digest[-1]&1 else -1),digest.hex()


def simulate(rows,spec,funding,config,start,end,signals,control=False):
    """Continuous-cash multi-trade episode. No fills from intra-bar targets.

    trade_count counts closed economic trades, including maintenance writeoff.
    Spot lot residuals persist separately from the sole active trade. Net trade
    PnL includes fees, its funding and mark of its newly-created spot residual.
    """
    product=config['product'];derivative=product=='CONDITIONAL_SWAP'
    family=config['rule']['family'];fee,slip=COSTS[product][config['cost']]
    unknown='UNKNOWN' if derivative else 'NOT_APPLICABLE'
    def invalid(reason,status='DATA_INVALID'):
        return {'metrics':dict(status=status,target_hit=None,final_equity=None,**{'return':None},max_drawdown=None,
                               fees=None,funding=None,exit_reason=reason,initial=500.,trade_count=0,entry_count=0,
                               trade_pnls=[],true_target=unknown,true_liquidation=unknown,
                               real_execution_validation='UNKNOWN'),'events':[],'equity':[]}
    prepared=rows if isinstance(rows,dict) and rows.get('kind')=='prepared_15m' else prepare_rows(rows)
    d,bad=prepared['indexed'],prepared['invalid']
    if start%HOUR or end%QUARTER or end<=start or end-start!=config['horizon_hours']*HOUR:
        return invalid('invalid_episode_bounds')
    first,last=prepared['first'],prepared['last'];lo=start-120*HOUR
    if None in bad or lo<first or end>last:
        return invalid('missing_zero_unconfirmed_or_invalid_candle')
    prefix=prepared['prefix']
    if prefix[(end-first)//QUARTER]!=prefix[(lo-first)//QUARTER]:
        return invalid('missing_zero_unconfirmed_or_invalid_candle')
    try:
        for field in ('tickSz','lotSz','minSz'):
            if not math.isfinite(float(spec[field])) or float(spec[field])<=0:return invalid('invalid_'+field,'SPEC_INVALID')
        coin=spec.get('baseCcy') or spec.get('ctValCcy') or spec['instId'].split('-')[0]
        expected=coin+'-USDT'+('-SWAP' if derivative else '')
        if spec['instId']!=expected or (config.get('coin') and config['coin']!=coin):return invalid('spec_identity','SPEC_INVALID')
        if derivative and (spec['instType']!='SWAP' or spec['ctType']!='linear' or spec['settleCcy']!='USDT' or
                           not math.isfinite(float(spec['ctVal'])) or float(spec['ctVal'])<=0):
            return invalid('nonlinear_or_missing_swap_spec','SPEC_INVALID')
        if derivative:
            try:
                current_max=float(spec['lever'])
            except (ValueError,KeyError,TypeError):
                return invalid('current_leverage_unknown','SPEC_INVALID')
            if not math.isfinite(current_max) or current_max<=0:
                return invalid('current_leverage_unknown','SPEC_INVALID')
            if current_max<config['leverage']:
                return invalid('current_leverage_unsupported','SPEC_INVALID')
        if not derivative and (spec['instType']!='SPOT' or spec.get('quoteCcy','USDT')!='USDT'):
            return invalid('nonspot_spec','SPEC_INVALID')
    except (ValueError,KeyError,TypeError):return invalid('missing_spec','SPEC_INVALID')
    rates={}
    if derivative:
        try:
            for f in funding:
                t=int(f['fundingTime'])
                if not start-8*HOUR<=t<=end+8*HOUR:continue
                rate=float(f['realizedRate'])
                if t%QUARTER or not math.isfinite(rate):return invalid('invalid_funding')
                if t in rates and rates[t]!=rate:return invalid('conflicting_funding')
                rates[t]=rate
            times=sorted(rates);left=max(t for t in times if t<=start);right=min(t for t in times if t>=end)
            covered=[t for t in times if left<=t<=right]
            if any(b-a>8*HOUR for a,b in zip(covered,covered[1:])):return invalid('funding_gap')
        except (ValueError,KeyError,TypeError):return invalid('missing_funding_coverage')
    sl_mult,tp_mult,max_hold={'trend':(2,4,96),'breakout':(2,4,96),'range':(2,1,48),
                             'martingale':(2,1,48),'pattern':(1.5,3,48),'scalp':(0,0,8)}[family]
    cooldown=1 if family=='scalp' else 4
    max_entries=8 if config['horizon_hours']==24 else 40
    cash=500.;qty=contracts=dust=0.;side=0;entry_px=None
    entry_count=0;trade_pnls=[];loss_streak=0;halted=False;pending=None;next_entry=start
    trade_id=None;trade_cash_delta=trade_funding=0.;trade_start_cash=0.;hold_bars=0
    entry_atr=None;fees=fund_total=0.;reason='NO_SIGNAL';events=[];curve=[];peak=500.;dd=0.

    def total_base():return side*qty+dust
    def event(t,kind,delta=0.,base_delta=0.,contract_delta=0.,**extra):
        events.append(dict(timestamp=t,type=kind,cash_delta=delta,base_delta=base_delta,contract_delta=contract_delta,
                           cash_after=cash,base_after=total_base(),contracts_after=side*contracts,**extra))
    def mark(reference):
        dust_price=adverse_price(reference,'sell',slip,spec['tickSz'])
        value=cash+dust*dust_price*(1-fee)
        if qty:
            px=adverse_price(reference,'sell' if side>0 else 'buy',slip,spec['tickSz'])
            value+=side*qty*(px-entry_px)-qty*px*fee if derivative else qty*px*(1-fee)
        return value
    def apply_funding(t,reference,terminal=False):
        nonlocal cash,fund_total,trade_funding
        if derivative and qty and t in rates:
            delta=-side*qty*reference*rates[t];cash+=delta;fund_total+=delta;trade_funding+=delta
            event(t,'FUNDING',delta,trade_id=trade_id,rate=rates[t],reference_price=reference,
                  notional_proxy=qty*reference,terminal_price_proxy=terminal)
    def finish_trade(t,pnl):
        nonlocal loss_streak,next_entry,halted,reason
        trade_pnls.append(pnl)
        loss_streak=loss_streak+1 if pnl<0 else 0
        next_entry=t+cooldown*QUARTER
        if family=='martingale' and loss_streak>=3:
            halted=True;reason='MARTINGALE_THREE_LOSSES'
    def close_trade(t,reference,why,terminal=False):
        nonlocal cash,qty,contracts,dust,side,fees,reason,pending
        old_qty,old_contracts,old_side=qty,contracts,side
        px=adverse_price(reference,'sell' if side>0 else 'buy',slip,spec['tickSz'])
        if derivative:
            charge=qty*px*fee;gross=side*qty*(px-entry_px);delta=gross-charge;residual=0.
            pnl=trade_cash_delta+trade_funding+delta
        else:
            sold=rounded(qty,spec['lotSz']);sold=0. if sold<float(spec['minSz']) else sold
            residual=qty-sold;charge=sold*px*fee;delta=sold*px*(1-fee);gross=None
            pnl=trade_cash_delta+delta+residual*px*(1-fee)
        cash+=delta;fees+=charge;dust+=residual;qty=contracts=0.;side=0;reason=why
        finish_trade(t,pnl)
        event(t,'EXIT',delta,-old_side*(old_qty-residual),-old_side*old_contracts,
              price=px,reference_price=float(reference),fee=charge,realized_pnl=gross,
              trade_net_pnl=pnl,trade_id=trade_id,reason=why,terminal_proxy=terminal,
              residual_base=residual,total_residual_base=dust,loss_streak=loss_streak)
        pending=None
    def breach(t,reference,phase):
        nonlocal cash,qty,contracts,side,halted,reason,pending,loss_streak
        if not derivative or not qty or halted:return False
        collateral=cash+side*qty*(reference-entry_px);threshold=qty*reference*.022
        if collateral>threshold:return False
        old_qty,old_contracts,old_side=qty,contracts,side
        delta=-cash;pnl=-trade_start_cash
        cash=0.;qty=contracts=0.;side=0;halted=True;reason='MAINTENANCE_PROXY_BREACH';pending=None
        trade_pnls.append(pnl)
        loss_streak=loss_streak+1 if pnl<0 else 0
        event(t,'MAINTENANCE_PROXY_BREACH',delta,-old_side*old_qty,-old_side*old_contracts,
              trade_id=trade_id,trade_net_pnl=pnl,adverse_price=reference,modeled_collateral=collateral,
              maintenance_threshold=threshold,model_equity=0.,phase=phase,true_liquidation='UNKNOWN')
        return True
    for t in range(start,end,QUARTER):
        o,h,l,c=map(float,d[t][1:5]);exited_here=False
        apply_funding(t,o);breach(t,o,'OPEN_BEFORE_EXIT')
        if pending and not halted:
            why,terminate=pending
            if qty:close_trade(t,o,why);exited_here=True
            else:pending=None
            if terminate:halted=True;reason=why
        info=signals.get(t)
        control_seed=None
        if control and (t-start)%(8*HOUR)==0 and info is not None:
            direction,control_seed=_control_direction(spec,config,start,t)
        else:direction=0 if control or info is None else int(info['direction'])
        if (not halted and not qty and not exited_here and t>=next_entry and entry_count<max_entries
            and direction in (-1,1) and (derivative or direction==1)):
            budget=min(.95*cash,.2*2**loss_streak*mark(o)) if family=='martingale' else .95*cash
            fraction=budget/cash if cash>0 else 0.
            px=adverse_price(o,'buy' if direction>0 else 'sell',slip,spec['tickSz'])
            if derivative:
                ct=float(spec['ctVal']);number=rounded(budget/(ct*px*(1/config['leverage']+fee)),spec['lotSz']);new_qty=number*ct
            else:number=rounded(budget/px,spec['lotSz']);new_qty=number*(1-fee)
            if number<=0 or number<float(spec['minSz']):
                event(t,'REJECTED',reason='MIN_SIZE_REJECTED',budget=budget,direction=direction)
                reason='MIN_SIZE_REJECTED'
            else:
                trade_start_cash=cash;entry_count+=1;trade_id=entry_count;side=direction;qty=new_qty
                contracts=number if derivative else 0.;entry_px=px;hold_bars=0
                entry_atr=min(.05,max(.003,float(info['atr_fraction'])))
                charge=qty*px*fee if derivative else number*px*fee
                delta=-charge if derivative else -number*px
                cash+=delta;fees+=charge;trade_cash_delta=delta;trade_funding=0.
                event(t,'ENTRY',delta,side*qty,side*contracts,trade_id=trade_id,direction=side,
                      signal_timestamp=t,price=px,reference_price=o,quantity=number,fee=charge,
                      fee_asset=number*fee if not derivative else 0.,budget=budget,allocation_fraction=fraction,
                      margin=qty*px/config['leverage'] if derivative else 0.,atr_fraction=entry_atr,
                      loss_streak=loss_streak,control_seed=control_seed)
        if qty and not halted:breach(t+QUARTER,l if side>0 else h,'INTRABAR_ADVERSE')
        value=mark(c);peak=max(peak,value);dd=max(dd,1-value/peak)
        curve.append(dict(timestamp=t+QUARTER,cash=cash,base=total_base(),contracts=side*contracts,
                          equity=value,exit_cost_included=True))
        if not halted:
            if value>=650:pending=('ACCOUNT_TARGET',True)
            elif value<=0:pending=('ACCOUNT_STOP',True)
            elif qty and pending is None:
                hold_bars+=1
                movement=side*(c/entry_px-1)
                sl,tp=(.004,.006) if family=='scalp' else (sl_mult*entry_atr,tp_mult*entry_atr)
                if movement<=-sl:pending=('TRADE_STOP',False)
                elif movement>=tp:pending=('TRADE_TARGET',False)
                elif hold_bars>=max_hold:pending=('TRADE_TIMEOUT',False)
    last_close=float(d[end-QUARTER][4])
    if qty and not halted:
        apply_funding(end,last_close,True);breach(end,last_close,'TERMINAL_AFTER_FUNDING')
        if qty:close_trade(end,last_close,'HORIZON_TERMINAL',True)
    final=mark(last_close);peak=max(peak,final);dd=max(dd,1-final/peak)
    curve[-1].update(cash=cash,base=total_base(),contracts=side*contracts,equity=final)
    status='VALID' if entry_count else 'NO_TRADE'
    return {'metrics':dict(status=status,target_hit=final>=650,final_equity=final,**{'return':final/500-1},
                           max_drawdown=dd,fees=fees,funding=fund_total,exit_reason=reason,initial=500.,
                           trade_count=len(trade_pnls),entry_count=entry_count,trade_pnls=trade_pnls,
                           loss_streak=loss_streak,halted=halted,terminal_residual_base=dust,
                           true_target=unknown,true_liquidation=unknown,real_execution_validation='UNKNOWN',
                           current_specs_historical_validity='UNKNOWN'),'events':events,'equity':curve}
