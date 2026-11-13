"""Cross-sectional rank using only fully closed hourly candles."""
def ranks(hourly,hours):
    closes={coin:{b['t']:b['c'] for b in bars if b['valid']} for coin,bars in hourly.items()};out={}
    times=sorted(set.intersection(*(set(v) for v in closes.values())))
    for t in times:
        before=t-hours*3600000
        if any(before not in v for v in closes.values()):continue
        values={c:v[t]/v[before]-1 for c,v in closes.items()}
        ordered=sorted(values,key=lambda c:(values[c],c))
        # Independently verify ordering with pairwise rank count.
        for i,c in enumerate(ordered):assert i==sum((values[o],o)<(values[c],c) for o in values)
        out[t]={c:i for i,c in enumerate(ordered)}
    return out

def apply(sig,rank,coin,keep,total=20):
    result={}
    for t,z in sig.items():
        d=z['direction'];r=rank.get(t,{}).get(coin)
        allowed=r is not None and (d==1 and r>=total-keep or d==-1 and r<keep)
        result[t]=dict(z,direction=d if allowed else 0)
    return result
