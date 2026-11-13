from pathlib import Path
from fractions import Fraction as F
import json,hashlib
from pressure_rules import pressure_choice,FOLLOW,FADE
B=Path(__file__).resolve().parent
def main():
 fr=json.loads((B/'execution_freeze.json').read_text())
 for n,h in fr['hashes'].items():assert hashlib.sha256((B/n).read_bytes()).hexdigest()==h
 cases=[{'total10':F(100),'net10':F(80),'total1':F(10),'net1':F(8),'expected':FOLLOW},{'total10':F(370),'net10':F(362),'total1':F(10),'net1':F(2),'expected':FADE}];receipts=[]
 for x in cases:
  prior=x['total10']-x['total1'];priornet=x['net10']-x['net1'];ratio=9*x['total1']/prior;imb1=x['net1']/x['total1'];assert abs(priornet)<=prior and abs(x['net10'])/x['total10']>=F(4,5);direction=1 if x['net10']>0 else -1
  derived=FOLLOW if ratio>=1 and abs(imb1)>=F(4,5) and imb1*direction>0 else FADE if ratio<=F(1,4) and abs(imb1)<=F(1,5) else None;assert derived==x['expected'];actual=pressure_choice(x['total10'],x['net10'],x['total1'],x['net1'],F(20),F(15),F(50),250000000)[0];assert actual==derived;receipts.append({'label':'SYNTHETIC_MATH_NOT_MARKET_OR_MODEL_RUN','expected':derived,'prior9':str(prior),'prior9_net':str(priornet),'ratio':str(ratio),'imb1':str(imb1),'costroom_equality_included':True})
 assert pressure_choice(F(370),F(369),F(10),F(2),F(20),F(15),F(50),0)[1]=='WAIT_NESTED_WINDOW_INCONSISTENCY'
 source=B.parent/'phase025_public_input_latency_probe/instruments.json';assert (B/'instruments.json').read_bytes()==source.read_bytes();r={'status':'PASS_FINITE_SYNTHETIC_EXACT_WINDOW_MATH_AND_PUBLIC_SPEC_COPY','cases':receipts,'impossible_nested_window_rejected':True,'fixed9spec_original_bytes':True,'real_market_profit_or_model_validation':None,'future_raw_audit_entry':'reference/current bookordinal/price plus rawdedup10s/1s sums/freshunique trade/rate/threshold/cut-cooldown; never fullstrategy thirdparty claim'};(B/'audit.json').write_text(json.dumps(r,indent=2));print(r['status'])
if __name__=='__main__':main()
