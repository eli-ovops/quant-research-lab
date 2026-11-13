"""Prior breakout confirmation; close decision and next-open fill remain separate."""
H=3600000
def build(bars,raw,kind,n):
    by={b['t']:b for b in bars if b['valid']};out={t:dict(z,direction=0) for t,z in raw.items()};next_allowed=0
    for t in sorted(raw):
        if t<next_allowed:continue
        d=0
        if kind=='direct':d=raw[t]['direction']
        else:
            for lag in ([1] if kind=='confirm' else [1,2,3,4]):
                p=t-lag*H;direction=raw.get(p,{}).get('direction',0)
                if not direction or any(p+j*H not in by for j in range(lag+1)):continue
                prior=[by.get(p-j*H) for j in range(1,n+1)]
                if any(x is None for x in prior):continue
                pivot=max(x['h'] for x in prior) if direction==1 else min(x['l'] for x in prior)
                b=by[t]
                if kind=='confirm':ok=direction*(b['c']-by[p]['c'])>0
                else:
                    # Intermediate closes must not have invalidated breakout.
                    ok=all(direction*(by[p+j*H]['c']-pivot)>0 for j in range(1,lag)) and b['l']<=pivot<=b['h'] and direction*(b['c']-pivot)>0
                if ok:d=direction;break
        out[t]['direction']=d
        if d:next_allowed=t+6*H
    return out

def audit(bars,raw,kind,n):
    by={b['t']:b for b in bars if b['valid']};candidates={}
    for p,z in raw.items():
        side=z['direction']
        if not side:continue
        if kind=='direct':candidates.setdefault(p,[]).append((0,side));continue
        pp=[by.get(p-j*H) for j in range(1,n+1)]
        if any(b is None for b in pp):continue
        pivot=(max(b['h'] for b in pp) if side>0 else min(b['l'] for b in pp))
        for lag in ([1] if kind=='confirm' else range(1,5)):
            t=p+lag*H
            if t not in raw or any(p+j*H not in by for j in range(lag+1)):continue
            b=by[t]
            valid=(side*(b['c']-by[p]['c'])>0) if kind=='confirm' else (all(side*(by[q]['c']-pivot)>0 for q in range(p+H,t,H)) and b['l']<=pivot<=b['h'] and side*(b['c']-pivot)>0)
            if valid:candidates.setdefault(t,[]).append((lag,side))
    result={};last=None
    for t,z in sorted(raw.items()):
        d=sorted(candidates.get(t,[]))[0][1] if t in candidates and (last is None or t-last>=6*H) else 0
        if d:last=t
        result[t]=dict(z,direction=d)
    return result
