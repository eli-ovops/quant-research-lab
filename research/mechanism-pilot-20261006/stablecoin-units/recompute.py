"""Offline arithmetic only. Synthetic scenarios are not historical returns."""
from decimal import Decimal as D
import json,pathlib
P=pathlib.Path(__file__).parent

def payload(n):return json.loads((P/'raw'/f'{n}.json').read_text())['structuredContent']['data']['data'][0]
i=payload('okx_index'); s=payload('okx_spot');f=payload('okx_swap');k=json.loads((P/'raw/kraken_usdtusd.body').read_text())['result']['USDTZUSD'];km=json.loads((P/'raw/kraken_usdtusd.meta.json').read_text())
x=D(i['idxPx']);sm=(D(s['bids'][0][0])+D(s['asks'][0][0]))/2;sb=D(k['bids'][0][0]);sa=D(k['asks'][0][0]);mid=(sb+sa)/2
snap={'status':'CURRENT_SNAPSHOT_NOT_ENTRY_SIGNAL_OR_ARBITRAGE','BTC_USD_index':str(x),'BTC_USDT_spot_bid':s['bids'][0][0],'BTC_USDT_spot_ask':s['asks'][0][0],'BTC_USDT_perp_bid':f['bids'][0][0],'BTC_USDT_perp_ask':f['asks'][0][0],'USDT_USD_Kraken_bid':str(sb),'USDT_USD_Kraken_ask':str(sa),'USDT_discount_mid_percent':str((1-mid)*100),'index_divided_by_spot_mid_diagnostic_only':str(x/sm),'BTC_USD_divided_by_USDT_USD_mid_diagnostic_USDT':str(x/mid),'timestamps_ms':{'index':int(i['ts']),'spot':int(s['ts']),'perp':int(f['ts'])},'OKX_source_skew_seconds':str(D(max(int(i['ts']),int(s['ts']),int(f['ts']))-min(int(i['ts']),int(s['ts']),int(f['ts'])))/1000),'Kraken_top_bid_level_last_update_unix':k['bids'][0][2],'Kraken_top_ask_level_last_update_unix':k['asks'][0][2],'Kraken_received_unix':km['ended_unix'],'Kraken_snapshot_timestamp':'NOT_PROVIDED; level timestamps are not snapshot sequence time','discount_0_1pct_current_mid':mid<=D('.999'),'15_min_persistence':'NOT_MEASURED','historical_depeg_event':'NOT_TESTED','perp_500USDT_depth_capacity':'UNKNOWN: sizes in contract units; ctVal not fetched'}
# Freeze synthetic parameters independently of real observations.
C=N=D(500);X0=D(100000);S0=D('.999');P0=X0/S0;q=N/P0;fee=D('.0005')
scenarios=[]
for name,X1,S1 in [('recovery_BTC_flat',X0,D('.9995')),('recovery_BTC_up_1pct',X0*D('1.01'),D('.9995')),('recovery_BTC_down_1pct',X0*D('.99'),D('.9995')),('depeg_worsens_BTC_flat',X0,D('.995')),('72h_timeout_no_recovery_BTC_flat',X0,S0)]:
 P1=X1/S1;pnl=q*(P0-P1);cost=fee*q*(P0+P1);usd_pnl=pnl*S1;cash=C*(S1-S0);eq=(C+pnl)*S1;delta=eq-C*S0
 assert abs(delta-(cash+usd_pnl))<D('1e-23')
 assert abs(usd_pnl-q*(X0*S1/S0-X1))<D('1e-23')
 scenarios.append({k:(v if isinstance(v,bool) else str(v)) for k,v in {'name':name,'synthetic':True,'X1_USD':X1,'S1_USD_per_USDT':S1,'q_BTC':q,'P0_USDT':P0,'P1_USDT':P1,'short_PNL_USDT_before_cost':pnl,'short_PNL_USD_before_cost':usd_pnl,'collateral_FX_PNL_USD':cash,'equity_USD_change_before_cost':delta,'assumed_5bps_each_side_fee_USDT':cost,'short_PNL_USDT_after_assumed_fee':pnl-cost,'equity_USD_change_after_assumed_fee':delta-cost*S1}.items()})
r={'live_snapshot':snap,'synthetic':{'label':'SYNTHETIC_NOT_REALIZED_OR_BACKTEST_RETURN','assumptions':{'collateral_USDT':'500','short_notional_at_entry_USDT':'500','BTC_USD_entry':'100000','S_entry_USD_per_USDT':'0.999','perp_equals_spot_at_each_endpoint':True,'basis_funding_slippage_liquidation_ignored':True,'fee_each_side_sensitivity':'0.0005 (assumed, not verified account fee)','initial_collateral_USD_value':'499.5'},'scenarios':scenarios},'conclusion':'Single BTC-USDT short is short BTC with USDT exposure, not stablecoin-only arbitrage. No 15-minute depeg signal or historical edge validated.'}
(P/'results.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
