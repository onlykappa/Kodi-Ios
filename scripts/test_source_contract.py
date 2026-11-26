"""Backup source contract (roadmap step 4): outcomes, expiry, capabilities, redaction and wrong-match rejection."""
import sys,socket,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import source_contract as c, provider_fallback as f

class HTTP(Exception):
 def __init__(s,code):super().__init__('https://private.invalid/x?token=SECRET');s.code=code

MOVIE={'media_type':'movie','title':'Example Film','year':2024,'quality':'1080p','profile':{}}
EP={'media_type':'episode','show_title':'Example Show','title':'Example Show','year':2020,'season':2,'episode':5,'profile':{}}
def src(name,**k):return dict({'name':name,'quality':'1080p','url':'https://fixture.invalid/m.mkv','size':1,'seeders':0},**k)
def ready(item,provider='jacktook',now=1000):
 n=f.normalize(item,provider);return c.stamp(n,now=now)

class Outcomes(unittest.TestCase):
 def test_every_failure_maps_to_one_known_outcome(self):
  cases=[(f.Canceled('x'),c.CANCELED),(TimeoutError(),c.TIMEOUT),(socket.timeout(),c.TIMEOUT),(ConnectionError(),c.OFFLINE),
   (HTTP(401),c.ACCOUNT_REQUIRED),(HTTP(402),c.ACCOUNT_REQUIRED),(HTTP(403),c.REFUSED),(HTTP(429),c.REFUSED),
   (HTTP(404),c.EXPIRED),(HTTP(410),c.EXPIRED),(ValueError('bad'),c.UNSUPPORTED),(c.Outcome(c.REFUSED),c.REFUSED),(RuntimeError(),c.OFFLINE)]
  for err,want in cases:
   self.assertEqual(c.classify(err),want,repr(err));self.assertIn(c.classify(err),c.OUTCOMES)
 def test_empty_vs_ok_and_unknown_kind(self):
  self.assertEqual(c.search_outcome([]),c.EMPTY);self.assertEqual(c.search_outcome([1]),c.OK)
  self.assertEqual(c.search_outcome([],TimeoutError()),c.TIMEOUT);self.assertEqual(c.Outcome('nonsense').kind,c.OFFLINE)

class Handles(unittest.TestCase):
 def test_expiry_default_capped_and_bogus(self):
  self.assertEqual(c.expiry({},now=100),100+c.DEFAULT_TTL)
  self.assertEqual(c.expiry({'expires_at':100+10**9},now=100),100+c.MAX_TTL)
  self.assertEqual(c.expiry({'expires_at':'junk'},now=100),100+c.DEFAULT_TTL)
  self.assertEqual(c.expiry({'expires_at':150},now=100),150)
 def test_expired_and_missing_stamp_count_as_expired(self):
  self.assertTrue(c.expired({'expires_at':100},now=100));self.assertFalse(c.expired({'expires_at':101},now=100))
  self.assertTrue(c.expired({},now=1));self.assertTrue(c.expired({'expires_at':float('nan')},now=1))
 def test_capabilities_come_from_facts(self):
  self.assertEqual(c.capabilities({'url':'https://a.invalid/m.mkv'}),('stream','download'))
  self.assertEqual(c.capabilities({'torrent_hash':'a'*40}),('download','torrent'))
  self.assertEqual(c.capabilities({'torrent_hash':'a'*40,'cached':True}),('stream','download','cached','torrent'))
  self.assertEqual(c.capabilities({'name':'only a name'}),())

class Redaction(unittest.TestCase):
 def test_no_link_header_or_token_survives(self):
  item=ready(src('Example.Film.2024.1080p.mkv',headers={'Authorization':'Bearer SECRET'},resolver={'token':'SECRET','request':{}}))
  out=c.redact(item);text=repr(out)
  self.assertNotIn('SECRET',text);self.assertNotIn('fixture.invalid',text);self.assertNotIn('url',out);self.assertNotIn('resolver',out)
  self.assertEqual(out['provider'],'jacktook');self.assertIn('expires_at',out)
 def test_classify_never_reads_message(self):
  self.assertNotIn('SECRET',repr(c.classify(HTTP(403))))

class Gate(unittest.TestCase):
 def test_right_title_passes(self):
  self.assertEqual(c.check_usable(ready(src('Example.Film.2024.1080p.mkv')),MOVIE,now=1001)['provider'],'jacktook')
 def rejects(self,item,req,kind,now=1001):
  with self.assertRaises(c.Outcome) as cm:c.check_usable(item,req,now=now)
  self.assertEqual(cm.exception.kind,kind)
 def test_wrong_title_year_episode_and_season_pack_are_unsupported(self):
  for name in ('Other.Film.2024.1080p.mkv','Example.Film.2019.1080p.mkv','Example.Film.Part.2.2024.1080p.mkv'):
   self.rejects(ready(src(name)),MOVIE,c.UNSUPPORTED)
  for name in ('Example.Show.S02E04.1080p.mkv','Example.Show.S03E05.1080p.mkv','Example.Show.S01.1080p.COMPLETE.mkv','Example.Show.2020.E05.1080p'):
   self.rejects(ready(src(name)),EP,c.UNSUPPORTED)
  self.assertEqual(c.check_usable(ready(src('Example.Show.S02E05.1080p.mkv')),EP,now=1001)['name'],'Example.Show.S02E05.1080p.mkv')
 def test_expired_handle_never_plays(self):
  self.rejects(ready(src('Example.Film.2024.1080p.mkv')),MOVIE,c.EXPIRED,now=1000+c.DEFAULT_TTL+1)
 def test_download_needs_download_capability(self):
  item=ready(src('Example.Film.2024.1080p.mkv',url='',resolver={'request':{}}))
  self.assertNotIn('download',item['capabilities'])
  self.rejects(item,dict(MOVIE,purpose='download'),c.UNSUPPORTED)
 def test_malformed_payloads_do_not_become_candidates(self):
  for bad in (None,'x',{},{'name':''},src('x'*3000),src('Example.Film.2024.mkv',size=float('nan')),src('Example.Film.2024.mkv',seeders=-1),{'name':'Example.Film.2024.mkv'}):
   self.assertIsNone(f.normalize(bad,'jacktook'),repr(bad)[:40])
  self.assertIsNone(f.normalize(src('Example.Film.2024.mkv'),'unknown-provider'))
 def test_ambiguous_title_without_year_is_not_accepted(self):
  self.rejects(ready(src('Example.Film.1080p.mkv')),dict(MOVIE,year=None,imdb=None,tmdb=None),c.UNSUPPORTED)

if __name__=='__main__':unittest.main()
