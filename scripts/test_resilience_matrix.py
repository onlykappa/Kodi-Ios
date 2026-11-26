"""Runs the step 13 matrix and checks the committed sanitized report still describes it (host checks only)."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import resilience_matrix as m
ROOT=Path(__file__).resolve().parents[1]

class Matrix(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.rows=m.run()
 def test_every_scenario_passes_or_is_skipped_with_a_reason(self):
  bad=[r for r in self.rows if r['status']=='fail'];self.assertEqual(bad,[],bad)
  self.assertGreaterEqual(len(self.rows),24);self.assertEqual({r['group'] for r in self.rows},{'outage','correctness','privacy','hygiene'})
 def test_the_committed_report_matches_this_run(self):
  report=json.loads((ROOT/'reports/source-resilience-matrix.json').read_text())['rows']
  # A scenario that needs a network-less namespace is 'pass' where `unshare -rn` works and 'skipped' where it does not (GitHub's runners): either is a match.
  env=lambda r:r['status'] if 'network-less namespace' not in r['scenario'] or r['status']=='fail' else 'pass-or-skipped'
  now=[(r['group'],r['scenario'],env(r)) for r in self.rows];kept=[(r['group'],r['scenario'],env(r)) for r in report]
  self.assertEqual(now,kept,'refresh with: python3 scripts/resilience_matrix.py --write')
 def test_the_report_holds_no_secret_link_or_address(self):
  text=(ROOT/'reports/source-resilience-matrix.json').read_text()
  for bad in (m.SECRET,'http://','https://','magnet:','Bearer','apikey='):self.assertNotIn(bad,text,bad)
 def test_no_non_loopback_connection_was_attempted(self):self.assertEqual(m.TRIP,[])

if __name__=='__main__':unittest.main()
