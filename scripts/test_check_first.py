"""Owner (build-187 log): Interstellar was converted and uploaded overnight, then its last check on Drive (reading the
new file's index back, 120 s at most) timed out on a slow line, and the retry waited behind the next movie's hours of
conversion. A movie that only needs checking goes first, and the check is tried three times."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import prepare_downloads as prep

class CheckFirst(unittest.TestCase):
 def test_order(self):
  jobs={'a':{'source':{'name':'Fall.2.2026.mkv'}},
        'b':{'source':{'name':'Interstellar.2014.mkv'},'cloud_output':{'0':{'id':'x','size':'1','md5Checksum':'m'}}},
        'c':{'source':{'name':'Now.mkv'},'priority':5}}
  self.assertEqual([k for k,_ in sorted(jobs.items(),key=lambda p:prep.order_key(*p))],['c','b','a'])   # Start now still wins
 def test_three_tries(self):
  s=(LIB/'prepare_cloud.py').read_text()
  self.assertIn("for tries in range(3):",s);self.assertIn("if 'timed out' not in str(error) or tries==2:raise",s)

if __name__=='__main__':unittest.main()
