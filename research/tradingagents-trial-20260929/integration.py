"""Offline TradingAgents research adapter; no model/credential/order access.

prepare: validated public daily candles -> immutable research packet.
accept: native final_state + receipt -> normalized, non-executable opinion.
"""
import argparse
import hashlib
import json
import math
import time
from datetime import datetime
from pathlib import Path

DAY = 86400000

def strict(text):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d: raise ValueError('DUPLICATE_KEY')
            d[k] = v
        return d
    def bad(_): raise ValueError('NONFINITE_JSON')
    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad)

def digest(data): return hashlib.sha256(data).hexdigest()

def closed_rows(raw, asof):
    rows = sorted((r for r in raw['data'] if len(r) == 9 and r[8] == '1'), key=lambda r: int(r[0]))
    if len(rows) < 60: raise ValueError('INSUFFICIENT_WARMUP')
    stamps = [int(r[0]) for r in rows]
    if any(b-a != DAY for a,b in zip(stamps,stamps[1:])): raise ValueError('GAP_OR_DUPLICATE')
    if not 0 <= asof-stamps[-1]-DAY < DAY: raise ValueError('FUTURE_OR_STALE_CANDLE')
    for r in rows:
        o,h,l,c,v = map(float,r[1:6])
        if not all(math.isfinite(x) for x in (o,h,l,c,v)): raise ValueError('NONFINITE_CANDLE')
        if min(o,h,l,c)<=0 or v<0 or l>min(o,c) or h<max(o,c): raise ValueError('INVALID_OHLCV')
    return rows

def prepare(source, asof):
    import pandas as pd
    import importlib.metadata
    from tradingagents.dataflows.vendors.yahoo import market
    raw_bytes=Path(source).read_bytes();raw=strict(raw_bytes)
    request_ms=int(datetime.fromisoformat(raw['requestTime'].replace('Z','+00:00')).timestamp()*1000)
    if not 0 <= asof-request_ms <= 600000:raise ValueError('STALE_SOURCE_RECEIPT')
    rows=closed_rows(raw,asof)
    frame=pd.DataFrame({'Date':pd.to_datetime([int(r[0]) for r in rows],unit='ms',utc=True).tz_localize(None),
                       **{name:[float(r[i]) for r in rows] for i,name in enumerate(['Open','High','Low','Close','Volume'],1)}})
    date=frame['Date'].iloc[-1].strftime('%Y-%m-%d')
    original=market.load_ohlcv
    def local_loader(symbol, end):
        if symbol!='ETH-USDT-SWAP' or end!=date:raise ValueError('INPUT_SCOPE')
        return frame.copy(deep=True)
    try:
        market.load_ohlcv=local_loader
        indicators={k:float(market.get_stockstats_indicator('ETH-USDT-SWAP',k,date)) for k in ['close_50_sma','close_10_ema','rsi','macd','atr']}
    finally:market.load_ohlcv=original
    if not all(math.isfinite(x) for x in indicators.values()):raise ValueError('INVALID_INDICATOR')
    return dict(schema=1,scope='RESEARCH_ONLY',instrument='ETH-USDT-SWAP',timeframe='1D',prepared_ms=asof,
                data_available_ms=request_ms,source_sha256=digest(raw_bytes),source_file=str(Path(source).resolve()),
                package_version=importlib.metadata.version('tradingagents'),candles=rows,indicators=indicators,
                trade_action=None,model_status='NOT_CONNECTED',limitations=['daily exchange boundary retained','no verified liquidation model','not a profit backtest'])

def accept(packet_bytes, receipt, at_ms):
    from tradingagents.agents.rating import run_rating, extract_rating
    p=strict(packet_bytes)
    if receipt['input_sha256']!=digest(packet_bytes):raise ValueError('INPUT_HASH_MISMATCH')
    if receipt['instrument']!=p['instrument']:raise ValueError('WRONG_INSTRUMENT')
    start,end=receipt['started_ms'],receipt['completed_ms']
    if not p['prepared_ms']<=start<=end<=at_ms:raise ValueError('INVALID_TIME_ORDER')
    if at_ms-p['prepared_ms']>600000:raise ValueError('DECISION_STALE')
    state=receipt['final_state'];rating=run_rating(state)
    if rating not in ['Buy','Overweight','Hold','Underweight','Sell','REVIEW']:raise ValueError('UNKNOWN_RATING')
    narrative=state.get('final_trade_decision','')
    parsed=extract_rating(narrative)
    if parsed and parsed!=rating:raise ValueError('CONFLICTING_RATINGS')
    fixture=receipt.get('source_kind')=='test_fixture'
    evidence=receipt.get('provider_receipt',{})
    # Strings are claimed metadata, not independent provider authentication.
    have_evidence=all(isinstance(evidence.get(k),str) and evidence[k].strip() and evidence[k]!='UNKNOWN' for k in ['request_id','model','provider'])
    reasons=['EXECUTION_POLICY_NOT_APPROVED','LIQUIDATION_MODEL_UNKNOWN']
    if fixture:reasons.append('TEST_FIXTURE_NOT_MODEL_OUTPUT')
    if not have_evidence:reasons.append('MODEL_RECEIPT_MISSING')
    if not narrative.strip():reasons.append('RATIONALE_MISSING')
    if rating=='REVIEW':reasons.append('UNPARSEABLE_RATING')
    bias={'Buy':'BULLISH','Overweight':'BULLISH','Hold':'NEUTRAL','Underweight':'BEARISH','Sell':'BEARISH','REVIEW':'UNKNOWN'}[rating]
    return dict(schema=1,instrument=p['instrument'],input_sha256=digest(packet_bytes),original_rating=rating,
                research_bias=bias,rationale=narrative,trade_action=None,paper_execution_allowed=False,
                blockers=reasons,model_receipt_status='CLAIMED_PENDING_VERIFICATION' if have_evidence else 'MISSING',
                source_kind=receipt.get('source_kind','UNKNOWN'),receipt_sha256=digest(json.dumps(receipt,sort_keys=True).encode()),
                reports={k:state.get(k) for k in ['market_report','news_report','sentiment_report','investment_debate_state','risk_debate_state']})

def write_new(path,data):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('prepare');a.add_argument('--source',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('accept');a.add_argument('--packet',required=True);a.add_argument('--receipt',required=True);a.add_argument('--out',required=True)
    args=parser.parse_args();at=int(time.time()*1000)
    # Component path is deliberately offline, including all imported libraries.
    import socket
    def blocked(*a,**kw):raise RuntimeError('NETWORK_DISABLED')
    socket.socket.connect=blocked;socket.create_connection=blocked
    if args.cmd=='prepare':out=prepare(args.source,at)
    else:out=accept(Path(args.packet).read_bytes(),strict(Path(args.receipt).read_bytes()),at)
    write_new(args.out,out)
    print(json.dumps({'saved':args.out,'scope':out.get('scope'),'trade_action':out.get('trade_action'),'paper_execution_allowed':out.get('paper_execution_allowed',False)}))

if __name__=='__main__':main()
