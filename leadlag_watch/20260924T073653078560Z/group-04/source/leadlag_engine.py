"""Causal public-book lead/lag event study; no orders or account access."""
from collections import deque, Counter
from decimal import Decimal as D
from detector import validate_books, spend, sell

PARAMETERS = dict(lookback_seconds=2, leader_jump_bps=20, lag_gap_bps=15,
                  entry_delay_seconds=1, exit_horizons_seconds=[1,3,10,30],
                  cooldown_seconds=35, max_schedule_lateness_seconds=.5,
                  buffer_bps=5, amounts_usdt=['100','250','500'])

class Study:
    def __init__(self, config):
        self.config=config; self.history={}; self.pending=[]; self.cooldown={}; self.serial=0
        self.counts=Counter(); self.latest=[]

    def step(self, views, now, mono):
        events=[]; self.latest=[]
        for job in list(self.pending):
            if mono<job['due']:continue
            self.pending.remove(job)
            s,v=job['symbol'],job['venue']; b=views[v][s]
            quality=validate_books(b,b,now,mono)['status']
            if mono-job['due']>.5:quality='SCHEDULE_LATE'
            if b['connection_id']!=job['connection_id']:quality='CONNECTION_CHANGED'
            if b['ref']==job['ref']:quality='NO_NEW_MESSAGE'
            common={k:job[k] for k in ['event_id','symbol','leader','venue']}
            common.update(observed_ms=now,actual_delay_seconds=mono-job['origin'],book_ref=b['ref'],quality=quality)
            if job['stage']=='entry':
                entries=[]
                if quality=='VALID':
                    rule=self.config['order_rules'][v][s]
                    for amount in PARAMETERS['amounts_usdt']:
                        for fee in ([10,20] if v=='gate' else [10]):
                            budget=D(amount); f=D(fee)/10000; qty=spend(b['asks'],budget/(1+f))
                            state='ESTIMATE_ONLY'
                            if qty is None:state='INSUFFICIENT_DEPTH'
                            else:
                                qty=qty//D(rule['lot'])*D(rule['lot']);cost=sell(b['asks'],qty)
                                if qty<=0 or qty<D(rule['min_qty']) or cost<D(rule['min_quote']) or (rule.get('max_qty') and qty>D(rule['max_qty'])) or (rule.get('max_quote') and cost>D(rule['max_quote'])):state='ORDER_CONSTRAINT'
                            entry=dict(amount_usdt=amount,fee_bps=fee,status=state)
                            if state=='ESTIMATE_ONLY':entry.update(quantity=str(qty),cost_usdt=str(cost),entry_fee_usdt=str(cost*f))
                            entries.append(entry)
                    for horizon in PARAMETERS['exit_horizons_seconds']:
                        self.pending.append(dict(job,stage='exit',due=mono+horizon,origin=mono,ref=b['ref'],entries=entries,horizon=horizon))
                events.append(dict(common,event='entry_observation',scenarios=entries))
            else:
                results=[]
                for entry in job['entries']:
                    out=dict(entry)
                    if quality!='VALID':out['status']=quality
                    elif entry['status']=='ESTIMATE_ONLY':
                        qty=D(entry['quantity']);revenue=sell(b['bids'],qty)
                        if revenue is None:out['status']='INSUFFICIENT_DEPTH'
                        elif revenue<D(self.config['order_rules'][v][s]['min_quote']):out['status']='ORDER_CONSTRAINT'
                        else:
                            cost=D(entry['cost_usdt']);fees=D(entry['entry_fee_usdt'])+revenue*D(entry['fee_bps'])/10000
                            net=revenue-cost-fees-cost*D(PARAMETERS['buffer_bps'])/10000
                            out.update(net_usdt=str(net),exit_revenue_usdt=str(revenue),total_fees_usdt=str(fees))
                    results.append(out)
                events.append(dict(common,event='outcome',horizon_seconds=job['horizon'],scenarios=results))
        for s in self.config['symbols']:
            pair=[views[v][s] for v in ['okx','gate']]; quality=validate_books(*pair,now,mono)['status']
            self.counts[quality]+=1
            missing=sum(not b['ref'] for b in pair)
            self.latest.append(dict(symbol=s,quality=quality,unreceived=missing))
            if quality!='VALID':continue
            mids={v:(views[v][s]['asks'][0][0]+views[v][s]['bids'][0][0])/2 for v in ['okx','gate']}
            refs=tuple(b['ref'] for b in pair); conns=tuple(b['connection_id'] for b in pair)
            h=self.history.setdefault(s,deque())
            if h and h[-1][3]!=conns:h.clear()
            while h and mono-h[0][0]>3:h.popleft()
            old=next((a for a in reversed(h) if mono-a[0]>=2),None)
            if old and mono-old[0]<=2.5 and all(a!=b for a,b in zip(refs,old[2])):
                moves={v:float((mids[v]/old[1][v]-1)*10000) for v in mids}
                for leader,venue in [('okx','gate'),('gate','okx')]:
                    key=(s,venue)
                    if moves[leader]>=20 and moves[leader]-moves[venue]>=15 and mono>=self.cooldown.get(key,0):
                        self.serial+=1; self.cooldown[key]=mono+35
                        event=dict(event='lead_signal',event_id=self.serial,symbol=s,leader=leader,venue=venue,observed_ms=now,moves_bps=moves,book_refs=refs,baseline_refs=old[2],qualification='UNKNOWN',classification='RESEARCH_ONLY')
                        events.append(event); b=views[venue][s]
                        self.pending.append(dict(stage='entry',event_id=self.serial,symbol=s,leader=leader,venue=venue,due=mono+1,origin=mono,ref=b['ref'],connection_id=b['connection_id']))
            h.append((mono,mids,refs,conns))
        for event in events:self.counts[event['event']]+=1
        return events
