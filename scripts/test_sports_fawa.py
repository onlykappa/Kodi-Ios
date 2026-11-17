import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_fawa as sf
import sports_jet as sj
class Tests(unittest.TestCase):
 def test_resolves_with_headers_into_local_proxy(self):
  calls=[]
  proxy=NS(get_proxy_url=lambda url,h:(calls.append((url,h)) or 'http://127.0.0.1:1234/fawa/test.m3u8'))
  with patch.object(sf,'fetch',return_value='var d1="https://cdn.invalid/";var d2="live";var d3=".m3u8";'),patch.object(sj,'add_module_paths'),patch.dict(sys.modules,{'fawa_proxy.util.stream_proxy':NS(get_stream_proxy=lambda *a,**kw:proxy)}):
   self.assertTrue(sf.resolve(sf.BASE+'event').startswith('http://127.0.0.1:'))
  self.assertEqual(calls[0][0],'https://cdn.invalid/live.m3u8');self.assertEqual(calls[0][1]['Referer'],sf.BASE)
 def test_lists_only_unique_schedule_matches(self):
  import sports_scores
  name=NS(get_text=lambda *a,**kw:'Alpha vs Beta')
  class Card:
   def find(self,tag=None,**kw):return name if kw.get('class_') else {'href':'Alpha vs Beta.html'}
  soup=NS(find_all=lambda *a,**kw:[Card()])
  game={'away':{'name':'Alpha'},'home':{'name':'Beta'},'league_name':'NBA','start':1000,'state':'live'}
  with patch.dict(sys.modules,{'bs4':NS(BeautifulSoup=lambda *a:soup)}),patch.object(sf,'fetch',return_value='fixture'),patch.object(sj,'add_module_paths'),patch.object(sports_scores,'fetch_live',return_value=[game]):
   items=sf.FawaNews().get_items();self.assertEqual(len(items),1)
   self.assertIn('Alpha%20vs%20Beta.html',items[0].links[0].address)
  with patch.dict(sys.modules,{'bs4':NS(BeautifulSoup=lambda *a:soup)}),patch.object(sf,'fetch',return_value='fixture'),patch.object(sj,'add_module_paths'),patch.object(sports_scores,'fetch_live',return_value=[]):
   self.assertEqual(sf.FawaNews().get_items(),[])
 def test_rejects_missing_source_and_local_media(self):
  for body in ['<html>offline</html>','var d1="http://127.0.0.1/";var d2="a";var d3=".m3u8";']:
   with patch.object(sf,'fetch',return_value=body):
    with self.assertRaises((ValueError,RuntimeError)):sf.resolve(sf.BASE+'event')
if __name__=='__main__':unittest.main()
