"""Metadata outages (roadmap step 20): TMDb answers stay usable but marked stale; a title never seen fails safe; remembered sports state is not 'live' for long."""
import json,sys,tempfile,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import source_match as sm, sports_match as m, source_contract as c

DAY=86400
MOVIE_DETAILS={'id':7,'imdb_id':'tt0000007','title':'Fall','original_title':'Fall','release_date':'2022-09-02','alternative_titles':{'titles':[{'title':'Fall: Fear Reaches New Heights'}]},'translations':{'translations':[]},'release_dates':{'results':[]}}
SEARCH={'results':[{'id':7,'title':'Fall','original_title':'Fall','release_date':'2022-09-02'},{'id':99,'title':'Fall','original_title':'Fall','release_date':'2026-01-01'}]}
def down(url):raise ConnectionError('TMDb unreachable')

class Tmdb(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);path=str(Path(self.tmp.name)/'cache.json')
  self.saved=(sm._cache_file,dict(sm._cache),list(sm._cache_loaded));sm._cache.clear();sm._cache_loaded[:]=[1]
  sm._cache_file=lambda:path
  self.addCleanup(lambda:(setattr(sm,'_cache_file',self.saved[0]),sm._cache.clear(),sm._cache.update(self.saved[1]),sm._cache_loaded.__setitem__(slice(None),self.saved[2])))
 def seed(self,age_days):
  t=time.time()-age_days*DAY
  for slot,d in (('/search/movie?query=Fall',SEARCH),('/search/movie?query=Fall&year=2022',SEARCH),('/movie/7?append_to_response=alternative_titles%2Crelease_dates%2Ctranslations',MOVIE_DETAILS)):sm._cache[slot]={'t':t,'d':d}
 def exp(self):return sm.expected('movie',['Fall'],2022,tmdb='7')
 def test_a_fresh_cache_needs_no_network(self):
  self.seed(1);e=sm.enrich(self.exp(),key='k',get=down);self.assertEqual(e['metadata'],'cached');self.assertIn('Fall: Fear Reaches New Heights',e['titles'])
 def test_an_old_answer_is_used_when_tmdb_is_down_and_marked_stale(self):
  self.seed(30);e=sm.enrich(self.exp(),key='k',get=down);self.assertEqual(e['metadata'],'stale')
  self.assertTrue(sm.check('Fall.2022.1080p.WEB',e)[0]);self.assertFalse(sm.check('Fall.2026.1080p.WEB',e)[0]);self.assertFalse(sm.check('Free.Fall.2014.1080p',e)[0])
 def test_without_the_key_or_with_tmdb_up_the_answer_is_refreshed_not_stale(self):
  self.seed(30);calls=[]
  def up(url):calls.append(url);return json.dumps(MOVIE_DETAILS if '/movie/7' in url else SEARCH)
  e=sm.enrich(self.exp(),key='k',get=up);self.assertEqual(e['metadata'],'live');self.assertTrue(calls)
  e2=sm.enrich(self.exp(),key='k',get=down);self.assertEqual(e2['metadata'],'cached','the refreshed copy is fresh again')
 def test_too_old_or_never_seen_fails_safe(self):
  self.seed(100);e=sm.enrich(self.exp(),key='k',get=down);self.assertEqual(e['metadata'],'none')
  self.assertFalse(sm.check('Fall.1080p.WEB.x264',e)[0],'no year and no way to know another film shares the title: hidden')
  sm._cache.clear();e=sm.enrich(sm.expected('movie',['Never Seen'],2020),key='k',get=down);self.assertEqual(e['metadata'],'none');self.assertTrue(sm.check('Never.Seen.2020.1080p',e)[0],'an exact title and year still passes')
  self.assertFalse(sm.check('Never.Seen.2021.1080p',e)[0])
 def test_the_stale_flag_is_per_call(self):
  self.seed(30);self.assertEqual(sm.enrich(self.exp(),key='k',get=down)['metadata'],'stale')
  sm._cache.clear();self.seed(1);self.assertEqual(sm.enrich(self.exp(),key='k',get=down)['metadata'],'cached')

NOW=1_800_000_000
def game(state='live',start=NOW-1800):return {'id':'espn:EPL:1','league':'EPL','state':state,'start':start,'away':{'name':'Chelsea'},'home':{'name':'Arsenal'}}
class Sports(unittest.TestCase):
 def test_a_remembered_live_answer_is_stale_after_fifteen_minutes(self):
  self.assertEqual(m.status(game(),NOW,as_of=NOW-60),'live');self.assertEqual(m.status(game(),NOW,as_of=NOW-m.LIVE_SNAPSHOT_MAX-1),'stale')
  self.assertEqual(m.status(game(),NOW),'live','a live fetch carries no snapshot age')
 def test_upcoming_from_an_old_snapshot_is_fine_until_its_start_passes_by_hours(self):
  g=game('upcoming',NOW+3600);self.assertEqual(m.status(g,NOW,as_of=NOW-6*3600),'upcoming');self.assertEqual(m.status(game('upcoming',NOW-4*3600),NOW,as_of=NOW-6*3600),'stale')
 def test_unique_match_and_start_reject_a_stale_snapshot(self):
  l=dict(game(),sources=[{'id':'a','addon':'x','play':'{}'}],start=NOW-1700)
  with self.assertRaises(c.Outcome) as cm:m.unique_match(game(),[l],NOW,as_of=NOW-3600)
  self.assertEqual(cm.exception.kind,c.UNSUPPORTED);self.assertEqual(m.unique_match(game(),[l],NOW,as_of=NOW-60)['sources'][0]['id'],'a')
  with self.assertRaises(c.Outcome):m.Launcher().start(game(),[l],NOW-10,lambda s:self.fail('launched'),NOW,as_of=NOW-3600)

if __name__=='__main__':unittest.main()
