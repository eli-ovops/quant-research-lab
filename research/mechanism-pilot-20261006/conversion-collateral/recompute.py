"""Offline only. Recompute frozen raw observations; performs no network calls."""
import json,pathlib,hashlib
from decimal import Decimal as D, ROUND_HALF_UP
from datetime import datetime,timezone
from abi import words
P=pathlib.Path(__file__).parent
def read(n):return json.loads((P/'raw'/f'{n}.body').read_text())
def decmap(n):return {x['id']:words(x['result']) for x in read(n) if isinstance(x.get('result'),str)}
s=decmap('comet_state'); v=decmap('comet_dex_oracle');block=next(x['result'] for x in read('comet_dex_oracle') if x['id']==4)
compound={'status':'UPPER_BOUND_NOT_EXECUTABLE_INVENTORY','block':int(block['number'],16),'block_hash':block['hash'],'block_utc':datetime.fromtimestamp(int(block['timestamp'],16),timezone.utc).isoformat(),'reserves_USDC':str(D(s[0][0])/10**6),'targetReserves_USDC':str(D(s[1][0])/10**6),'buy_paused':bool(s[3][0]),'inventory_WETH':str(D(s[2][0])/10**18),'spend_USDC':100,'quote_WETH':str(D(s[5][0])/10**18),'DEX_net_of_swap_fee_and_impact_USDC':str(D(v[2][0])/10**6),'gross_before_chain_cost_USDC':str(D(v[2][0])/10**6-100),'inventory_supports_100_USDC':s[2][0]>=s[5][0],'inventory_implied_max_spend_USDC_linear_upper':str(D(100)*s[2][0]/s[5][0]),'asset_oracle_USD':str(D(v[0][0])/10**8),'base_oracle_USD':str(D(v[1][0])/10**8),'oracle_updated_unix':v[3][3],'oracle_age_at_block_seconds':int(block['timestamp'],16)-v[3][3],'base_fee_gwei':str(D(int(block['baseFeePerGas'],16))/10**9),'quoter_swap_only_gas_estimate':v[2][3],'full_execution_gas':'UNKNOWN','priority_and_ordering_cost':'UNKNOWN','next_block_arrival':'NOT_SIMULATED','30_day_history':'NOT_RUN','realized_profit':'NOT_TESTED'}
e=json.loads((P/'selected_event.json').read_text());ms=sorted(e['markets'],key=lambda m:int(m['id']));books={x['asset_id']:x for x in read('poly_books')};adapter=decmap('poly_adapter'); packed=adapter[1][0].to_bytes(32,'big');fee_bps=int.from_bytes(packed[3:5],'big');retained=D(1)-D(fee_bps)/10000
legs=[]
for i,m in enumerate(ms):
 id=json.loads(m['clobTokenIds'])[1 if i==0 else 0];b=books[id];side='asks' if i==0 else 'bids';levels=sorted(b[side],key=lambda x:D(x['price']),reverse=i>0)
 legs.append({'market_id':m['id'],'name':m['groupItemTitle'],'operation':'BUY_NO' if i==0 else 'SELL_YES','asset_id':id,'adapter_token_matches':str(adapter[i+2][0])==id,'levels':levels,'top_price':levels[0]['price'],'top_size':levels[0]['size'],'timestamp_ms':int(b['timestamp']),'hash':b['hash'],'fee_rate':m['feeSchedule']['rate'],'fee_exponent':m['feeSchedule']['exponent']})
def fill(leg,q):
 rem=q;value=D(0);fee=D(0)
 for l in leg['levels']:
  n=min(rem,D(l['size']));price=D(l['price']); value+=n*price;fee+=n*D(str(leg['fee_rate']))*price*(1-price);rem-=n
  if rem<=0:break
 return value,fee.quantize(D('.00001'),rounding=ROUND_HALF_UP),rem
def scenario(q):
 buy,buyfee,rem=fill(legs[0],q);sales=[fill(l,q*retained) for l in legs[1:]]; revenue=sum(x[0] for x in sales);fees=buyfee+sum(x[1] for x in sales)
 return {'shares_NO':str(q),'shares_each_YES':str(q*retained),'buy_value':str(buy),'sell_value':str(revenue),'taker_fees_estimate':str(fees),'cash_needed_including_buy_fee':str(buy+buyfee),'gross_before_fees':str(revenue-buy),'after_taker_and_conversion_fees_before_gas':str(revenue-buy-fees),'unfilled':str(rem+sum(x[2] for x in sales))}
lo,hi=D(0),D(2000)
for i in range(80):
 mid=(lo+hi)/2;buy,fee,rem=fill(legs[0],mid)
 if buy+fee<=500 and rem==0:lo=mid
 else:hi=mid
q=lo.quantize(D('.000001'),rounding='ROUND_DOWN'); times=[l['timestamp_ms'] for l in legs];meta=json.loads((P/'raw/poly_books.meta.json').read_text())
poly={'status':'OBSERVED_BOOK_UPPER_BOUND_NEGATIVE_NOT_SEQUENTIAL_BACKTEST','event_id':e['id'],'title':e['title'],'event_augmented':e['negRiskAugmented'],'gamma_version':sorted(set(m['version'] for m in ms)),'adapter':'0xd91E80cF2E7be2e162c6513ceD06f1dD0dA35296','adapter_collateral':'0x'+hex(adapter[0][0])[2:].zfill(40),'adapter_collateral_decimals':words(read('poly_collateral_decimals')['result'])[0],'question_count_onchain':packed[0],'determined_onchain':bool(packed[1]),'conversion_fee_bps':fee_bps,'all_leg_ids_match_adapter':all(l['adapter_token_matches'] for l in legs),'quote_unit':'CLOB dollar unit; adapter collateral is 6-decimal USDC.e; CLOB pUSD ramp parity/cost NOT_SIMULATED','book_timestamp_spread_seconds':(max(times)-min(times))/1000,'oldest_book_age_at_receive_seconds':meta['ended_unix']-min(times)/1000,'snapshot_50_shares':scenario(D(50)),'capacity_under_500_including_buy_fee':scenario(q),'book_legs':legs,'gas':'UNKNOWN','sequential_buy_settlement_convert_sell':'NOT_RUN','7_day_10_event_history':'NOT_RUN','fee_precision_note':'Per-leg aggregate rounding to 5 decimals; exact match-level rounding may differ. Negative zero-fee bound unchanged.'}
r={'compound':compound,'polymarket':poly};(P/'results.json').write_text(json.dumps(r,indent=2)); print(json.dumps({'compound':compound,'polymarket':{k:v for k,v in poly.items() if k!='book_legs'}},indent=2))
