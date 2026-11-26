"""Independent site adapters (roadmap step 9): synthetic pages in each site's documented JSON format; fail one backend at a time."""
import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import independent_sites as s, source_contract as c
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fixtures_site_captures import CAPTURES

H=lambda n:('%040x'%n)
MOVIE={'media_type':'movie','title':'Example Film','year':2024,'imdb':'tt1234567','profile':{}}
EP={'media_type':'episode','show_title':'Example Show','title':'Example Show','year':2020,'season':2,'episode':5,'imdb':'tt7654321','profile':{}}
def apibay(*rows):return json.dumps([{'id':str(i),'name':n,'info_hash':h,'seeders':str(sd),'size':str(sz)} for i,(n,h,sd,sz) in enumerate(rows,1)])
NONE=json.dumps([{'id':'0','name':'No results returned','info_hash':'0'*40,'seeders':'0','size':'0'}])
def yts(*movies):return json.dumps({'status':'ok','data':{'movie_count':len(movies),'movies':[{'title':t,'year':y,'torrents':[{'hash':h,'quality':q,'type':'web','seeds':sd,'size_bytes':sz} for (h,q,sd,sz) in tor]} for (t,y,tor) in movies]}})
def eztv(*rows):return json.dumps({'torrents':[{'filename':n,'hash':h,'seeds':sd,'size_bytes':sz,'season':str(se),'episode':str(ep)} for (n,h,sd,sz,se,ep) in rows]})
def knaben(*rows):return json.dumps({'hits':[{'title':n,'hash':h,'seeders':sd,'bytes':sz} for (n,h,sd,sz) in rows]})
LEET_LIST='<table><tbody></tbody></table>'

class Fetch:
 """host -> page text, or an Exception; records every URL."""
 def __init__(s_,pages):s_.pages=pages;s_.calls=[]
 def __call__(s_,url,timeout):
  s_.calls.append(url)
  for host,v in s_.pages.items():
   if url.startswith(host):
    if isinstance(v,Exception):raise v
    return v
  raise ConnectionError('no fixture')
def pages(movie=True):
 if movie:return {'https://apibay.org':apibay(('Example.Film.2024.1080p.WEB-DL.x264',H(1),50,2e9),('Example.Film.2019.1080p',H(2),99,2e9),('Other.Film.2024.1080p',H(3),99,2e9)),
  'https://movies-api.accel.li':yts(('Example Film',2024,[(H(4),'1080p',30,1.5e9),(H(1),'720p',5,1e9)]),('Example Film',2019,[(H(5),'1080p',80,1e9)])),
  'https://eztvx.to':ConnectionError(),'https://api.knaben.org':knaben(('Example.Film.2024.1080p.BluRay',H(1),70,3e9),('Example.Film.2024.2160p.WEB',H(12),15,9e9),('Example.Film.2023.1080p',H(13),99,1e9)),'https://1337x.to':LEET_LIST}
 return {'https://apibay.org':apibay(('Example.Show.S02E05.1080p.WEB',H(6),20,1e9),('Example.Show.S02E04.1080p.WEB',H(7),99,1e9),('Example.Show.S02.COMPLETE.1080p',H(8),99,9e9)),
  'https://eztvx.to':eztv(('Example.Show.S02E05.720p.HDTV.x264-GRP',H(9),12,5e8,2,5),('Example.Show.S02E04.720p.HDTV',H(10),90,5e8,2,4),('Example.Show.S02E05.mislabeled.S09E09',H(11),90,5e8,2,6)),
  'https://movies-api.accel.li':yts(),'https://api.knaben.org':knaben(('Example.Show.S02E05.2160p.WEB-DL',H(14),8,4e9),('Example.Show.S02E06.1080p',H(15),90,1e9)),'https://1337x.to':LEET_LIST}

