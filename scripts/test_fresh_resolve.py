"""Fresh resolution (roadmap step 6) against a controlled loopback server that demands header and cookie continuity."""
import sys,threading,unittest,urllib.parse
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import fresh_resolve as r, source_contract as c, provider_fallback as f

class Site:
 """token: header X-Token the site currently accepts; cookie set by the master and required afterwards."""
 def __init__(self):
  self.token='t1';self.mode='ok';self.hits=[];self.cookie='sid=abc123'
  site=self
  class H(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_GET(self):
    p=urllib.parse.urlsplit(self.path).path;site.hits.append((p,self.headers.get('X-Token'),self.headers.get('Cookie'),self.headers.get('Range')))
    if site.mode=='429':return self.send(429,b'')
    if site.mode=='401':return self.send(401,b'')
    if self.headers.get('X-Token')!=site.token:return self.send(410 if site.mode=='expire' else 403,b'')
    if p=='/master.m3u8':
     return self.send(200,b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1\nv/var.m3u8\n',cookie=site.cookie)
    if p=='/redir.m3u8':
     self.send_response(302);self.send_header('Location','http://localhost:%d/master.m3u8'%self.server.server_port);self.end_headers();return
    if p!='/' and 'sid=abc123' not in (self.headers.get('Cookie') or '') and site.mode!='nocookie':return self.send(403,b'')
    if p=='/v/var.m3u8':
     key=b'#EXT-X-KEY:METHOD=%s,URI="k.bin"\n'%(b'SAMPLE-AES' if site.mode=='drm' else b'AES-128')
     return self.send(200,b'#EXTM3U\n'+key+b'#EXTINF:6,\nseg0.ts\n#EXT-X-ENDLIST\n')
    if p=='/v/rot.m3u8':return self.send(200,b'#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\n#EXT-X-KEY:METHOD=AES-128,URI="k.bin"\n#EXTINF:6,\nseg0.ts\n#EXT-X-KEY:METHOD=AES-128,URI="k2.bin"\n#EXTINF:6,\nseg1.ts\n#EXT-X-ENDLIST\n')
    if p=='/v/empty.m3u8':return self.send(200,b'#EXTM3U\n#EXT-X-ENDLIST\n')
    if p=='/plain.mp4':return self.send(200,b'x')
    if p in('/v/k.bin','/v/k2.bin','/v/init.mp4','/v/seg0.ts'):return self.send(200,b'\x00'*16)
    self.send(404,b'')
   def send(self,code,body,cookie=None):
    self.send_response(code)
    if cookie:self.send_header('Set-Cookie',cookie+'; Path=/')
    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  self.srv=ThreadingHTTPServer(('127.0.0.1',0),H);self.port=self.srv.server_port
  threading.Thread(target=self.srv.serve_forever,daemon=True).start()
 def url(self,path='/master.m3u8',host='127.0.0.1'):return 'http://%s:%d%s'%(host,self.port,path)

class Transport:
 """Stands in for the provider's resolver: hands out whatever the site currently accepts, a new link each call."""
 def __init__(self,site,path='/master.m3u8',tokens=None):self.site=site;self.path=path;self.tokens=list(tokens or []);self.calls=0
 def resolve(self,p,cand,req,deadline,cancel):
  self.calls+=1
  token=self.tokens.pop(0) if len(self.tokens)>1 else (self.tokens[0] if self.tokens else self.site.token)
  return {'url':self.site.url(self.path),'headers':{'X-Token':token}}
MOVIE={'media_type':'movie','title':'Example Film','year':2024,'profile':{}}
CAND={'provider':'jacktook','name':'Example.Film.2024.1080p.WEB','quality':'1080p','url':'https://saved.invalid/old','size':1,'seeders':0}

class Fresh(unittest.TestCase):
 def setUp(self):self.site=Site()
 def tearDown(self):self.site.srv.shutdown();self.site.srv.server_close()
 def play(self,path='/master.m3u8',tokens=None):
  return r.play_ready(CAND,MOVIE,Transport(self.site,path,tokens))
 def test_chain_with_header_and_cookie_continuity(self):
  res=self.play();self.assertIn('hls',repr(res));paths=[h[0] for h in self.site.hits]
  self.assertEqual(paths,['/master.m3u8','/v/var.m3u8','/v/k.bin','/v/seg0.ts'])
  self.assertTrue(all(h[1]=='t1' for h in self.site.hits),'header on every request')
  self.assertTrue(all('sid=abc123' in (h[2] or '') for h in self.site.hits[1:]),'cookie from the master on every later request')
  self.assertEqual(self.site.hits[-1][3],'bytes=0-0')
 def test_saved_link_is_never_used(self):
  self.play();self.assertFalse(any('saved.invalid' in h[0] for h in self.site.hits))
 def test_missing_header_is_refused(self):
  class T(Transport):
   def resolve(s,*a):return {'url':s.site.url(),'headers':{}}
  with self.assertRaises(c.Outcome) as cm:r.play_ready(CAND,MOVIE,T(self.site))
  self.assertEqual(cm.exception.kind,c.REFUSED)
 def test_expired_token_gets_one_fresh_resolution(self):
  self.site.mode='expire';self.site.token='new'
  t=Transport(self.site,tokens=['stale','new']);res=r.play_ready(CAND,MOVIE,t)
  self.assertEqual(t.calls,2);self.assertIn('hls',repr(res))
 def test_expired_twice_gives_expired_not_a_loop(self):
  self.site.mode='expire';t=Transport(self.site,tokens=['a','b','c'])
  self.site.token='never'
  with self.assertRaises(c.Outcome) as cm:r.play_ready(CAND,MOVIE,t)
  self.assertEqual((cm.exception.kind,t.calls),(c.EXPIRED,2))
 def test_429_401_and_drm_and_empty_are_typed(self):
  for mode,want in (('429',c.REFUSED),('401',c.ACCOUNT_REQUIRED),('drm',c.UNSUPPORTED)):
   self.site.mode=mode;self.site.token='t1'
   with self.assertRaises(c.Outcome) as cm:self.play();
   self.assertEqual(cm.exception.kind,want,mode)
 def test_playlist_without_segments_is_empty_and_non_hls_is_unsupported(self):
  self.site.mode='nocookie'
  res=r.Resolved(self.site.url('/v/empty.m3u8'),{'X-Token':'t1'},0)
  with self.assertRaises(c.Outcome) as cm:r.verify_chain(res,r.Session(res))
  self.assertEqual(cm.exception.kind,c.EMPTY)
  res=r.Resolved(self.site.url('/plain.mp4'),{'X-Token':'t1'},0);self.assertEqual(r.verify_chain(res)['kind'],'file')
 def test_credentials_do_not_follow_a_redirect_to_another_host(self):
  res=r.Resolved(self.site.url('/redir.m3u8'),{'X-Token':'t1'},0)
  with self.assertRaises(c.Outcome):r.verify_chain(res)    # localhost is another host: the cookie header is dropped on the hop
  self.assertTrue(any(h[0]=='/master.m3u8' for h in self.site.hits))
 def test_cancel_before_resolution(self):
  with self.assertRaises(c.Outcome) as cm:r.play_ready(CAND,MOVIE,Transport(self.site),cancel=lambda:True)
  self.assertEqual(cm.exception.kind,c.CANCELED);self.assertEqual(self.site.hits,[])
 def test_wrong_title_never_resolves(self):
  t=Transport(self.site)
  with self.assertRaises(c.Outcome):r.play_ready(dict(CAND,name='Other.Film.2024.1080p'),MOVIE,t)
  self.assertEqual(t.calls,0)

class Rotation(unittest.TestCase):
 def test_init_segment_and_rotating_keys_are_each_fetched_once(self):
  site=Site();site.mode='nocookie'
  try:
   res=r.Resolved(site.url('/v/rot.m3u8'),{'X-Token':'t1'},0);report=r.verify_chain(res)
   self.assertEqual([h[0] for h in site.hits],['/v/rot.m3u8','/v/k.bin','/v/k2.bin','/v/init.mp4','/v/seg0.ts'])
   self.assertTrue(report['keyed'] and report['mapped'])
  finally:site.srv.shutdown();site.srv.server_close()

class Secrets(unittest.TestCase):
 def test_repr_and_scrub_hide_links_and_tokens(self):
  res=r.Resolved('https://cdn.invalid/a.m3u8?token=SECRET',{'Authorization':'Bearer SECRET'},0)
  self.assertNotIn('SECRET',repr(res)+str(res));self.assertNotIn('cdn.invalid',repr(res))
  text=r.scrub('failed https://cdn.invalid/a.m3u8?token=SECRET&x=1 sig=ABC magnet:?xt=urn:btih:'+'a'*40)
  for bad in ('SECRET','cdn.invalid','ABC','btih'):self.assertNotIn(bad,text)
 def test_split_headers(self):
  self.assertEqual(r.split('https://a.invalid/x|X-Token=1&User-Agent=u'),('https://a.invalid/x',{'X-Token':'1','User-Agent':'u'}))
 def test_stale(self):
  res=r.Resolved('https://a.invalid/x',{},100,ttl=10);self.assertFalse(res.stale(109));self.assertTrue(res.stale(110))

if __name__=='__main__':unittest.main()
