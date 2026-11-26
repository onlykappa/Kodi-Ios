"""First-party search adapter (roadmap step 5): fixtures are synthetic pages in the site's table layout, not live responses."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import independent_search as s, source_contract as c, provider_fallback as f

BASE='https://1337x.to'
def row(name,seeds,size,tid):
 return ('<tr><td class="coll-1 name"><a href="/sub/1/0/" class="icon"><i></i></a><a href="/torrent/%d/x/">%s</a></td><td class="coll-2 seeds">%s</td>'
  '<td class="coll-3 leeches">1</td><td class="coll-date">Nov. 1st</td><td class="coll-4 size mob-uploader">%s<span class="seeds">3</span></td><td class="coll-5">u</td></tr>')%(tid,name,seeds,size)
def page(*rows):return '<html><table><thead><tr><th>n</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></html>'
def detail(h):return '<a href="magnet:?xt=urn:btih:%s&dn=x&tr=udp%%3A%%2F%%2Ft.invalid">Magnet</a>'%h
H1,H2,H3='a'*40,'b'*40,'c'*40
MOVIE={'media_type':'movie','title':'Example Film','year':2024,'profile':{}}
EP={'media_type':'episode','show_title':'Example Show','title':'Example Show','year':2020,'season':2,'episode':5,'profile':{}}

class Fetch:
 def __init__(self,pages):self.pages=pages;self.calls=[]
 def __call__(self,url,timeout):
  self.calls.append(url)
  v=self.pages.get(url) if url in self.pages else next((x for k,x in self.pages.items() if k in url),None)
  if isinstance(v,Exception):raise v
  if v is None:raise ConnectionError('no fixture')
  return v
def pages(*rows,hashes=()):
 d={'/sort-category-search/':page(*rows)}
 for i,h in enumerate(hashes,1):d['/torrent/%d/'%i]=detail(h)
 return d

class Adapter(unittest.TestCase):
 def test_movie_found_with_hash_and_no_add_on(self):
  self.assertNotIn('xbmc',sys.modules)
  fx=Fetch(pages(row('Example.Film.2024.1080p.WEB-DL.x264',40,'2.1 GB',1),row('Example.Film.2019.1080p.BluRay',90,'3 GB',2),row('Other.Film.2024.1080p',70,'1 GB',3),hashes=(H1,H2,H3)))
  out,found=s.search(MOVIE,fetch=fx)
  self.assertEqual(out,c.OK);self.assertEqual([x['name'] for x in found],['Example.Film.2024.1080p.WEB-DL.x264'])
  self.assertEqual(found[0]['torrent_hash'],H1);self.assertEqual(found[0]['provider'],'local');self.assertEqual(found[0]['quality'],'1080p')
  self.assertIn('download',found[0]['capabilities']);self.assertGreater(found[0]['size'],2e9)
  self.assertEqual(len([u for u in fx.calls if '/torrent/' in u]),1,'wrong titles must not cost a detail request')
 def test_episode_exact_season_and_episode_only(self):
  fx=Fetch(pages(row('Example.Show.S02E05.1080p.WEB',30,'1 GB',1),row('Example.Show.S02E04.1080p.WEB',99,'1 GB',2),row('Example.Show.S02.1080p.COMPLETE',99,'9 GB',3),hashes=(H1,H2,H3)))
  out,found=s.search(EP,fetch=fx);self.assertEqual([x['name'] for x in found],['Example.Show.S02E05.1080p.WEB'])
 def test_query_words(self):
  self.assertEqual(s.query(MOVIE),'Example Film 2024');self.assertEqual(s.query(EP),'Example Show S02E05')
 def test_valid_page_without_matches_is_empty(self):
  self.assertEqual(s.search(MOVIE,fetch=Fetch(pages()))[0],c.EMPTY)
  self.assertEqual(s.search(MOVIE,fetch=Fetch(pages(row('Example.Film.2024.1080p',0,'1 GB',1))))[0],c.EMPTY,'no seeders')
 def test_changed_layout_is_unsupported_not_empty(self):
  out,found=s.search(MOVIE,fetch=Fetch({'/sort-category-search/':'<html><div>new design</div></html>'}));self.assertEqual((out,found),(c.UNSUPPORTED,[]))
 def test_errors_become_typed_outcomes(self):
  class H(Exception):
   def __init__(self,code):super().__init__('https://private.invalid?token=SECRET');self.code=code
  for err,want in ((TimeoutError(),c.TIMEOUT),(ConnectionError(),c.OFFLINE),(H(403),c.REFUSED),(H(404),c.EXPIRED)):
   out,found=s.search(MOVIE,fetch=Fetch({'/sort-category-search/':err}));self.assertEqual((out,found),(want,[]))
 def test_detail_failure_or_missing_magnet_gives_empty(self):
  d=pages(row('Example.Film.2024.1080p',5,'1 GB',1));d['/torrent/1/']='<html>no magnet</html>'
  self.assertEqual(s.search(MOVIE,fetch=Fetch(d))[0],c.EMPTY)
  d['/torrent/1/']=TimeoutError();self.assertEqual(s.search(MOVIE,fetch=Fetch(d))[0],c.EMPTY)
 def test_other_host_links_are_dropped(self):
  r=row('Example.Film.2024.1080p',5,'1 GB',1).replace('/torrent/1/x/','https://evil.invalid/torrent/1/x/')
  fx=Fetch(pages(r,hashes=(H1,)));self.assertEqual(s.search(MOVIE,fetch=fx)[0],c.EMPTY);self.assertFalse(any('evil' in u for u in fx.calls))
 def test_cancel_stops_before_any_request(self):
  fx=Fetch(pages(row('Example.Film.2024.1080p',5,'1 GB',1),hashes=(H1,)))
  self.assertEqual(s.search(MOVIE,fetch=fx,cancel=lambda:True),(c.CANCELED,[]));self.assertEqual(fx.calls,[])
 def test_ineligible_request_is_unsupported(self):
  self.assertEqual(s.search({'media_type':'movie','title':'Example Film','profile':{}},fetch=Fetch({}))[0],c.UNSUPPORTED)
 def test_second_domain_used_after_first_fails(self):
  fx=Fetch({'a.invalid/sort':ConnectionError(),'b.invalid/sort':page(row('Example.Film.2024.1080p',5,'1 GB',1)),'b.invalid/torrent/1/':detail(H1)})
  out,found=s.search(MOVIE,fetch=fx,domains=('https://a.invalid','https://b.invalid'));self.assertEqual((out,len(found)),(c.OK,1))
 def test_detail_requests_are_capped(self):
  rows=[row('Example.Film.2024.1080p.v%d'%i,10+i,'1 GB',i) for i in range(1,21)]
  fx=Fetch(pages(*rows,hashes=tuple('%040x'%i for i in range(1,21))));s.search(MOVIE,fetch=fx)
  self.assertLessEqual(len([u for u in fx.calls if '/torrent/' in u]),s.MAX_DETAIL)
 def test_candidates_survive_the_contract_gate_and_redact(self):
  fx=Fetch(pages(row('Example.Film.2024.1080p.WEB',5,'1 GB',1),hashes=(H1,)));out,found=s.search(MOVIE,fetch=fx)
  item=found[0]
  c.check_usable(item,dict(MOVIE,purpose='download'))
  with self.assertRaises(c.Outcome) as cm:c.check_usable(item,dict(MOVIE,purpose='stream'))
  self.assertEqual(cm.exception.kind,c.UNSUPPORTED,'a bare torrent cannot stream until debrid or Elementum resolves it')
  out=c.redact(item);self.assertNotIn('magnet',out);self.assertNotIn(H1,repr(out))
  self.assertTrue(item['magnet'].startswith('magnet:?xt=urn:btih:'))

if __name__=='__main__':unittest.main()
