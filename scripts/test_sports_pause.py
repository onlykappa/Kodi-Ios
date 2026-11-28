import sys,tempfile,unittest,json
from types import SimpleNamespace as NS
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_pause as sp
import sports_jet as sj

class Window:
 def __init__(self):self.props={}
 def getProperty(self,key):return self.props.get(key,'')
 def setProperty(self,key,value):self.props[key]=value
 def clearProperty(self,key):self.props.pop(key,None)

class TestPause(unittest.TestCase):
 def test_pause_persists_expires_and_resets_on_build(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'pause.json';clock=[1000];window=Window()
   pause=sp.Pause(window,path,'build1',lambda:clock[0]);self.assertFalse(pause.active());pause.pause();self.assertTrue(pause.active())
   self.assertTrue(sp.Pause(Window(),path,'build1',lambda:clock[0]).active())
   self.assertFalse(sp.Pause(Window(),path,'build2',lambda:clock[0]).active())
   clock[0]+=sp.DURATION+1;self.assertFalse(pause.active())
   clock[0]=1000;pause.clear();self.assertFalse(pause.active())
 def test_paused_play_skips_jet_and_tries_alternate(self):
  with tempfile.TemporaryDirectory() as tmp:
   home=Window();path=Path(tmp)/'pause.json'
   with patch.object(sp,'location',return_value=path),patch.object(sp,'build',return_value='same'),patch.dict(sys.modules,{'xbmc':NS(),'xbmcgui':NS(Window=lambda i:home)}):
    sp.Pause(window=home).pause()
    jet=json.dumps({'e':'JetScraper','l':{}}); alt=json.dumps({'e':'IndependentStreamsCenter','l':{'address':'fixture'}})
    import sports_independent
    with patch.object(sj,'import_jet',side_effect=AssertionError('paused Jet called')),patch.object(sports_independent,'resolve',return_value=('https://video.invalid/live.m3u8',{})),patch.object(sj,'play_local',lambda address,headers,logger,name:played.append((address,name)) or True),patch.dict(sys.modules,{'xbmc':NS(Player=lambda:NS(play=lambda path:None))}):
     played=[]
     self.assertTrue(sj.play({'play':jet,'alts':[alt]},lambda s:None));self.assertEqual(played,[('https://video.invalid/live.m3u8','StreamsCenter')])   # the paused Jet source is skipped, our own site plays
 def test_paused_candidate_does_not_expand_or_resolve(self):
  calls=[];extractor=NS(get_links=lambda link:calls.append('links'),get_link=lambda link:calls.append('link'))
  for link in (NS(links=True),NS(links=False,direct=False,resolveurl=False)):
   with patch.object(sj,'jet_paused',return_value=True):self.assertEqual(list(sj.candidates(None,extractor,link)),[])
  self.assertEqual(calls,[])
 def test_refusals_are_specific(self):
  self.assertTrue(sp.is_refusal(Exception('User is banned')))
  self.assertTrue(sp.is_refusal(Exception('Addon not in whitelist')))
  self.assertFalse(sp.is_refusal(Exception('connection timed out')))
if __name__=='__main__':unittest.main()
