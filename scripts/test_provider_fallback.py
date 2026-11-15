"""Fallback policy tests: failure recovery, strict identity/quality, cancellation and resolver safety."""
import sys,time,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import provider_fallback as f

class Transport:
 def __init__(self,answers):self.answers=answers;self.calls=[]
 def available(self,p):return p in self.answers
 def search(self,p,r,d,c):
  self.calls.append(p);answer=self.answers[p]
  if isinstance(answer,Exception):raise answer
  return answer
 def resolve(self,p,c,r,d,cancel):return c.get('url')

class Fallback(unittest.TestCase):
 def setUp(self):
  self.request={'media_type':'movie','title':'Example Film','year':2024,'quality':'1080p','profile':{'quality':'1080p','strict_quality':True}}
  self.source={'name':'Example.Film.2024.1080p.WEB-DL.mkv','quality':'1080p','url':'https://fixture.invalid/media.mkv','size':1,'seeders':0}
 def test_first_success_stops_later_backups(self):
  t=Transport({'jacktook':[self.source],'pov':[self.source]})
  self.assertEqual(f.search(self.request,transport=t)[0]['provider'],'jacktook');self.assertEqual(t.calls,['jacktook'])
 def test_offline_and_empty_continue(self):
  t=Transport({'jacktook':ConnectionError('private-url'),'pov':[],'thecrew':[self.source]})
  self.assertEqual(f.search(self.request,transport=t)[0]['provider'],'thecrew');self.assertEqual(t.calls,['jacktook','pov','thecrew'])
 def test_wrong_title_year_and_quality_are_not_usable(self):
  wrong=[dict(self.source,name='Other.Film.2024.1080p.mkv'),dict(self.source,name='Example.Film.2025.1080p.mkv'),dict(self.source,quality='720p')]
  t=Transport({'jacktook':wrong,'pov':[self.source]})
  self.assertEqual(f.search(self.request,transport=t)[0]['provider'],'pov')
 def test_cancel_never_searches_backup(self):
  t=Transport({'jacktook':[self.source]})
  with self.assertRaises(f.Canceled):f.search(self.request,transport=t,cancel=lambda:True)
  self.assertEqual(t.calls,[])
 def test_no_anime_guess_or_primary_recursion(self):
  t=Transport({'jacktook':[self.source],'otaku':[self.source],'thecrew':[self.source]})
  self.assertEqual(f.search(self.request,primary='jacktook',transport=t)[0]['provider'],'thecrew');self.assertEqual(t.calls,['thecrew'])
 def test_empty_and_deadline(self):
  self.assertEqual(f.search(self.request,transport=Transport({})),[])
  with self.assertRaises(TimeoutError):f.search(self.request,transport=Transport({}),timeout=0)
 def test_exact_episode_identity(self):
  r={'media_type':'episode','show_title':'Example Show','title':'Pilot','season':2,'episode':3}
  wrong=dict(self.source,name='Example.Show.S02E04.1080p.mkv');right=dict(self.source,name='Example.Show.S02E03.1080p.mkv')
  self.assertEqual(len(f.verified([wrong,right],r,'pov')),1)
 def test_duplicates_and_nonfinite_sizes_rejected(self):
  self.assertEqual(len(f.verified([self.source,self.source,dict(self.source,size=float('nan'))],self.request,'pov')),1)
 def test_resolve_only_verified_origin(self):
  c=f.verified([self.source],self.request,'pov')[0]
  self.assertEqual(f.resolve(c,self.request,transport=Transport({})),self.source['url'])
  with self.assertRaises(ValueError):f.resolve(dict(c,name='Other.Film.2024.mkv'),self.request,transport=Transport({}))
 def test_executable_urls_and_header_injection_rejected(self):
  for url in ['plugin://evil/play','file:///private/movie.mkv','javascript:alert(1)','{}://{}:{}{}fixture.invalid/x'.format('https','user','pass',chr(64)),'https://fixture.invalid/x\nsecret']:
   with self.subTest(url=url),self.assertRaises(ValueError):f.safe_url(url)
  with self.assertRaises(ValueError):f.safe_url({'url':'https://fixture.invalid/x','headers':{'X':'a\nb'}})
  with self.assertRaises(ValueError):f.safe_url('https://fixture.invalid/x|Cookie=a%0D%0Ab')
 def test_header_preservation(self):
  self.assertEqual(f.safe_url({'url':'https://fixture.invalid/x','headers':{'User-Agent':'A B'}}),'https://fixture.invalid/x|User-Agent=A+B')
if __name__=='__main__':unittest.main()
