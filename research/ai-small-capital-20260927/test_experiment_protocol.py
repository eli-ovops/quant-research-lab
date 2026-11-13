import unittest
from experiment_protocol import DAY_MS,validate_window,coverage


class Protocol(unittest.TestCase):
    def setUp(self):
        self.p={'days':30,'interval_ms':DAY_MS,'start_ms':1000,
                'end_ms':1000+30*DAY_MS,'window_ms':600000,
                'model_identifier':'TEST_FIXTURE','prompt_sha256':'fixture'}
        self.d={'window_index':0,'slot':'1000','committed_ms':1100}

    def test_window_and_deadline_boundaries(self):
        validate_window(self.p,self.d,1101)
        for now,error in [(1000,'EARLY'),(601000,'EARLY'),(self.p['end_ms'],'ENDED')]:
            with self.assertRaisesRegex(ValueError,error):validate_window(self.p,self.d,now)
        with self.assertRaisesRegex(ValueError,'MODEL_NOT_FROZEN'):
            validate_window({**self.p,'model_identifier':'UNKNOWN'},self.d,1101)

    def test_missing_windows_not_backfilled(self):
        c=coverage(self.p,[self.d],self.p['end_ms'])
        self.assertEqual(c['observed_windows'],1)
        self.assertEqual(c['missing_windows'],list(range(1,30)))
        self.assertTrue(c['deadline_reached'])
        self.assertFalse(c['all_windows_present'])


if __name__=='__main__':unittest.main()
