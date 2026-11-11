"""Owner (build 192): "all my stuff is re converting even though it says ready in library status". Movies prepared
before build 191 are re-packed so Kodi opens them quickly (owner: keep it automatic); Transfers' Up next now says
"faster start" for them instead of "convert", and they wait behind real work."""
import sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.dont_write_bytecode=True;sys.path[:0]=[str(BOOT/'resources/lib'),str(BOOT)]
import prepare_downloads,transfers

class Label(unittest.TestCase):
 def test_up_next_says_faster_start_for_repacks(self):
  with tempfile.TemporaryDirectory() as p:
   prepare_downloads.save(p,{'jobs':{'a':{'source':{'id':'a','name':'Fall.2.mkv','size':2*1024**3},'status':'waiting','repack':True},
                                     'b':{'source':{'id':'b','name':'Scary.Movie.mkv','size':1024**3},'status':'waiting'}},'sessions':{}})
   lines=dict(transfers.queue_lists(p,0))
  self.assertTrue(any(v.startswith('faster start · 2.0 GB') for v in lines.values()),lines)
  self.assertTrue(any(v.startswith('convert · 1.0 GB') for v in lines.values()),lines)
 def test_repacks_wait_behind_real_work(self):
  src=(BOOT/'resources/lib/prepare_downloads.py').read_text()
  self.assertIn("return (-job.get('priority',0),1 if job.get('repack') else 0,",src)

if __name__=='__main__':unittest.main()