class Parsers(unittest.TestCase):
 def test_apibay_placeholder_and_layout_change(self):
  self.assertEqual(s.Apibay().parse(NONE,MOVIE),[])
  with self.assertRaises(ValueError):s.Apibay().parse('{"error":1}',MOVIE)
  with self.assertRaises(ValueError):s.Apibay().parse('[{"x":1}]',MOVIE)
 def test_yts_layout_and_names(self):
  rows=s.Yts().parse(yts(('Example Film',2024,[(H(4),'1080p',30,1.5e9)])),MOVIE);self.assertEqual(rows[0]['name'],'Example.Film.2024.1080p.WEB.x264-YTS')
  with self.assertRaises(ValueError):s.Yts().parse('{"status":"error"}',MOVIE)
 def test_eztv_requires_imdb_and_site_numbers(self):
  self.assertFalse(s.Eztv().applies(dict(EP,imdb='')));self.assertFalse(s.Eztv().applies(MOVIE));self.assertTrue(s.Eztv().applies(EP))
  self.assertEqual([r['name'] for r in s.Eztv().parse(eztv(('A.S02E05',H(1),1,1,2,5),('B',H(2),1,1,2,4)),EP)],['A.S02E05'])
 def test_knaben_layout_and_rows(self):
  self.assertEqual(s.Knaben().parse(knaben(('Example.Film.2024',H(1),5,1)),MOVIE)[0]['torrent_hash'],H(1))
  with self.assertRaises(ValueError):s.Knaben().parse('{"hits":3}',MOVIE)
  self.assertIn('c=3000000',s.Knaben().plan(MOVIE)[0]);self.assertIn('c=2000000',s.Knaben().plan(EP)[0])
 def test_zero_hash_and_bad_numbers_dropped(self):
  self.assertEqual(s.Apibay().parse(apibay(('Example.Film.2024',H(0),5,1)),MOVIE),[])
  self.assertEqual(s.Apibay().parse(apibay(('Example.Film.2024',H(1),'x','y')),MOVIE)[0]['seeders'],0)

class Search(unittest.TestCase):
 def test_movie_merges_and_dedupes_by_hash_and_rejects_wrong_matches(self):
  fx=Fetch(pages());out,found,report=s.search_all(MOVIE,fetch=fx)
  self.assertEqual(out,c.OK);names=[i['name'] for i in found]
  self.assertEqual(sorted(i['torrent_hash'] for i in found),[H(1),H(4),H(12)]);self.assertNotIn(H(2),[i['torrent_hash'] for i in found])
  self.assertEqual(found[0]['torrent_hash'],H(1),'best-seeded first, one row for a hash two sites share');self.assertEqual(found[0]['seeders'],70)
  self.assertEqual({k:report[k] for k in ('apibay','yts','knaben','1337x')},{'apibay':c.OK,'yts':c.OK,'knaben':c.OK,'1337x':c.EMPTY});self.assertNotIn('eztv',report,'eztv is TV only')
  self.assertTrue(all(i['magnet'].startswith('magnet:?xt=urn:btih:') and 'download' in i['capabilities'] for i in found))
 def test_episode_exact_numbers_only(self):
  out,found,report=s.search_all(EP,fetch=Fetch(pages(False)))
  # S02E04 and the site-mislabelled row are out; a pack for the right season stays (source_match's existing rule), a wrong-season pack would not.
  self.assertEqual(sorted(i['torrent_hash'] for i in found),sorted([H(14),H(6),H(8),H(9)]));self.assertNotIn('yts',report)
 def test_each_site_failing_alone_leaves_the_others_unchanged(self):
  for failing in ('apibay','yts','knaben'):
   host={'apibay':'https://apibay.org','yts':'https://movies-api.accel.li','knaben':'https://api.knaben.org'}[failing];p=pages();p[host]=TimeoutError()
   fx=Fetch(p);out,found,report=s.search_all(MOVIE,fetch=fx)
   self.assertEqual(report[failing],c.TIMEOUT,failing);self.assertEqual(out,c.OK)
   self.assertTrue(found and all(i['site']!=failing for i in found),'the other family still answers and nothing comes from the failed one')
 def test_disabled_site_is_never_requested_by_anyone(self):
  for site,host in (('apibay','https://apibay.org'),('yts','https://movies-api.accel.li'),('knaben','https://api.knaben.org'),('1337x','https://1337x.to')):
   fx=Fetch(pages());out,found,report=s.search_all(MOVIE,fetch=fx,disabled=(site,))
   self.assertFalse(any(u.startswith(host) for u in fx.calls),site);self.assertNotIn(site,report)
  fx=Fetch(pages(False));s.search_all(EP,fetch=fx,disabled=('eztv',));self.assertFalse(any('eztvx' in u for u in fx.calls))
 def test_all_sites_failing_gives_a_typed_outcome_not_empty(self):
  p={h:ConnectionError() for h in ('https://apibay.org','https://movies-api.accel.li','https://eztvx.to','https://api.knaben.org','https://1337x.to')}
  out,found,report=s.search_all(MOVIE,fetch=Fetch(p));self.assertEqual((out,found),(c.OFFLINE,[]));self.assertEqual(set(report.values()),{c.OFFLINE})
 def test_changed_layout_everywhere_is_unsupported(self):
  p={'https://apibay.org':'{"x":1}','https://movies-api.accel.li':'<html>','https://api.knaben.org':'{"x":1}','https://1337x.to':'<html>'}
  out,found,report=s.search_all(MOVIE,fetch=Fetch(p));self.assertEqual(out,c.UNSUPPORTED)
 def test_cancel_and_ineligible(self):
  fx=Fetch(pages());self.assertEqual(s.search_all(MOVIE,fetch=fx,cancel=lambda:True)[0],c.CANCELED)
  self.assertEqual(s.search_all({'media_type':'movie','title':'X','profile':{}},fetch=Fetch({}))[0],c.UNSUPPORTED)
 def test_coverage_table_matches_the_adapters(self):
  self.assertEqual(set(s.COVERAGE),set(s.SITES))

