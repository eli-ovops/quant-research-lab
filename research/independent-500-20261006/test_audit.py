"""Synthetic invariants and tamper rejection only; never read market/PnL files."""
import copy
import math
import unittest
import audit


def fixture(path=None, hours=150):
    rows=[]
    for i in range(hours*4):
        p=100. if path is None else path(i)
        rows.append([str(i*audit.STEP),str(p),str(p+.02),str(p-.02),str(p),
                     '100','100','10000','1'])
    return rows


class AuditTests(unittest.TestCase):
    def setUp(self):
        # engine is used only to produce synthetic test fixtures.
        import engine
        self.engine=engine
        self.start=120*audit.HOUR;self.end=144*audit.HOUR
        self.spot={'instId':'BTC-USDT','instType':'SPOT','baseCcy':'BTC',
                   'lotSz':'.001','minSz':'.001','tickSz':'.01'}
        self.swap=dict(self.spot,instId='BTC-USDT-SWAP',instType='SWAP',
                       ctType='linear',settleCcy='USDT',ctVal='.01',lotSz='1',minSz='1')
        self.funding=[{'fundingTime':str(t),'realizedRate':'.0001'}
                      for t in range(112*audit.HOUR,153*audit.HOUR,8*audit.HOUR)]
        self.config={'id':'synthetic','rule':{'id':'donchian20','family':'donchian','n':20},
                     'product':'CONDITIONAL_SWAP','cost':'stress','leverage':10,'horizon_hours':24}

    def run_case(self,rows=None,config=None,signals=None,control=False,spec=None,funding=None):
        rows=fixture() if rows is None else rows
        config=self.config if config is None else config
        signals={self.start:1} if signals is None else signals
        spec=(self.spot if config['product']=='SPOT' else self.swap) if spec is None else spec
        funding=self.funding if funding is None else funding
        result=self.engine.simulate(rows,spec,funding,config,self.start,self.end,signals,control)
        checked=audit.verify(audit.prepare_rows(rows),spec,funding,config,self.start,self.end,signals,result,control)
        self.assertTrue(checked['ok'])
        return rows,spec,funding,config,signals,result

    def test_all_signal_families_and_reset(self):
        rules=[{'id':'d20','family':'donchian','n':20},{'id':'d55','family':'donchian','n':55},
               {'id':'e12','family':'ema','fast':12,'slow':48},{'id':'e24','family':'ema','fast':24,'slow':96},
               {'id':'m2','family':'momentum','n':24,'threshold':.02},
               {'id':'m5','family':'momentum','n':24,'threshold':.05},
               {'id':'b2','family':'boll','n':20,'z':2},{'id':'b25','family':'boll','n':20,'z':2.5},
               {'id':'r','family':'rsi','n':14,'low':30,'high':70},
               {'id':'a','family':'atr_break','n':12,'atr_n':14,'atr_multiple':.5}]
        rows=fixture(lambda i:100+10*math.sin(i/27)+.001*i,hours=360)
        for gaps in (False,True):
            x=copy.deepcopy(rows)
            if gaps:x[140*4][5]='0'
            independent=audit.prepare_signals(x,rules)
            for rule in rules:
                self.assertEqual(independent[rule['id']],self.engine.prepare_signals(x,rule))
                audit.verify_signals(x,rule,independent[rule['id']])
        changed=copy.deepcopy(independent['d20']);changed[self.start]=1
        with self.assertRaises(audit.AuditError):audit.verify_signals(x,rules[0],changed)

    def test_spot_long_only_and_short_swap(self):
        self.run_case(config=dict(self.config,product='SPOT',leverage=1),signals={self.start:-1,self.start+audit.HOUR:1})
        self.run_case(signals={self.start:-1})
        self.run_case(control=True)
        self.run_case(config=dict(self.config,product='SPOT',leverage=1),control=True)

    def test_funding_before_terminal_and_not_before_entry(self):
        *_,result=self.run_case()
        observed=[x for x in result['events'] if x['type']=='FUNDING']
        self.assertTrue(observed)
        self.assertNotIn(self.start,[x['timestamp'] for x in observed])
        self.assertEqual(observed[-1]['timestamp'],self.end)
        self.assertTrue(observed[-1]['terminal_price_proxy'])
        self.assertEqual(result['events'][-1]['type'],'EXIT')

    def test_adverse_breach_precedes_profitable_close(self):
        rows=fixture();rows[120*4][2:5]=['160','80','155']
        *_,result=self.run_case(rows=rows)
        self.assertEqual(result['metrics']['final_equity'],0)
        self.assertFalse(result['metrics']['target_hit'])
        self.assertEqual(result['events'][-1]['type'],'MAINTENANCE_PROXY_BREACH')
        self.assertEqual(result['metrics']['true_target'],'UNKNOWN')

    def test_actual_exit_after_target_close_decides_success(self):
        rows=fixture();rows[120*4][2:5]=['104','99.98','104']
        *_,result=self.run_case(rows=rows)
        exit_event=next(x for x in result['events'] if x['type']=='EXIT')
        self.assertEqual(exit_event['timestamp'],self.start+audit.STEP)
        self.assertEqual(exit_event['reason'],'TARGET_CLOSE_SIGNAL')
        self.assertFalse(result['metrics']['target_hit'])

    def test_invalid_rows_funding_specs_and_minimum(self):
        rows=fixture();rows.pop(120*4)
        *_,result=self.run_case(rows=rows)
        self.assertEqual(result['metrics']['status'],'DATA_INVALID')
        *_,result=self.run_case(funding=[])
        self.assertEqual(result['metrics']['status'],'DATA_INVALID')
        *_,result=self.run_case(spec=dict(self.swap,ctVal='nan'))
        self.assertEqual(result['metrics']['status'],'SPEC_INVALID')
        *_,result=self.run_case(spec=dict(self.swap,minSz='10000000'))
        self.assertEqual(result['metrics']['status'],'ORDER_REJECTED')

    def test_missing_first_entry_and_event_or_metric_tampering(self):
        rows,spec,funding,config,signals,result=self.run_case()
        for kind in ('entry','fee','equity','funding','target','unknown'):
            x=copy.deepcopy(result)
            if kind=='entry':x['events'].pop(0)
            elif kind=='fee':x['events'][0]['fee']+=1
            elif kind=='equity':x['equity'][2]['cash']+=1
            elif kind=='funding':next(e for e in x['events'] if e['type']=='FUNDING')['rate']+=.001
            elif kind=='target':x['metrics']['target_hit']=not x['metrics']['target_hit']
            else:x['metrics']['true_liquidation']='FALSE'
            with self.subTest(kind=kind),self.assertRaises(audit.AuditError):
                audit.verify(rows,spec,funding,config,self.start,self.end,signals,x)
        empty=self.engine.simulate(rows,spec,funding,config,self.start,self.end,{})
        with self.assertRaises(audit.AuditError):audit.verify(rows,spec,funding,config,self.start,self.end,signals,empty)


if __name__=='__main__':unittest.main()
