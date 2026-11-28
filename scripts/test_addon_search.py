"""Add-on search follows the phone's native search field (addon_search.py, ISSUE-497)."""
import os,sys,unittest
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','migration','bundled-bootstrap','resources','lib'))
import addon_search as a

class Fake:
 def __init__(s,folder='addons://search/%E2%80%8B'):
  s.typed='';s.folder=folder;s.shut=False;s.went=[];s.backs=0;s.now=0.0
  s.f=a.Follower(lambda:s.typed,lambda:s.folder,lambda:s.shut,s.went.append,lambda:setattr(s,'backs',s.backs+1),lambda:s.now)

class AddonSearch(unittest.TestCase):
 def test_addresses(self):
  self.assertEqual(a.path(''),'addons://search/%E2%80%8B');self.assertEqual(a.path('  '),a.BLANK)
  self.assertEqual(a.path('  jet   proxy '),'addons://search/jet%20proxy');self.assertEqual(a.path('café'),'addons://search/caf%C3%A9')
 def test_follows_typing_once_per_change(self):
  t=Fake();self.assertTrue(t.f.tick());self.assertEqual(t.went,[],'nothing typed: the blank search page is already open')
  t.typed='jet';t.f.tick();t.f.tick();self.assertEqual(t.went,['addons://search/jet'])
  t.typed='jet  ';t.f.tick();self.assertEqual(t.went,['addons://search/jet'],'spaces alone are not a new search')
  t.typed='';t.f.tick();self.assertEqual(t.went[-1],a.BLANK)
 def test_closing_the_field_goes_back_and_ends(self):
  t=Fake();t.shut=True;self.assertFalse(t.f.tick());self.assertEqual(t.backs,1)
 def test_ends_when_the_page_leaves_the_search(self):
  t=Fake();t.f.tick();t.folder='addons://';self.assertFalse(t.f.tick());self.assertEqual(t.backs,0)
 def test_waits_for_the_page_to_arrive(self):
  t=Fake(folder='addons://');self.assertTrue(t.f.tick(),'still on the old page, within the grace time')
  t.now=6;self.assertFalse(t.f.tick(),'the page never opened')

if __name__=='__main__':unittest.main()
