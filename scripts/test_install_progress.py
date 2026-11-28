"""Add-on install progress copied from Kodi's hidden background box (install_progress.py, ISSUE-497)."""
import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','migration','bundled-bootstrap','resources','lib'))
import install_progress as ip

class Props:
 def __init__(s):s.v={}
 def set(s,k,v):s.v[k]=v
 def clear(s,k):s.v.pop(k,None)

class InstallProgress(unittest.TestCase):
 def test_parse_names_the_addon_and_the_stage(self):
  self.assertEqual(ip.parse('Installing Otaku...','Downloading add-on...'),('Otaku',0))
  self.assertEqual(ip.parse('Installing The Loop...','Checking dependencies...'),('The Loop',0))
  self.assertEqual(ip.parse('Installing Otaku...','Verifying downloaded add-on...'),('Otaku',1))
  self.assertEqual(ip.parse('Installing Otaku...','Installing add-on dependencies...'),('Otaku',2))
  self.assertEqual(ip.parse('Installing Otaku...','Installing add-on...'),('Otaku',3))
  self.assertEqual(ip.parse('[B]Installing[/B] Otaku...','[COLOR red]Downloading add-on...[/COLOR]'),('Otaku',0))
 def test_other_background_jobs_are_ignored(self):
  for heading in ('Updating library','Elementum Burst errors','','Scanning TV shows'):self.assertIsNone(ip.parse(heading,'x'))
 def test_publish_sets_and_clears(self):
  p=Props();self.assertTrue(ip.publish(('Installing Otaku...','Installing add-on...',140),p.set,p.clear))
  self.assertEqual(p.v,{ip.NAME:'Otaku',ip.STAGE:'3',ip.PERCENT:'100'})
  self.assertFalse(ip.publish(None,p.set,p.clear));self.assertEqual(p.v,{})
  self.assertFalse(ip.publish(('Updating library','',5),p.set,p.clear));self.assertEqual(p.v,{})
 def test_watch_polls_fast_while_it_shows_and_cleans_up(self):
  p=Props();boxes=iter([('Installing A...','Downloading add-on...',10),('Installing A...','Installing add-on...',90),None]);waits=[]
  def wait(s):
   waits.append(s);return len(waits)>3
  ip.watch(lambda:next(boxes),p.set,p.clear,wait)
  self.assertEqual(waits,[3.0,0.7,0.7,3.0]);self.assertEqual(p.v,{})

if __name__=='__main__':unittest.main()
