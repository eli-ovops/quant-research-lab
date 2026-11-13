import unittest
import copy
import random
import math
import engine

Q,H=engine.QUARTER,engine.HOUR
START=120*H
SPOT={'instId':'BTC-USDT','instType':'SPOT','baseCcy':'BTC','quoteCcy':'USDT','tickSz':'.01','lotSz':'.001','minSz':'.001'}
SWAP={'instId':'BTC-USDT-SWAP','instType':'SWAP','ctType':'linear','settleCcy':'USDT','ctValCcy':'BTC','ctVal':'.01','tickSz':'.01','lotSz':'1','minSz':'1'}
CFG={'product':'SPOT','leverage':1,'horizon_hours':24,'cost':'base','rule':{'id':'scalp','family':'scalp','rsi_n':7,'threshold':20}}


def fixture(hours=300,price=100):
    return [[t,str(price),str(price+.1),str(price-.1),str(price),'10','10','1000','1'] for t in range(0,hours*H,Q)]


def funding(end):return [{'fundingTime':t,'realizedRate':'.0001'} for t in range(START,end+8*H,8*H)]


def opportunities(end,direction=1,atr=.005):
    return {t:{'direction':direction,'atr_fraction':atr} for t in range(START,end,H//4)}


class EngineTests(unittest.TestCase):
    def simulate(self,rows=None,cfg=None,spec=None,signals=None,control=False):
        cfg=cfg or CFG;end=START+cfg['horizon_hours']*H
        return engine.simulate(rows if rows is not None else fixture(),spec or SPOT,funding(end),cfg,START,end,
                               signals if signals is not None else opportunities(end),control)

    def assert_ledger(self,result):
        cash=500.;base=contracts=0.
        for e in result['events']:
            cash+=e['cash_delta'];base+=e['base_delta'];contracts+=e['contract_delta']
            self.assertAlmostEqual(cash,e['cash_after'],places=7)
            self.assertAlmostEqual(base,e['base_after'],places=7)
            self.assertAlmostEqual(contracts,e['contracts_after'],places=7)
            self.assertGreaterEqual(cash,-1e-8)
        self.assertAlmostEqual(sum(e.get('fee',0) for e in result['events']),result['metrics']['fees'])
        self.assertAlmostEqual(sum(e['cash_delta'] for e in result['events'] if e['type']=='FUNDING'),result['metrics']['funding'])
        self.assertEqual(result['metrics']['trade_count'],len(result['metrics']['trade_pnls']))
        self.assertAlmostEqual(result['equity'][-1]['equity'],result['metrics']['final_equity'])

    def test_precision(self):
        self.assertEqual(engine.adverse_price(.09,'sell',.001,'.00001'),.08991)
        self.assertEqual(engine.adverse_price(70,'sell',.001,'.01'),69.93)

    def test_multitrade_cap_cooldown_dust_and_costs(self):
        result=self.simulate();self.assert_ledger(result)
        entries=[e for e in result['events'] if e['type']=='ENTRY']
        exits=[e for e in result['events'] if e['type']=='EXIT']
        self.assertEqual(len(entries),8);self.assertEqual(len(exits),8)
        for old,new in zip(exits,entries[1:]):self.assertGreaterEqual(new['timestamp'],old['timestamp']+Q)
        self.assertGreater(result['metrics']['terminal_residual_base'],0)
        self.assertAlmostEqual(sum(result['metrics']['trade_pnls']),result['metrics']['final_equity']-500)
        self.assertLess(result['metrics']['final_equity'],500)

    def test_seven_day_entry_cap40(self):
        result=self.simulate(cfg=dict(CFG,horizon_hours=168))
        self.assertEqual(result['metrics']['entry_count'],40)
        self.assertEqual(result['metrics']['trade_count'],40)
        self.assert_ledger(result)

    def test_martingale_three_losses_stop_and_stakes(self):
        cfg=dict(CFG,rule={'family':'martingale'},horizon_hours=168)
        result=self.simulate(cfg=cfg);self.assert_ledger(result)
        entries=[e for e in result['events'] if e['type']=='ENTRY']
        self.assertEqual(len(entries),3)
        self.assertEqual(result['metrics']['exit_reason'],'MARTINGALE_THREE_LOSSES')
        self.assertEqual(result['metrics']['loss_streak'],3)
        self.assertTrue(result['metrics']['halted'])
        self.assertTrue(all(p<0 for p in result['metrics']['trade_pnls']))
        self.assertAlmostEqual(entries[0]['budget'],100)
        self.assertGreater(entries[1]['budget'],entries[0]['budget']*1.9)
        self.assertGreater(entries[2]['budget'],entries[1]['budget']*1.9)
        self.assertTrue(all(e['allocation_fraction']<=.95+1e-10 for e in entries))
        exits=[e for e in result['events'] if e['type']=='EXIT']
        for old,new in zip(exits,entries[1:]):self.assertGreaterEqual(new['timestamp'],old['timestamp']+4*Q)

    def test_target_queued_exit_next_open_and_no_restart(self):
        rows=fixture();i=START//Q
        rows[i][1:5]=['100','150','99','150'];rows[i+1][1:5]=['149','150','148','149']
        result=self.simulate(rows=rows);self.assert_ledger(result)
        self.assertEqual(result['events'][1]['timestamp'],START+Q)
        self.assertEqual(result['events'][1]['reason'],'ACCOUNT_TARGET')
        self.assertTrue(result['metrics']['halted']);self.assertTrue(result['metrics']['target_hit'])
        self.assertEqual(result['metrics']['entry_count'],1)

    def test_account_stop_and_price_gap_allowance(self):
        rows=fixture();i=START//Q
        rows[i][1:5]=['100','101','39','40'];rows[i+1][1:5]=['30','31','29','30']
        result=self.simulate(rows=rows)
        self.assertEqual(result['metrics']['entry_count'],1)
        self.assertEqual(result['metrics']['exit_reason'],'ACCOUNT_STOP')
        self.assertTrue(result['metrics']['halted']);self.assertLess(result['metrics']['final_equity'],250)
        self.assertFalse(result['metrics']['target_hit']);self.assert_ledger(result)

    def test_swap_funding_by_trade_long_and_short(self):
        cfg=dict(CFG,product='CONDITIONAL_SWAP',leverage=3,rule={'family':'trend'})
        for direction in [-1,1]:
            result=self.simulate(cfg=cfg,spec=SWAP,signals=opportunities(START+24*H,direction,.05))
            self.assert_ledger(result)
            charges=[e for e in result['events'] if e['type']=='FUNDING']
            self.assertEqual([e['timestamp'] for e in charges],[START+8*H,START+16*H,START+24*H])
            self.assertTrue(all(e['cash_delta']*direction<0 for e in charges))
            self.assertTrue(charges[-1]['terminal_price_proxy'])
            self.assertEqual(result['events'][-1]['type'],'EXIT')
            self.assertEqual(result['metrics']['true_liquidation'],'UNKNOWN')
            self.assertAlmostEqual(sum(result['metrics']['trade_pnls']),result['metrics']['final_equity']-500)

    def test_adverse_extreme_maintenance_beats_profitable_close(self):
        rows=fixture();i=START//Q;rows[i][1:5]=['100','200','1','180']
        cfg=dict(CFG,product='CONDITIONAL_SWAP',leverage=10)
        result=self.simulate(rows=rows,cfg=cfg,spec=SWAP)
        self.assertEqual(result['metrics']['final_equity'],0)
        self.assertEqual(result['metrics']['entry_count'],1)
        self.assertEqual(result['metrics']['trade_pnls'],[-500])
        self.assertEqual(result['metrics']['loss_streak'],1)
        self.assertEqual(result['metrics']['exit_reason'],'MAINTENANCE_PROXY_BREACH')
        self.assert_ledger(result)

    def test_hold_bar_exit_and_terminal_proxy(self):
        result=self.simulate(signals={START:{'direction':1,'atr_fraction':.005}})
        exit_event=result['events'][-1]
        self.assertEqual(exit_event['timestamp'],START+8*Q)
        self.assertEqual(exit_event['reason'],'TRADE_TIMEOUT')
        cfg=dict(CFG,rule={'family':'trend'})
        result=self.simulate(cfg=cfg,signals={START:{'direction':1,'atr_fraction':.05}})
        self.assertEqual(result['events'][-1]['timestamp'],START+24*H)
        self.assertEqual(result['events'][-1]['reason'],'HORIZON_TERMINAL')
        self.assertTrue(result['events'][-1]['terminal_proxy'])

    def test_minimum_invalid_and_prepared(self):
        result=self.simulate(spec=dict(SPOT,minSz='10000'))
        self.assertEqual(result['metrics']['entry_count'],0)
        self.assertEqual(result['metrics']['final_equity'],500)
        self.assertTrue(all(e['type']=='REJECTED' for e in result['events']))
        rows=fixture();rows[10][5]='0'
        result=self.simulate(rows=rows)
        self.assertEqual(result['metrics']['status'],'DATA_INVALID');self.assertIsNone(result['metrics']['final_equity'])
        self.assertEqual(self.simulate(rows=fixture()),self.simulate(rows=engine.prepare_rows(fixture())))
        cfg=dict(CFG,product='CONDITIONAL_SWAP',leverage=3)
        end=START+24*H
        bad=engine.simulate(fixture(),SWAP,[],cfg,START,end,opportunities(end))
        self.assertEqual(bad['metrics']['status'],'DATA_INVALID')

    def test_controls_same_family_parameter_and_cost_seed(self):
        cfg=dict(CFG,product='CONDITIONAL_SWAP',leverage=3)
        a=engine._control_direction(SWAP,cfg,START,START)
        b=engine._control_direction(SWAP,dict(cfg,cost='stress',rule={'family':'scalp','rsi_n':10}),START,START)
        self.assertEqual(a,b)
        maps={t:{'direction':0,'atr_fraction':.005} for t in range(START,START+24*H,H)}
        result=self.simulate(signals=maps,control=True)
        self.assertEqual(result['metrics']['entry_count'],3)
        self.assertEqual([e['timestamp'] for e in result['events'] if e['type']=='ENTRY'],[START,START+8*H,START+16*H])

    def test_all30_registered_rule_maps_future_and_control_atr(self):
        import json
        from pathlib import Path
        protocol=json.loads(Path(__file__).with_name('protocol.json').read_text())
        rules={c['rule']['id']:c['rule'] for c in protocol['configs']}
        self.assertEqual(len(rules),30)
        rng=random.Random(50020261006);rows=fixture();last=100.
        for r in rows:
            c=max(1.,last*(1+rng.uniform(-.005,.005)))
            r[1:5]=[str(last),str(max(last,c)+.2),str(min(last,c)-.2),str(c)]
            r[5]=str(10+rng.randrange(5));last=c
        changed=copy.deepcopy(rows);cut=180*H
        for r in changed:
            if r[0]>=cut:r[1:5]=['1000','1001','999','1000']
        prepared=engine.prepare_rows(rows);reference_maps={}
        for rule in rules.values():
            a=engine.prepare_signals(prepared,rule);b=engine.prepare_signals(changed,rule)
            self.assertEqual({t:v for t,v in a.items() if t<=cut},{t:v for t,v in b.items() if t<=cut})
            self.assertIn(START,a)
            atr={t:v['atr_fraction'] for t,v in a.items()}
            if rule['family'] in reference_maps:self.assertEqual(atr,reference_maps[rule['family']])
            reference_maps[rule['family']]=atr

    def test_funding_before_open_gap_breach_overrides_target(self):
        rows=fixture();i=(START+8*H-Q)//Q
        rows[i][1:5]=['100','140','99','140'];rows[i+1][1:5]=['1','2','.9','1']
        cfg=dict(CFG,product='CONDITIONAL_SWAP',leverage=10,rule={'family':'trend'})
        result=self.simulate(rows=rows,cfg=cfg,spec=SWAP)
        same=[e['type'] for e in result['events'] if e['timestamp']==START+8*H]
        self.assertEqual(same,['FUNDING','MAINTENANCE_PROXY_BREACH'])
        self.assertEqual(result['metrics']['final_equity'],0)
        self.assertFalse(result['metrics']['target_hit']);self.assert_ledger(result)

    def test_future_perturbation_all_six_families(self):
        rng=random.Random(50020261006);rows=fixture()
        for i,r in enumerate(rows):
            p=100+4*math.sin(i/19)+rng.uniform(-1,1)
            r[1:5]=[str(p-.1),str(p+1),str(p-1),str(p)];r[5]=str(10+rng.randrange(5))
        changed=copy.deepcopy(rows);cut=180*H
        for r in changed:
            if r[0]>=cut:r[1:5]=['1000','1001','999','1000']
        rules=[dict(family='trend',fast=8,slow=32,er_min=.2),dict(family='breakout',n=12,volume_multiple=1),
               dict(family='range',n=20,z=2,er_max=.25),dict(family='martingale',n=20,z=1.5,er_max=.4),
               dict(family='pattern',shape='engulf'),dict(family='scalp',rsi_n=7,threshold=20)]
        for rule in rules:
            a=engine.prepare_signals(rows,rule);b=engine.prepare_signals(changed,rule)
            self.assertEqual({t:v for t,v in a.items() if t<=cut},{t:v for t,v in b.items() if t<=cut})
            self.assertTrue(all('atr_fraction' in v for v in a.values()))
            self.assertTrue(any(v['direction']==0 for v in a.values()))
            self.assertEqual(a,engine.prepare_signals(engine.prepare_rows(rows),rule))

if __name__=='__main__':unittest.main()
