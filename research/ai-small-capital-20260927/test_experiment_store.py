import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from paper_ledger import commit_decision
from experiment_store import process
from test_paper_experiment import fixture


class Store(unittest.TestCase):
    def test_restart_duplicate_and_atomic_failure(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);db=root/'experiment.sqlite'
            d,books,specs,_=fixture(1000)
            p=commit_decision(root,d);time.sleep(.003)
            for b in books.values():b['ts']=time.time_ns()//1000000
            s=process(db,p,books,specs)
            self.assertEqual(len(s['scenarios']),4)
            with self.assertRaisesRegex(ValueError,'DUPLICATE'):process(db,p,books,specs)
            time.sleep(.003)
            p2=commit_decision(root,{**d,'slot':'2000'});time.sleep(.003)
            for b in books.values():b['ts']=time.time_ns()//1000000
            with patch('experiment_store.step',side_effect=RuntimeError('injected crash')):
                with self.assertRaises(RuntimeError):process(db,p2,books,specs)
            with sqlite3.connect(db) as c:
                self.assertEqual(c.execute('SELECT count(*) FROM events').fetchone()[0],1)
            s2=process(db,p2,books,specs)
            self.assertEqual(len(s2['slots']),2)
            with sqlite3.connect(db) as c:
                c.execute("UPDATE events SET body='{}' WHERE seq=1")
            with self.assertRaisesRegex(ValueError,'INTEGRITY'):process(db,p2,books,specs)

    def test_code_change_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            root=Path(root);d,books,specs,_=fixture(1000)
            p=commit_decision(root,d)
            process(root/'db.sqlite',p,{},specs)
            with patch('experiment_store.implementation_hash',return_value='changed'):
                with self.assertRaisesRegex(ValueError,'IMPLEMENTATION_CHANGED'):
                    process(root/'db.sqlite',p,{},specs)


if __name__=='__main__':unittest.main()
