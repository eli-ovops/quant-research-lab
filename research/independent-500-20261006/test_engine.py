import unittest
import copy
import math
import engine

Q,H=engine.QUARTER,engine.HOUR
START=120*H
SPOT={'instId':'BTC-USDT','instType':'SPOT','baseCcy':'BTC','tickSz':'.01','lotSz':'.001','minSz':'.001'}
SWAP={'instId':'BTC-USDT-SWAP','instType':'SWAP','ctType':'linear','settleCcy':'USDT','ctValCcy':'BTC','ctVal':'.01','tickSz':'.01','lotSz':'1','minSz':'1'}
CONFIG={'product':'SPOT','leverage':1,'horizon_hours':24,'cost':'base','rule':{'family':'donchian','n':20}}


def fixture(hours=300,price=100):
    return [[t,str(price),str(price+.1),str(price-.1),str(price),'10','10','1000','1'] for t in range(0,hours*H,Q)]


def funding(end):
    return [{'fundingTime':t,'realizedRate':'.001'} for t in range(START,end+8*H,8*H)]


class EpisodeTests(unittest.TestCase):
    def run_episode(self,rows=None,config=None,spec=None,signals=None,control=False):
        config=config or CONFIG
        end=START+config['horizon_hours']*H
        return engine.simulate(rows if rows is not None else fixture(),spec or SPOT,funding(end),config,START,end,
                               signals if signals is not None else {START:1},control)

    def test_spot_actual_ledger_double_cost(self):
        result=self.run_episode()
        buys=[e for e in result['events'] if e['type']=='ENTRY']
        sells=[e for e in result['events'] if e['type']=='EXIT']
        self.assertEqual(len(buys),1);self.assertEqual(len(sells),1)
        entry=buys[0];self.assertAlmostEqual(entry['base_after'],entry['quantity']*.999)
        cash=500;position=0
        for event in result['events']:
            cash+=event['cash_delta'];position+=event['base_delta']
            self.assertAlmostEqual(cash,event['cash_after'])
            self.assertAlmostEqual(position,event['base_after'])
        self.assertGreater(result['metrics']['fees'],0)
        self.assertLess(result['metrics']['final_equity'],500)
        self.assertEqual(result['metrics']['status'],'VALID')

    def test_price_tick_precision(self):
        self.assertEqual(engine.adverse_price(.09,'sell',.001,'.00001'),.08991)
        self.assertEqual(engine.adverse_price(70,'sell',.001,'.01'),69.93)
        self.assertEqual(engine.adverse_price(10,'buy',.001,'.05'),10.05)

    def test_future_changes_do_not_change_closed_signals(self):
        rows=fixture()
        for i,r in enumerate(rows):
            p=100+5*math.sin(i//4/9)
            r[1:5]=[str(p),str(p+.1),str(p-.1),str(p)]
        changed=copy.deepcopy(rows);cut=180*H
        for r in changed:
            if r[0]>=cut:r[1:5]=['1000','1001','999','1000']
        rules=[dict(family='donchian',n=20),dict(family='ema',fast=12,slow=48),
               dict(family='momentum',n=24,threshold=.02),dict(family='boll',n=20,z=2),
               dict(family='rsi',n=14,low=30,high=70),
               dict(family='atr_break',n=12,atr_n=14,atr_multiple=.5)]
        for rule in rules:
            a=engine.prepare_signals(rows,rule);b=engine.prepare_signals(changed,rule)
            self.assertEqual({t:v for t,v in a.items() if t<=cut},{t:v for t,v in b.items() if t<=cut})

    def test_entry_uses_next_open_not_signal_close(self):
        rows=fixture();rows[START//Q][1:5]=['101','102','100','102']
        result=self.run_episode(rows=rows)
        event=result['events'][0]
        self.assertEqual(event['reference_price'],101)
        self.assertEqual(event['timestamp'],START)
        self.assertEqual(event['price'],engine.adverse_price(101,'buy',.0005,'.01'))

    def test_funding_long_pays_short_receives_no_entry_snapshot(self):
        config=dict(CONFIG,product='CONDITIONAL_SWAP',leverage=5)
        for sign in [-1,1]:
            result=self.run_episode(config=config,spec=SWAP,signals={START:sign})
            charges=[e for e in result['events'] if e['type']=='FUNDING']
            self.assertTrue(charges)
            self.assertGreater(charges[0]['timestamp'],START)
            self.assertTrue(all(e['cash_delta']*sign<0 for e in charges))
            entry=result['events'][0]
            self.assertAlmostEqual(abs(entry['base_after']),entry['quantity']*.01)
            self.assertAlmostEqual(entry['margin']+entry['fee'],entry['quantity']*.01*entry['price']*(1/5+.0005))
            self.assertEqual(result['metrics']['true_target'],'UNKNOWN')

    def test_adverse_extreme_beats_close_target_and_never_reopens(self):
        rows=fixture();r=rows[START//Q];r[1:5]=['100','200','1','180']
        config=dict(CONFIG,product='CONDITIONAL_SWAP',leverage=10)
        result=self.run_episode(rows=rows,config=config,spec=SWAP,signals={START:1,START+H:1})
        self.assertEqual(result['metrics']['exit_reason'],'MAINTENANCE_PROXY_BREACH')
        self.assertEqual(result['metrics']['final_equity'],0)
        self.assertFalse(result['metrics']['target_hit'])
        self.assertEqual(len([e for e in result['events'] if e['type']=='ENTRY']),1)
        self.assertEqual(result['metrics']['max_drawdown'],1)

    def test_missing_and_zero_retained_invalid(self):
        for warmup in [True,False]:
            rows=fixture();index=10 if warmup else START//Q+1
            rows[index][5]='0'
            result=self.run_episode(rows=rows)
            self.assertEqual(result['metrics']['status'],'DATA_INVALID')
            self.assertIsNone(result['metrics']['final_equity'])
            rows=fixture();del rows[index]
            self.assertEqual(self.run_episode(rows=rows)['metrics']['status'],'DATA_INVALID')

    def test_missing_funding_invalid(self):
        cfg=dict(CONFIG,product='CONDITIONAL_SWAP',leverage=5)
        result=engine.simulate(fixture(),SWAP,[],cfg,START,START+24*H,{START:1})
        self.assertEqual(result['metrics']['status'],'DATA_INVALID')
        self.assertIsNone(result['metrics']['return'])

    def test_minimum_rejection_one_attempt(self):
        result=self.run_episode(spec=dict(SPOT,minSz='10000'),signals={START:1,START+H:1})
        self.assertEqual(result['metrics']['status'],'ORDER_REJECTED')
        self.assertEqual(result['metrics']['final_equity'],500)
        self.assertEqual(len(result['events']),1)

    def test_target_signal_exits_next_open_actual_net_decides(self):
        rows=fixture();r=rows[START//Q];r[1:5]=['100','140','99','140']
        rows[START//Q+1][1:5]=['90','91','89','90']
        result=self.run_episode(rows=rows)
        self.assertEqual(result['events'][1]['timestamp'],START+Q)
        self.assertEqual(result['metrics']['exit_reason'],'TARGET_CLOSE_SIGNAL')
        self.assertFalse(result['metrics']['target_hit'])

    def test_controls_share_seed_across_rules(self):
        a=engine.control_choice(SPOT,CONFIG,START)
        b=engine.control_choice(SPOT,dict(CONFIG,rule={'family':'ema','fast':12,'slow':48}),START)
        self.assertEqual(a,b)
        self.assertTrue(START<=a[0]<START+12*H)
        self.assertEqual(a[1],1)

    def test_funding_before_queued_exit(self):
        rows=fixture();index=(START+8*H-Q)//Q
        rows[index][1:5]=['100','140','99','140']
        cfg=dict(CONFIG,product='CONDITIONAL_SWAP',leverage=5)
        result=self.run_episode(rows=rows,config=cfg,spec=SWAP)
        same=[e for e in result['events'] if e['timestamp']==START+8*H]
        self.assertEqual([e['type'] for e in same],['FUNDING','EXIT'])

    def test_exact_120_hour_warmup_available_boundary(self):
        rows=fixture()
        rows[START//Q-1][1:5]=['100','131','99','130']
        signals=engine.prepare_signals(rows,dict(family='donchian',n=20))
        self.assertEqual(signals.get(START),1)
        self.assertTrue(all(t>=START for t in signals))

    def test_terminal_funding_uses_last_close_before_proxy_exit(self):
        cfg=dict(CONFIG,product='CONDITIONAL_SWAP',leverage=5)
        result=self.run_episode(config=cfg,spec=SWAP)
        end=START+24*H
        final=[e for e in result['events'] if e['timestamp']==end]
        self.assertEqual([e['type'] for e in final],['FUNDING','EXIT'])
        self.assertTrue(final[0]['terminal_price_proxy'])
        self.assertEqual(final[0]['reference_price'],100)

    def test_gap_open_maintenance_precedes_queued_exit(self):
        rows=fixture();index=(START+8*H-Q)//Q
        rows[index][1:5]=['100','140','99','140']
        rows[index+1][1:5]=['1','2','.9','1']
        cfg=dict(CONFIG,product='CONDITIONAL_SWAP',leverage=5)
        result=self.run_episode(rows=rows,config=cfg,spec=SWAP)
        same=[e for e in result['events'] if e['timestamp']==START+8*H]
        self.assertEqual([e['type'] for e in same],['FUNDING','MAINTENANCE_PROXY_BREACH'])
        self.assertEqual(result['metrics']['final_equity'],0)
        self.assertEqual(same[-1]['phase'],'OPEN_BEFORE_EXIT')

    def test_actual_donchian_cross_atr_break_and_prepared_input(self):
        rows=fixture()
        rows[START//Q-1][1:5]=['100','131','99','130']
        for i in range(START//Q,START//Q+4):rows[i][1:5]=['140','141','139','140']
        don=engine.prepare_signals(rows,dict(family='donchian',n=20))
        self.assertEqual(don[START],1)
        self.assertNotIn(START+H,don)
        atr=engine.prepare_signals(rows,dict(family='atr_break',n=12,atr_n=14,atr_multiple=.5))
        self.assertEqual(atr[START+H],1)
        prepared=engine.prepare_rows(rows)
        self.assertEqual(self.run_episode(rows=rows),self.run_episode(rows=prepared))
        self.assertEqual(don,engine.prepare_signals(prepared,dict(family='donchian',n=20)))

    def test_random_long_fixture_independent_audit_with_gaps(self):
        import random
        import audit
        rng=random.Random(50020261006)
        rows=[];last=100.0
        for i in range(1250):
            current=max(.1,last*(1+rng.uniform(-.008,.008)))
            high=max(last,current)*(1+rng.uniform(0,.015))
            low=min(last,current)*(1-rng.uniform(0,.015))
            rows.append([i*Q,str(last),str(high),str(low),str(current),'10','10','1000','1'])
            last=current
        rules=[dict(id='don20',family='donchian',n=20),dict(id='don55',family='donchian',n=55),
               dict(id='ema12',family='ema',fast=12,slow=48),dict(id='ema24',family='ema',fast=24,slow=96),
               dict(id='mom2',family='momentum',n=24,threshold=.02),dict(id='mom5',family='momentum',n=24,threshold=.05),
               dict(id='boll2',family='boll',n=20,z=2),dict(id='boll25',family='boll',n=20,z=2.5),
               dict(id='rsi',family='rsi',n=14,low=30,high=70),
               dict(id='atr',family='atr_break',n=12,atr_n=14,atr_multiple=.5)]
        independent=audit.prepare_signals(rows,rules)
        prepared=engine.prepare_rows(rows)
        audit_prepared=audit.prepare_rows(rows)
        for rule in rules:
            sig=engine.prepare_signals(prepared,rule)
            self.assertEqual(sig,independent[rule['id']])
            for product,leverage,spec in [('SPOT',1,SPOT),('CONDITIONAL_SWAP',5,SWAP),('CONDITIONAL_SWAP',10,SWAP)]:
                for horizon in [24,168]:
                    end=START+horizon*H
                    for cost in ['base','stress']:
                        cfg=dict(CONFIG,rule=rule,product=product,leverage=leverage,horizon_hours=horizon,cost=cost)
                        scoped=[r for r in rows if START-120*H<=r[0]<end]
                        for control in [False,True]:
                            result=engine.simulate(prepared,spec,funding(end),cfg,START,end,sig,control)
                            checked=audit.verify(audit_prepared if control else scoped,spec,funding(end),cfg,START,end,sig,result,control)
                            self.assertEqual(checked['status'],'PASS')
        for missing in [10*H,130*H]:
            gapped=[r for r in rows if r[0]!=missing]
            prepared=engine.prepare_rows(gapped)
            for rule in rules:
                sig=engine.prepare_signals(prepared,rule)
                self.assertEqual(sig,audit.prepare_signals(gapped,rule))
            for product,leverage,spec in [('SPOT',1,SPOT),('CONDITIONAL_SWAP',5,SWAP)]:
                cfg=dict(CONFIG,product=product,leverage=leverage)
                end=START+24*H
                result=engine.simulate(prepared,spec,funding(end),cfg,START,end,{START:1})
                self.assertEqual(result['metrics']['status'],'DATA_INVALID')
                scoped=[r for r in gapped if START-120*H<=r[0]<end]
                self.assertEqual(audit.verify(scoped,spec,funding(end),cfg,START,end,{START:1},result)['status'],'PASS')
                self.assertEqual(audit.verify(audit.prepare_rows(gapped),spec,funding(end),cfg,START,end,{START:1},result)['status'],'PASS')

    def test_spot_ignores_short_signal(self):
        result=self.run_episode(signals={START:-1,START+H:1})
        self.assertEqual(result['events'][0]['timestamp'],START+H)


if __name__=='__main__':unittest.main()
