"""Causal contraction hypotheses, not an original SEPA reproduction."""
import statistics

def build(bars, baseline, mode, n=12):
    out={};fast=slow=None;segment=[]
    for b in bars:
        if not b['valid']:
            fast=slow=None;segment=[];continue
        fast=b['c'] if fast is None else fast+2/13*(b['c']-fast)
        slow=b['c'] if slow is None else slow+2/49*(b['c']-slow)
        segment.append(b);t=b['t']
        if t not in baseline:continue
        item=dict(baseline[t]);direction=item['direction']
        if mode=='baseline':out[t]=item;continue
        # Exclude current trigger candle from both contraction windows.
        if len(segment)<2*n+1:item['direction']=0;out[t]=item;continue
        older=segment[-2*n-1:-n-1];recent=segment[-n-1:-1]
        old_range=max(x['h'] for x in older)-min(x['l'] for x in older)
        recent_range=max(x['h'] for x in recent)-min(x['l'] for x in recent)
        contraction=old_range>0 and recent_range<=.75*old_range and statistics.mean(x['v'] for x in recent)<=statistics.mean(x['v'] for x in older)
        if mode=='filter':direction=direction if contraction else 0
        elif mode=='breakout':
            long=contraction and fast>slow and b['c']>max(x['h'] for x in recent)
            short=contraction and fast<slow and b['c']<min(x['l'] for x in recent)
            direction=1 if long else -1 if short else 0
        else:raise ValueError(mode)
        item['direction']=direction;out[t]=item
    return out
