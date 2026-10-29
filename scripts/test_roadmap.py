import unittest
from pathlib import Path
from check_roadmap import summarize,validate,progress_line
class RoadmapTests(unittest.TestCase):
 def setUp(self):self.text=(Path(__file__).resolve().parents[1]/'ROADMAP.md').read_text()
 def test_status_change(self):
  import re
  original=summarize(self.text)
  text=re.sub(r'- \[x\] (P\d-\d{3} — .*?Status:) COMPLETE\.',r'- [ ] \1 NOT STARTED.',self.text,count=1,flags=re.S)
  result=summarize(text);self.assertEqual(result['completed_count'],original['completed_count']-1)
  line=progress_line(result);text=re.sub(r'Progress: .*',line,text,count=1)
  validate(text,line)
 def test_add_task(self):
  before=summarize(self.text)
  text=self.text+'\n- [ ] P5-999 — Regression fixture\n  - Status: NOT STARTED. Dependencies: P5-001.\n  - Deliverable and acceptance: fixture\n  - Validation: fixture\n  - Evidence: pending.\n'
  result=summarize(text);self.assertEqual(result['tasks'],before['tasks']+1)
  import re
  validate(re.sub(r'Progress: .*',progress_line(result),text,count=1),progress_line(result))
 def test_inconsistent_status(self):
  with self.assertRaises(AssertionError):summarize(self.text.replace('- [x]','- [ ]',1))
 def test_stale_tracker(self):
  with self.assertRaises(AssertionError):validate(self.text,'Progress: invalid')
if __name__=='__main__':unittest.main()
