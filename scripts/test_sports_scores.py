"""Scores enrich only a uniquely matched event and do not block the Sports list."""
import copy,sys,threading,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'migration/bundled-bootstrap/resources/lib'),str(ROOT/'scripts')]
import sports_jet as sj
import sports_scores as scores
from test_sports_espn import NOW,body,event,team

class Scores(unittest.TestCase):
 def test_fetch_uses_requested_leagues_and_keeps_valid_score_and_clock(self):
  calls=[]
  def fetch(url):
   calls.append(url)
   return body(event('1','2025-11-16T17:00Z','in',team('IND','Indiana Pacers','88',False),team('PHI','Philadelphia 76ers','91'),period=3,clock='8:41',kind='STATUS_IN_PROGRESS'))
  games=scores.fetch_live(['NBA'],clock=lambda:NOW,fetch=fetch)
  self.assertEqual(len(calls),1)
  self.assertEqual((games[0]['away']['score'],games[0]['home']['score'],games[0]['clock']),(88,91,'Q3 · 8:41'))
 def test_enrichment_is_async_and_requires_unique_same_game(self):
  release=threading.Event();done=threading.Event()
  game={'league':'NBA','state':'live','start':NOW,'away':{'name':'Indiana Pacers','score':None},'home':{'name':'Philadelphia 76ers','score':None},'clock':'','left':None}
  scored=copy.deepcopy(game);scored['away']['score']=88;scored['home']['score']=91;scored['clock']='Q3 · 8:41'
  def fetch(codes):
   self.assertEqual(codes,['NBA']);release.wait(2);done.set();return [scored]
  provider=sj.JetProvider(score_loader=fetch)
  first=provider._with_scores({'live':[copy.deepcopy(game)]})
  self.assertIsNone(first['live'][0]['away']['score'])
  release.set();self.assertTrue(done.wait(2))
  deadline=time.monotonic()+2
  while provider._score_busy and time.monotonic()<deadline:time.sleep(.005)
  result=provider._with_scores({'live':[copy.deepcopy(game)]})['live'][0]
  self.assertEqual((result['away']['score'],result['home']['score'],result['clock']),(88,91,'Q3 · 8:41'))
  reverse=copy.deepcopy(game);reverse['away'],reverse['home']=reverse['home'],reverse['away']
  reversed_result=provider._with_scores({'live':[reverse]})['live'][0]
  self.assertEqual((reversed_result['away']['score'],reversed_result['home']['score']),(91,88))
  with provider.lock:provider._scores=[scored,copy.deepcopy(scored)]
  ambiguous=provider._with_scores({'live':[copy.deepcopy(game)]})['live'][0]
  self.assertIsNone(ambiguous['away']['score'])
  other=copy.deepcopy(game);other['home']['name']='Different Team'
  self.assertIsNone(provider._with_scores({'live':[other]})['live'][0]['away']['score'])
 def test_live_page_refreshes_once_when_background_scores_arrive(self):
  import ast,types
  from unittest.mock import patch
  tree=ast.parse((ROOT/'migration/bundled-bootstrap/sports_live.py').read_text())
  node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='loop')
  states=iter([False,False,True]);revisions=iter([0,1]);calls=[]
  env={'xbmc':types.SimpleNamespace(Monitor=lambda:object()),'sports_provider':types.SimpleNamespace(get=lambda:types.SimpleNamespace(score_revision=lambda:next(revisions))),'time':types.SimpleNamespace(monotonic=lambda:0),'EVERY':30}
  with patch.dict(sys.modules,{'page_wait':types.SimpleNamespace(idle=lambda *args:next(states))}):
   exec(compile(ast.Module(body=[node],type_ignores=[]),'sports-loop','exec'),env)
   env['loop'](types.SimpleNamespace(stop=object(),fetch=lambda *args,**kwargs:calls.append((args,kwargs))))
  self.assertEqual(calls,[((False,),{'quiet':True})])
if __name__=='__main__':unittest.main()
