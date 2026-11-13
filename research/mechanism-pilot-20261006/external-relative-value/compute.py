import json,pathlib,math,hashlib,datetime
B=pathlib.Path(__file__).resolve().parent
def read(n):return json.loads((B/'raw'/(n+'.json')).read_text())
def mcp(n):return read(n)['data']['data']
def vwap(rows,q):
 total=0;remaining=q
 for price,size,*_ in rows:
  use=min(remaining,float(size));total+=use*float(price);remaining-=use
  if remaining<1e-10:return total/q
 raise ValueError('Insufficient sampled depth')
S=float(mcp('index')[0]['idxPx']);N=100;q=1;fee=.0005
nb=mcp('near_book')[0];fb=mcp('far_book')[0]
A=vwap(nb['asks'],q);b=vwap(nb['bids'],q);Bfar=vwap(fb['bids'],q);a=vwap(fb['asks'],q)
pnlbtc=N*(1/A-1/b)+N*(1/a-1/Bfar)
costbtc=fee*N*(1/A+1/b+1/a+1/Bfar)
sp={'status':'报价与规模验证完成；收益未检验','near_buy':A,'near_immediate_sell':b,'far_sell':Bfar,'far_immediate_buy':a,'snapshot_skew_ms':abs(int(nb['ts'])-int(fb['ts'])),'gross_contract_face_usd':200,'min_contracts':.1,'conservative_collateral_usd':200,'actual_account_eligibility':'UNKNOWN','immediate_round_trip_gross_usd':pnlbtc*S,'fee_assumption_roundtrip_usd':costbtc*S,'immediate_round_trip_net_usd':(pnlbtc-costbtc)*S,'hypothetical_same_exit_price_carry_usd':N*(1/A-1/Bfar)*S,'warning':'same exit price is hypothetical and not a terminal identity for different expiries','scenarios':[]}
for near,far,label in [(85000,85500,'curve narrows'),(85000,86500,'curve widens'),(90000,90000,'hypothetical flat curve')]:
 gross=N*(1/A-1/near+1/far-1/Bfar)*near
 fees=N*fee*(1/A+1/near+1/far+1/Bfar)*near
 sp['scenarios'].append({'label':label,'near_exit':near,'far_exit':far,'usd_conversion':near,'net_usd':gross-fees,'execution':'hypothetical exits, not observed'})
ob=mcp('option_book')[0];bid=vwap(ob['bids'],1);ask=vwap(ob['asks'],1);mult=.01
g=next(x for x in read('option_summary')['data'] if x['instId']=='BTC-USD-261009-85500-C')
mark=float(read('option_mark')['data'][0]['markPx']);delta=float(g['deltaBS']);hedge=delta*mult
factor=float(read('option_tiers')['data'][0]['optMgnFactor'])
fwd=float(g['fwdPx']);otm=max(85500-fwd,0);posim=(max(.1,.15-otm/fwd)*factor+mark)*mult*S
openim=max(posim-bid*mult*S,.1*mult*S);mmr=(.03*factor+mark)*mult*S
opt={'status':'期权链与保证金纸面验证完成；收益未检验','id':g['instId'],'min_contracts':1,'multiplier_btc':mult,'underlying_usd':S,'bid_btc_per_underlying':bid,'ask_btc_per_underlying':ask,'mark':mark,'exchange_mark_iv':float(g['markVol']),'exchange_deltaBS':delta,'exchange_inverse_delta':float(g['delta']),'spot_delta_hedge_btc':hedge,'spot_hedge_notional_usd':hedge*S,'short_premium_usd':bid*mult*S,'position_imr_usd':posim,'sell_to_open_imr_usd':openim,'maintenance_margin_usd':mmr,'margin_factor':factor,'separate_collateral_plus_hedge_usd':hedge*S+openim,'collateral_counted_as_part_of_spot_hedge_usd':hedge*S,'capital_remaining_before_fees_usd':500-hedge*S,'option_roundtrip_fee_assumption_usd':2*min(.0003,.07*bid)*mult*S,'option_immediate_spread_cost_usd':(ask-bid)*mult*S,'spot_entry_fee_assumption_usd':.001*hedge*S,'snapshot_timing':'index ~04:13:03, book ~04:13:56, greeks ~04:14:20, mark ~04:15:06 UTC; asynchronous, cannot be executable net quote','spot_actual_bidask':'UNKNOWN','account_eligibility':'UNKNOWN; public help says mainland KYC options enabling capital 10000 USD; actual account not queried','gamma_5pct_move_approx_usd':.5*float(g['gammaBS'])*mult*(S*.05)**2,'risk':'delta hedging has gamma/jump/vega/rehedging/margin/collateral FX risks; local quadratic stress is not tail-loss bound','realized_pnl':None}
h=read('prediction_history')['history'];ts=[int(x['t']) for x in h]
pred={'status':'取得真实赔率历史；传导收益未检验','event':'SEC first spot Bitcoin ETF on Jan 10 2024','token_mapping':'BTC; control ETH frozen before return test','n_points':len(h),'first_utc':datetime.datetime.fromtimestamp(min(ts),datetime.timezone.utc).isoformat() if ts else None,'last_utc':datetime.datetime.fromtimestamp(max(ts),datetime.timezone.utc).isoformat() if ts else None,'max_gap_sec':max([b-a for a,b in zip(ts,ts[1:])] or [0]),'historical_token_bidask':'UNKNOWN','first_public_receipt_latency':'UNKNOWN','lead_lag_pnl':None,'limitation':'historical API is a current reconstruction, no original receipt timestamps or matched token quotes; ex-post chosen event, no causal inference'}
idx={'status':'公告与实物产品验证完成；资金流证据不足','historical_events':[{'announced':'2026-01-02','effective':'2026-01-30 16:00 ET','addition':'BNB','indicative_weight':.1556,'weight_factor_date':'2026-01-23'},{'announced':'2026-04-02','effective':'2026-04-30 16:00 ET','addition':'TAO','indicative_weight':.006,'weight_factor_date':'2026-04-23'}],'future_event':{'announced':'2026-10-02','effective':'2026-10-30 16:00 ET','addition':'GRAM (previously Toncoin)','indicative_weight':.0061,'factor_date':'2026-10-23','token_identity':'requires contract / ticker mapping, no GRAM return test'},'physical_product_isin':'GB00BN474G19','actual_factsheet_date':'2026-08-31','actual_before_after_constituent_quantities':'UNKNOWN','shares_creation_redemption':'UNKNOWN','estimated_actual_net_buy_usd':None,'sample_pnl':None,'tested_rebalance_count':0,'historical_events_identified':2,'required_events':4}
out={'as_of':'2026-10-06','capital_usd':500,'calendar_spread':sp,'delta_hedged_options':opt,'prediction_token_transmission':pred,'index_mechanical_buying':idx,'stablecoin_units':{'identity':'P_BTC_USDT=P_BTC_USD/S_USDT_USD','usd_flat_stablecoin_down_2pct_quote_up_pct':(1/.98-1)*100,'direct_short_btc':'adds BTC directional exposure; not a denomination-only hedge','requirements':'common USD book; quantities and exposure of both collateral and hedge; stablecoin liability/asset FX included'},'public_explicit_calls':37,'internal_retries':'UNKNOWN','profitability_claim':False}
(B/'results.json').write_text(json.dumps(out,indent=2,ensure_ascii=False))
files=[]
for f in sorted((B/'raw').iterdir()):files.append({'path':str(f),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(B/'manifest.json').write_text(json.dumps(files,indent=2));print(json.dumps(out,indent=2,ensure_ascii=False))
