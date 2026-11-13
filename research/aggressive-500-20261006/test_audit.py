"""Independent synthetic tests. Read frozen rules only, never market or PnL files."""
import copy
import json
import random
import unittest
from pathlib import Path
import audit

H,Q=audit.HOUR,audit.STEP
START=120*H
SPOT={'instId':'BTC-USDT','baseCcy':'BTC','quoteCcy':'USDT','instType':'SPOT',
      'tickSz':'.01','lotSz':'.001','minSz':'.001'}
SWAP={'instId':'BTC-USDT-SWAP','ctValCcy':'BTC','settleCcy':'USDT','instType':'SWAP','ctType':'linear',
      'ctVal':'.01','lever':'20','tickSz':'.01','lotSz':'1','minSz':'1'}


def frozen():
    return json.loads(Path(__file__).with_name('protocol.json').read_text())


def fixture(hours=310,change=None):
    result=[]
    for i in range(hours*4):
        p=100. if change is None else change(i)
        result.append([str(i*Q),str(p),str(p+.1),str(p-.1),str(p),'10','10','1000','1'])
    return result


def funding(end):
    return [{'fundingTime':t,'realizedRate':'.0001'} for t in range(START,end+8*H,8*H)]


class AuditTests(unittest.TestCase):
    def setUp(self):
        import engine
        self.engine=engine
        self.cfg={'product':'SPOT','leverage':1,'horizon_hours':24,'cost':'base',
                  'rule':{'id':'scalp_0','family':'scalp','rsi_n':5,'threshold':20}}

    def checked(self,rows=None,config=None,signals=None,spec=None,fund=None,control=False):
        config=self.cfg if config is None else config;end=START+config['horizon_hours']*H
        rows=fixture() if rows is None else rows
        spec=(SPOT if config['product']=='SPOT' else SWAP) if spec is None else spec
        sig={t:{'direction':1,'atr_fraction':.003} for t in range(START,end,Q)} if signals is None else signals
        fund=funding(end) if fund is None else fund
        expected=self.engine.simulate(self.engine.prepare_rows(rows),spec,fund,config,START,end,sig,control)
        receipt=audit.verify(audit.prepare_rows(rows),spec,fund,config,START,end,sig,expected,control)
        self.assertTrue(receipt['ok'])
        return rows,spec,fund,config,end,sig,expected

    def test_twenty_leverage_keeps_position_below250_until_terminal(self):
        config=dict(self.cfg,product='CONDITIONAL_SWAP',leverage=20,
                    rule={'id':'trend_1','family':'trend','fast':12,'slow':48,'er_min':.2})
        raw=fixture();end=START+24*H
        for i in range(START//Q,end//Q):raw[i][1:5]=['97','97.1','96.99','97']
        raw[START//Q][1:5]=['100','100.1','96.99','97']
        signals={START:{'direction':1,'atr_fraction':.05}}
        *_,result=self.checked(rows=raw,config=config,signals=signals)
        self.assertLess(result['equity'][0]['equity'],250)
        self.assertGreater(result['metrics']['final_equity'],0)
        self.assertLess(result['metrics']['final_equity'],250)
        self.assertEqual(result['metrics']['exit_reason'],'HORIZON_TERMINAL')
        self.assertFalse(result['metrics']['halted'])
        self.assertEqual(result['events'][-1]['timestamp'],end)
        self.assertEqual(result['metrics']['entry_count'],1)

    def test_independent_leverage_rejection_and_gate_tamper(self):
        config=dict(self.cfg,product='CONDITIONAL_SWAP',leverage=20)
        for spec in [dict(SWAP,lever='19.99'),dict(SWAP,lever='unknown'),
                     {k:v for k,v in SWAP.items() if k!='lever'}]:
            rows,_,fund,cfg,end,sig,result=self.checked(config=config,spec=spec)
            self.assertEqual(result['metrics']['status'],'SPEC_INVALID')
            self.assertFalse(result['events'])
            altered=copy.deepcopy(result);altered['metrics']['exit_reason']='missing_spec'
            with self.assertRaises(audit.AuditError):audit.verify(rows,spec,fund,cfg,START,end,sig,altered)

    def test_conversion_catches_never_swallow_audit_rejections(self):
        cases=[dict(spec=dict(SPOT,instId='ETH-USDT')),
               dict(spec=dict(SPOT,tickSz='0')),
               dict(config=dict(self.cfg,product='CONDITIONAL_SWAP',leverage=20),
                    fund=[{'fundingTime':START,'realizedRate':'NaN'}])]
        for kwargs in cases:
            rows,spec,fund,cfg,end,sig,result=self.checked(**kwargs)
            altered=copy.deepcopy(result)
            altered['metrics']['exit_reason']='missing_funding_coverage' if result['metrics']['status']=='DATA_INVALID' else 'missing_spec'
            with self.subTest(reason=result['metrics']['exit_reason']),self.assertRaises(audit.AuditError):
                audit.verify(rows,spec,fund,cfg,START,end,sig,altered)

    def test_continuous_balance_dust_cooldown_and_caps(self):
        for h,cap in ((24,8),(168,40)):
            *_,r=self.checked(config=dict(self.cfg,horizon_hours=h))
            self.assertEqual(r['metrics']['entry_count'],cap)
            entries=[e for e in r['events'] if e['type']=='ENTRY'];exits=[e for e in r['events'] if e['type']=='EXIT']
            for i,e in enumerate(entries[1:]):
                self.assertAlmostEqual(e['budget'],.95*exits[i]['cash_after'])
                self.assertGreaterEqual(e['timestamp'],exits[i]['timestamp']+Q)
            self.assertGreater(r['metrics']['terminal_residual_base'],0)

    def test_martingale_three_losses_and_gain_reset(self):
        c=dict(self.cfg,rule={'id':'martingale_0','family':'martingale','n':20,'z':1.5,'er_max':.25})
        raw=fixture(change=lambda i:100 if i<480 else 100-.08*(i-480))
        *_,r=self.checked(rows=raw,config=c)
        entries=[e for e in r['events'] if e['type']=='ENTRY']
        self.assertEqual(len(entries),3);self.assertTrue(r['metrics']['halted'])
        self.assertEqual(r['metrics']['exit_reason'],'MARTINGALE_THREE_LOSSES')
        for i,e in enumerate(entries):
            self.assertLessEqual(e['allocation_fraction'],.95)
            self.assertAlmostEqual(e['allocation_fraction'],.2*2**i,places=3)
        raw=fixture(change=lambda i:100 if i<480 else 100+.08*(i-480))
        *_,g=self.checked(rows=raw,config=c)
        e=[e for e in g['events'] if e['type']=='ENTRY']
        self.assertGreater(len(e),1)
        self.assertTrue(all(x['loss_streak']==0 for x in e))

    def test_proxy_precedence_short_and_funding_terminal(self):
        c=dict(self.cfg,product='CONDITIONAL_SWAP',leverage=10,
               rule={'id':'trend_0','family':'trend','fast':8,'slow':32,'er_min':.2})
        raw=fixture();raw[480][2:5]=['150','70','145']
        *_,r=self.checked(rows=raw,config=c)
        self.assertEqual(r['metrics']['final_equity'],0)
        self.assertFalse(r['metrics']['target_hit'])
        self.assertEqual(r['metrics']['true_liquidation'],'UNKNOWN')
        end=START+24*H
        signals={START:{'direction':-1,'atr_fraction':.05}}
        *_,r=self.checked(config=c,signals=signals)
        self.assertEqual(next(x for x in r['events'] if x['type']=='ENTRY')['direction'],-1)
        f=[e for e in r['events'] if e['type']=='FUNDING']
        self.assertNotIn(START,[e['timestamp'] for e in f])
        self.assertEqual(f[-1]['timestamp'],end)
        self.assertTrue(f[-1]['terminal_price_proxy'])

    def test_registered_maps_and_random64_multi_ledgers(self):
        p=frozen();rules=list({c['rule']['id']:c['rule'] for c in p['configs']}.values())
        rng=random.Random(50020261006);raw=[];previous=100.
        for i in range(1300):
            o=previous+rng.uniform(-.2,.2);c=max(30.,o+rng.uniform(-1.4,1.4));h=max(o,c)+rng.uniform(.01,.8);l=min(o,c)-rng.uniform(.01,.8)
            raw.append([str(i*Q),str(o),str(h),str(l),str(c),str(rng.uniform(1,30)),'10','1000','1']);previous=c
        maps=audit.prepare_signals(raw,rules)
        for rule in rules:
            audit.compare_signals(self.engine.prepare_signals(raw,rule),maps[rule['id']])
        ep,ap=self.engine.prepare_rows(raw),audit.prepare_rows(raw)
        for config in p['configs']:
            end=START+config['horizon_hours']*H;spec=SPOT if config['product']=='SPOT' else SWAP
            for control in (False,True):
                result=self.engine.simulate(ep,spec,funding(end),config,START,end,maps[config['rule']['id']],control)
                audit.verify(ap,spec,funding(end),config,START,end,maps[config['rule']['id']],result,control)
        raw[600][5]='0'
        maps=audit.prepare_signals(raw,rules)
        for rule in rules:audit.compare_signals(self.engine.prepare_signals(raw,rule),maps[rule['id']])

    def test_tampered_reentry_budget_cash_atr_pnl_and_unknown(self):
        rows,spec,fund,config,end,sig,r=self.checked()
        for kind in ('budget','cash','cooldown','atr','tradepnl','count','missing_entry'):
            bad=copy.deepcopy(r);entry=[e for e in bad['events'] if e['type']=='ENTRY']
            if kind=='budget':entry[1]['budget']+=20
            elif kind=='cash':bad['equity'][20]['cash']+=1
            elif kind=='cooldown':entry[1]['timestamp']-=Q
            elif kind=='atr':entry[0]['atr_fraction']+=.01
            elif kind=='tradepnl':bad['metrics']['trade_pnls'][0]+=1
            elif kind=='count':bad['metrics']['entry_count']-=1
            else:bad['events'].remove(entry[0])
            with self.subTest(kind=kind),self.assertRaises(audit.AuditError):
                audit.verify(rows,spec,fund,config,START,end,sig,bad)
        badmap=copy.deepcopy(sig);badmap[START]['direction']=-1
        with self.assertRaises(audit.AuditError):audit.compare_signals(badmap,sig)

    def test_invalid_gate_spec_funding_and_missing_warmup(self):
        rows=fixture();rows.pop(480)
        *_,r=self.checked(rows=rows)
        self.assertEqual(r['metrics']['status'],'DATA_INVALID')
        *_,r=self.checked(spec=dict(SPOT,instId='ETH-USDT'))
        self.assertEqual(r['metrics']['status'],'SPEC_INVALID')
        *_,r=self.checked(config=dict(self.cfg,product='CONDITIONAL_SWAP',leverage=3),fund=[])
        self.assertEqual(r['metrics']['status'],'DATA_INVALID')


if __name__=='__main__':unittest.main()
