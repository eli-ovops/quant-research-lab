"""Separate indexed implementation of the registered contraction formula."""
def build(bars,base,mode,n):
    result={};segment=[]
    for b in bars:
        if not b['valid']:segment=[];continue
        segment.append(b);t=b['t']
        if t not in base:continue
        z=dict(base[t]);k=len(segment)-1
        if mode=='baseline':result[t]=z;continue
        if k<2*n:z['direction']=0;result[t]=z;continue
        a=[segment[j] for j in range(k-2*n,k-n)];bfr=[segment[j] for j in range(k-n,k)]
        span=lambda x:max(v['h'] for v in x)-min(v['l'] for v in x)
        ok=span(a)>0 and span(bfr)<=span(a)*.75 and sum(x['v'] for x in bfr)<=sum(x['v'] for x in a)
        if mode=='filter':z['direction']=z['direction'] if ok else 0
        else:
            # closed-form EMA from start of the valid segment, no future prices
            def ema(period):
                decay=1-2/(period+1)
                return segment[0]['c']*decay**k+sum((1-decay)*segment[j]['c']*decay**(k-j) for j in range(max(1,k-1500),k+1))
            fast,slow=ema(12),ema(48);c=segment[k]['c']
            z['direction']=1 if ok and fast>slow and c>max(x['h'] for x in bfr) else -1 if ok and fast<slow and c<min(x['l'] for x in bfr) else 0
        result[t]=z
    return result