BBB={'media_type':'movie','title':'Big Buck Bunny','year':2008,'profile':{}}
ONE={'media_type':'episode','show_title':'One Piece','title':'One Piece','year':1999,'season':23,'episode':6,'profile':{}}
class RealCaptures(unittest.TestCase):
 """Excerpts of real pages captured 2026-11-26: they prove each parser against the sites' actual markup at that date, not that the markup stays."""
 def test_each_parser_reads_its_real_page(self):
  want={'bitsearch':(BBB,'dd8255ecdc7ca55fb0bbf81323d87062db1f6d1c','Big Buck Bunny',48),
   'torrentdownload':(BBB,'c39fe3eefbdb62da9c27eb6398ff4a7d2e26e7ab','Big Buck Bunny BDRip XviD MEDiC',161),
   'limetorrents':(BBB,'3180e68a4ec7c6f181cdba8cb37b2d3ac8e50ae2','Big Buck Bunny trailer',7),
   'kick4ss':(BBB,'5b8c29a1e13d409422089cf113851dec9e2f4e97','Big Buck Bunny 4K UHD HFR 60 fps FLAC WEBRip 2160p X265 ZMachine',1),
   'nyaa':(ONE,'611e5b6bcfa317ea580a40da2e7befda5caf3a9f','[AnoZu] One Piece S23E06 1080p CR WEB-DL Dual-Audio DDP 2.0 H.264',197)}
  adapters={a.name:a for a in s.SIMPLE}
  for name,(req,h,title,seeds) in want.items():
   rows=adapters[name].parse(CAPTURES[name],req)
   self.assertEqual(len(rows),2,name);self.assertEqual((rows[0]['torrent_hash'],rows[0]['name'],rows[0]['seeders']),(h,title,seeds),name);self.assertGreater(rows[0]['size'],1e6,name)
 def test_real_pages_end_to_end_apply_the_strict_identity_check(self):
  # A real page for Big Buck Bunny has no row that is verifiably the 2008 film by name alone (no year in the names), so none passes.
  p={'https://bitsearch.eu':CAPTURES['bitsearch'],'https://www.torrentdownload.info':CAPTURES['torrentdownload'],'https://www.limetorrents.lol':CAPTURES['limetorrents'],'https://kick4ss.com':CAPTURES['kick4ss']}
  out,found,report=s.search_all(BBB,fetch=Fetch(p),disabled=('apibay','yts','knaben','1337x'))
  self.assertEqual(found,[]);self.assertTrue(all(report[k]==c.EMPTY for k in ('bitsearch','torrentdownload','limetorrents','kick4ss')),report)
  out,found,report=s.search_all(ONE,fetch=Fetch({'https://nyaa.si':CAPTURES['nyaa']}),disabled=('apibay','knaben','1337x','bitsearch','torrentdownload','limetorrents','kick4ss','eztv'))
  self.assertEqual([i['torrent_hash'] for i in found],['611e5b6bcfa317ea580a40da2e7befda5caf3a9f'],'only the exact S23E06 row; S01E1161 is another episode')
 def test_changed_layout_per_family_is_unsupported_and_feed_tricks_rejected(self):
  for a in (s.Bitsearch(),s.TorrentDownload(),s.Lime(),s.Kick()):
   with self.assertRaises(ValueError):a.parse('<html>redesigned</html>',BBB)
  with self.assertRaises(ValueError):s.Nyaa().parse('<html>',ONE)
  with self.assertRaises(ValueError):s.Nyaa().parse('<rss><!DOCTYPE x [<!ENTITY a "b">]></rss>',ONE)
 def test_nyaa_only_for_episodes(self):
  self.assertTrue(s.Nyaa().applies(ONE));self.assertFalse(s.Nyaa().applies(BBB))

if __name__=='__main__':unittest.main()
