import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from detector import Book, ingest
from evidence import Journal, EvidenceFailure, atomic_json
from monitor import collect, Episodes
from replay import replay


class EvidenceTests(unittest.TestCase):
    def fixture(self,root):
        config=dict(symbols=['LSKUSDT'],venues=['okx','gate'],amounts_usdt=['100','500','1000'],
                    fee_scenarios={'base':{'okx':'10','gate':'10'},'higher_gate':{'okx':'10','gate':'20'}},buffer_bps='5',source_sha256={})
        atomic_json(root/'config.json',config)
        books={v:{'LSKUSDT':Book()} for v in config['venues']}
        j=Journal(root,min_free=0)
        frames={
            'okx':dict(arg={'instId':'LSK-USDT'},action='snapshot',data=[dict(bids=[['99','20']],asks=[['100','20']],ts='10000',seqId=4,prevSeqId=-1)]),
            'gate':dict(channel='spot.order_book',event='update',result=dict(s='LSK_USDT',bids=[['102','20']],asks=[['103','20']],t=10000,lastUpdateId=4))}
        for v,msg in frames.items():
            books[v]['LSKUSDT'].reset(v)
            j.append('connect',venue=v,connection_id=v,received_ms=10000,mono=10)
            ref=j.append('frame',venue=v,connection_id=v,received_ms=10000,processed_ms=10000,mono=10,raw=json.dumps(msg))
            ingest(v,msg,books[v]);b=books[v]['LSKUSDT'];b.ref=ref;b.received=10
        views={v:{s:b.view() for s,b in bs.items()} for v,bs in books.items()}
        rows=collect(views,10000,10,config)
        self.assertEqual(rows[0]['net_usdt'],'1.748')
        j.append('decision',observed_ms=10000,mono=10,results=rows)
        for event in Episodes().update(rows,10000):j.append('event',**event)
        j.append('run_end',observed_ms=10000)
        j.close()
        return j

    def test_independent_replay_and_tamper_detection(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);j=self.fixture(root)
            r=replay(root)
            self.assertTrue(r['passed'],r);self.assertTrue(r['complete'])
            self.assertEqual(r['independent_anomalies'],1)
            self.assertEqual(r['estimates_compared'],12)
            manifest=json.loads((root/'journal_manifest.json').read_text())
            manifest['files'][0]['sha256']='0'*64
            atomic_json(root/'journal_manifest.json',manifest)
            self.assertFalse(replay(root)['passed'])

    def test_missing_frame_cannot_pass_by_updating_hash(self):
        import gzip
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root)
            path=root/'journal-000000.jsonl.gz'
            rows=[json.loads(line) for line in gzip.open(path,'rt')]
            rows=[r for r in rows if not (r['kind']=='frame' and r['venue']=='gate')]
            with gzip.open(path,'wt') as f:
                for row in rows:f.write(json.dumps(row)+'\n')
            manifest=json.loads((root/'journal_manifest.json').read_text())
            manifest['files'][0]['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
            atomic_json(root/'journal_manifest.json',manifest)
            self.assertFalse(replay(root)['passed'])

    def test_storage_limit_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            journal=Journal(Path(td),max_bytes=0,min_free=0)
            with self.assertRaises(EvidenceFailure):journal.append('test')
            self.assertIsNotNone(journal.failure)


if __name__=='__main__':unittest.main()
