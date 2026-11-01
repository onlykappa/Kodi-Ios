import unittest
from pathlib import Path
from check_ci_workflow import validate
class WorkflowTests(unittest.TestCase):
 def setUp(self):self.text=(Path(__file__).resolve().parents[1]/'.github/workflows/drive-upstream.yml').read_text()
 def test_approved_workflow(self):self.assertTrue(validate(self.text)['approved_template_match'])
 def test_timeout_expansion(self):
  with self.assertRaises(AssertionError):validate(self.text.replace('timeout-minutes: 5','timeout-minutes: 60'))
 def test_permissions_expansion(self):
  with self.assertRaises(AssertionError):validate(self.text.replace('permissions: {}','permissions: write-all'))
 def test_unsafe_event(self):
  with self.assertRaises(AssertionError):validate(self.text.replace('pull_request:','pull_request_target:'))
if __name__=='__main__':unittest.main()
