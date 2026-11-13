import unittest
from publication_wrapper import metadata_for_source
class T(unittest.TestCase):
 def test_current008_schema_earlier_than_start(self):
  p={'run_id':'r8','source':'job008','schema016_freeze_UTC':'2026-10-06T20:42:39+00:00','cost_rule_UTC':'2026-10-06T20:20:25+00:00'};i={'run_id':'r8','start_utc':'2026-10-06T21:13:13+00:00'};m=metadata_for_source(p,i);self.assertFalse(m['schema_cut_later_than_capture_start']);self.assertTrue(m['rule_cut_earlier_than_capture']);self.assertEqual(m['current_source_run_id'],'r8');self.assertTrue(m['status'].startswith('CLOSED_JOB008'))
 def test_prior_time_or_mismatched_identity_never_silently_reused(self):
  p={'run_id':'r8','source':'job008','schema016_freeze_UTC':'2026-10-06T20:42:39+00:00','cost_rule_UTC':'2026-10-06T20:20:25+00:00'};self.assertTrue(metadata_for_source(p,{'run_id':'r8','start_utc':'2026-10-06T20:30:00+00:00'})['schema_cut_later_than_capture_start']);self.assertRaises(ValueError,metadata_for_source,p,{'run_id':'r7','start_utc':'2026-10-06T21:13:13+00:00'})
if __name__=='__main__':unittest.main()
