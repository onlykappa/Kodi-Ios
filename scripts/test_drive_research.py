import copy,json,unittest
from pathlib import Path
from check_drive_research import validate
ROOT=Path(__file__).resolve().parents[1]
class ResearchPolicyTests(unittest.TestCase):
 def setUp(self):
  self.lock=json.loads((ROOT/'migration/google-drive/source-lock.json').read_text())
  self.research=json.loads((ROOT/'reports/google-drive-research.json').read_text())
  self.suite=json.loads((ROOT/'reports/drive-upstream-validation.json').read_text())
  self.roadmap=(ROOT/'ROADMAP.md').read_text()
 def run_check(self):return validate(self.lock,self.research,self.suite,self.roadmap)
 def test_current_evidence(self):self.assertTrue(self.run_check()['research_consistent'])
 def test_unapproved_architecture(self):
  self.research['owner_approved']=False
  with self.assertRaises(AssertionError):self.run_check()
 def test_false_readiness(self):
  self.research['phase3_ready']=True
  with self.assertRaises(AssertionError):self.run_check()
 def test_scope_expansion(self):
  self.lock['relay']['scope']='https://www.googleapis.com/auth/drive'
  with self.assertRaises(AssertionError):self.run_check()
 def test_hidden_errors(self):
  self.suite['suite_passed']=True
  with self.assertRaises(AssertionError):self.run_check()
if __name__=='__main__':unittest.main()
