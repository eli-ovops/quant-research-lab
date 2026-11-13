import json,itertools
from pathlib import Path
R=Path(__file__).resolve().parent
families={
 'trend':[{'fast':a,'slow':b,'er_min':c} for a,b,c in [(8,32,.2),(12,48,.2),(20,80,.2),(12,48,.35),(20,80,.35)]],
 'breakout':[{'n':a,'volume_multiple':b} for a,b in [(12,1),(20,1),(55,1),(20,1.5),(55,1.5)]],
 'range':[{'n':20,'z':a,'er_max':b} for a,b in [(1.5,.25),(2,.25),(2.5,.25),(2,.4),(2.5,.4)]],
 'pattern':[{'shape':s} for s in ['engulf','pin','inside','three_run','failed_break']],
 'scalp':[{'rsi_n':a,'threshold':b} for a,b in [(5,20),(7,25),(10,30),(7,20),(10,25)]],
 'martingale':[{'n':20,'z':a,'er_max':b} for a,b in [(1.5,.25),(2,.25),(2.5,.25),(2,.4),(2.5,.4)]]}
configs=[]
for family,variants in families.items():
 for i,params in enumerate(variants):
  for lev,h,cost in itertools.product([1,3,10],[24,168],['base','stress']):
   rule={'id':f'{family}_{i}','family':family,**params}
   configs.append({'id':f'{rule["id"]}_L{lev}_H{h}_{cost}','rule':rule,'leverage':lev,'horizon_hours':h,'cost':cost,'product':'SPOT' if lev==1 else 'CONDITIONAL_SWAP'})
