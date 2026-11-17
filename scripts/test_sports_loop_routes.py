import sys,json,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_loop_routes as lr
import sports_jet as sj
class Tests(unittest.TestCase):
 def test_exact_loop_route_handoff_never_imports_jet(self):
  route='plugin://plugin.video.the-loop/play/fixture';calls=[]
  with patch.object(sj,'import_jet',side_effect=AssertionError('direct Jet import')),patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(play=lambda value:calls.append(value))),'xbmcgui':NS()}):
   self.assertTrue(sj.play_one(json.dumps({'e':lr.NAME,'l':{'address':route}}),lambda s:None))
  self.assertEqual(calls,[route])
 def test_reject_other_addon_or_network_url(self):
  for value in ['https://example.invalid','plugin://other.addon/play','plugin://user:pass@plugin.video.the-loop/play']:
   self.assertFalse(lr.valid_route(value))
if __name__=='__main__':unittest.main()
