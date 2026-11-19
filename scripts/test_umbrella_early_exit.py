"""ISSUE-340 (owner log 218a6000: "route=direct wait_ms=5017 ready=False blocks=0/3 … bytes=3145728", Umbrella 15.8 s): the
cache route waited its whole 5 s for opening blocks that could not finish at ~0.6 MB/s. It now gives up after 1.5 s
when, at the speed so far, the blocks cannot be complete in time (or nothing arrived)."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm

class EarlyExit(unittest.TestCase):
 def test_the_owners_case_gives_up_early(self):
  st={'opening_blocks':3,'read_bytes':int(.6*1024*1024*1.5)}
  self.assertTrue(rm.hopeless(st,1.5,5.0))
 def test_nothing_arrived(self):
  self.assertTrue(rm.hopeless({'opening_blocks':3,'read_bytes':0},1.6,5.0))
 def test_a_fast_source_keeps_waiting(self):
  st={'opening_blocks':3,'read_bytes':8*1024*1024}   # ~5.3 MB/s: 4 MB more within the budget
  self.assertFalse(rm.hopeless(st,1.5,5.0))
 def test_never_before_the_first_look(self):
  self.assertFalse(rm.hopeless({'opening_blocks':3,'read_bytes':0},1.0,5.0))
 def test_wired_into_the_wait(self):
  self.assertIn('if hopeless(st,clock()-began,limit):return False',(ROOT/'migration/bundled-bootstrap/resources/lib/remote_media.py').read_text())

if __name__=='__main__':unittest.main()