p={'version':1,'registered_before_new_pnl':True,'owner':'root','started_utc':'2026-10-06T01:25:27Z','deadline_utc':'2026-10-07T01:25:27Z','configuration_cap':360,'new_candle_cap':2000000,'configs':configs,
 'screen_assets':['BTC','ETH','SOL','XRP','DOGE','ADA','LINK','LTC','AVAX','DOT','BCH','NEAR','SUI','APT','TRX'],
 'holdout_assets':['OP','ARB','UNI','AAVE','ETC','FIL','ATOM','ICP'],
 'raw_start':'2026-07-05T00:00:00Z','start':'2026-07-10T00:00:00Z','end':'2026-10-05T00:00:00Z',
 'folds':[['2026-07-10','2026-08-08'],['2026-08-08','2026-09-06'],['2026-09-06','2026-10-05']],
 'data_warning':'Screen assets all previously observed. New asset holdout not previously used by this batch but calendar regimes correlated and prior project exposure cannot be excluded. No blind/future claim. Current surviving assets bias remains.',
 'initial':500,'target':650,'account_stop':250,'max_entry_fraction':.95,
 'rules':{'signal_timing':'All rules closed UTC hourly using four valid15m bars except scalp uses closed15m. Signal timestamp=next15m boundary. 120h warmup. EMA seeded at first valid close; history resets after invalid hour. RSI Cutler simple gains/losses. ER20=abs(c-last20c)/sum(abs20changes); zero denominator ER0. ATR14 simple true range.',
 'trend':'EMAfast/slow actual cross AND ER20>=er_min; direction of cross. Must have 120 closed hours.',
 'breakout':'Close >previous n highs AND volume>=volume_multiple*mean(previous20 hourlyvolume), or mirror short. Current bar not included in reference.',
 'range':'Boll population z crosses up -z long / down +z short, ER20<=er_max and RSI14<50 long or >50 short. band each time includes own closedbar.',
 'pattern':'engulf: previous bearish,current bullish body contains priorbody long; mirror short. pin: lowerwick>=2*body and upperwick<=body,long, mirror short; body>0. inside: previousbar range inside barbeforeprevious, currentclose breaks previoushigh/low. three_run: 3 rising closes and currentclose>prior20high long; mirror short. failed_break: currentlow<prior20low and currentclose>prior20low long; mirror short. All patterns trendfilter currentclose>EMA48 forlong and <EMA48 forshort; both sides simultaneously=>no signal.',
 'scalp':'15m CutlerRSI crosses up threshold long, down100-threshold short, ER20<=.5, close<rolling20 volumeweightedclose long, close>rollingVWclose short. This is not tradeVWAP or actual HFT.',
 'martingale':'Same signals as range. After net losing closedtrade margin allocation multiplier1,2,4; after gain/reset nonloss return1; 3consecutive losses halts account untilwindowend. Startstake20%currentequity, multiply,capped95%. No openposition averaging and no cash topup.'},
 'execution':'Same public OHLC cost assumptions as previousbatch. Each independentcoin/window starts500. SPOT longonly; SWAPboth directions. One position at a time. Standard marginallocation95%currentcash; martingale asdefined. Spotbuybasefee, sellquotefee, leftovers retained in equity. SWAPlinearctVal contracts, initialmargin reservation+entryfee<=allocation, no borrow beyond cash. Decimal adverse ticks/floorlots.',
 'trade_exit':'Signal entry next15mopen; holdbars increment closes. Fixed entry ATR fraction clipped [.003,.05]. Trend/breakout price SL2ATR TP4ATR max96bars; range/martingale SL2ATR TP1ATR max48bars; pattern SL1.5ATR TP3ATR max48bars; scalp SL.004 TP.006 max8bars. Evaluate only closed15m price, then exit next15mopen. No intrabarstop/targetfill; gap losses allowed. No opposite-signal exit. Cooldown4bars afterexit, scalp1bar. Max8entries24h/40entries168h. Targets/accountstop determined at closednetexit-equity650/250 then nextopenexit and terminate; actualfinal650 counts target. Never restart terminated account. Endexit lastcloseproxy.',
 'funding':'realizedRate at actualfundingTime for heldposition, tradedbaropenproxy; charge before scheduledexit, not beforeentry atsameboundary. At end lastcloseproxy. Require bracketingfunding and gaps<=8h.',
 'liquidation':'Same fixed proxy2%maintenance+.2%liquidationfee, adverse OHLC and openbeforeexit. Onbreach modelcash0 and halt; never claim actualexchange liquidated. AllSWAPtrue_target/true_liquidationUNKNOWN.',
 'costs':{'SPOT':{'base':{'fee':.001,'slip':.0005},'stress':{'fee':.002,'slip':.001}},'CONDITIONAL_SWAP':{'base':{'fee':.0005,'slip':.0005},'stress':{'fee':.001,'slip':.001}}},
 'data_gate':'Full120hwarmup+window missing/zero/unconfirmed/conflicting/invalid=>INVALID retained; nofill. Check exactspecidentity, current specs historical validityUNKNOWN.',
 'episodes':'Daily24h, 7day nonoverlap windows anchored each29dayfold, fullhorizonfits. No pooled capital or sum across configurations.',
 'control':'Identical rule risk exits/staking, but entry opportunity every8hours fromstart, direction fixedSHA256 seed50020261006b product/lev/h/coin/start/bar; spotlong. Same maxtrade/cooldown/termination. This is scheduled-random-direction benchmark, not exact exposurematching; report tradecounts.',
 'selection':'Screening ONLY old15coins across3folds; choose atmost1 per(product,horizon), STRESS configurations only. Eligible: noinvalid, >=30closedtrades, targets>=3, totalmeanreturn>0, at least2of3foldmeanpositive, pooled pairedmeanreturn minus control>0. Rank minimumfoldmeanreturn, tie pooledpairedmeanreturn thenid. No subsequent replacement. Save selection before holdoutsignal/PnL.',
 'paper_candidate_gate':'Selected configuration on8newcoins: invalid0, >=30closedtrades, targets>=3, pooledmeanreturn>0, >=2of3foldpositive, pairedmeanreturn>0. Report datecluster bootstrap90%mean/paired intervals withfixedseed and2000resamples; lowerbounds must both>0 for papereligible. Still no realprofit guarantee. SWAPconditionalonly, true execution remainsUNKNOWN.',
 'stops':'No re-tune after newcoin outcomes, no new batch this turn, no live/privateAPI/keys/install/payments/oldmonitor/backgroundpolling.',
 'rules_version':'AUTONOMOUS-2026-10-05-v1 / ROUTUTING-2026-09-30-v3','actual_model_effort':'UNKNOWN'}
assert len(configs)==360
(R/'protocol.json').write_text(json.dumps(p,indent=2)+'\n')
(R/'run.json').write_text(json.dumps({'status':'PREPARING','owner':'root','started_utc':p['started_utc'],'deadline_utc':p['deadline_utc'],'max_configs':360,'max_new_candles':2000000,'actual_model_effort':'UNKNOWN'},indent=2)+'\n')
