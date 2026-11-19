import sys,threading,unittest,urllib.request,urllib.error,http.cookiejar
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
from sports_hls_proxy import Proxy
class Response:
 def __init__(self,r):self.r=r;self.status_code=r.status;self.headers=r.headers;self.url=r.url
 def __enter__(self):return self
 def __exit__(self,*a):self.r.close()
 def iter_content(self,size):
  while True:
   data=self.r.read(size)
   if not data:break
   yield data
class Session:
 def __init__(self):self.op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def get(self,url,headers,**kw):return Response(self.op.open(urllib.request.Request(url,headers=headers)))
 def close(self):pass
class Test(unittest.TestCase):
 def test_all_resources_have_headers_cookies_and_safe_local_paths(self):
  seen=[]
  class Upstream(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    seen.append((self.path,self.headers.get('Referer'),self.headers.get('Origin'),self.headers.get('Cookie')))
    if self.headers.get('Referer')!='https://source.invalid/' or self.headers.get('Origin')!='https://source.invalid':self.send_error(403);return
    data=b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=100\nchild.m3u8?fresh=1\n' if self.path=='/master' else (b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="/key?fresh=1"\n#EXTINF:6,\nsegment?fresh=1\n' if self.path.startswith('/child') else b'fixture')
    self.send_response(200);self.send_header('Content-Length',str(len(data)))
    if self.path=='/master':self.send_header('Set-Cookie','session=fixture; Path=/')
    self.end_headers();self.wfile.write(data)
  server=ThreadingHTTPServer(('127.0.0.1',0),Upstream);threading.Thread(target=server.serve_forever,daemon=True).start()
  with self.assertRaises(urllib.error.HTTPError):Proxy('http://127.0.0.1:%d/master'%server.server_port,{},Session())
  seen.clear()
  proxy=Proxy('http://127.0.0.1:%d/master'%server.server_port,{'Referer':'https://source.invalid/','Origin':'https://source.invalid'},Session())
  try:
   master=urllib.request.urlopen(proxy.url).read().decode();child=[x for x in master.splitlines() if x and not x.startswith('#')][0]
   media=urllib.request.urlopen(child).read().decode()
   import re
   key=re.search(r'URI="([^"]+)"',media).group(1);segment=[x for x in media.splitlines() if x and not x.startswith('#')][0]
   self.assertTrue(key.endswith('.key'));self.assertTrue(segment.endswith('.ts'));self.assertNotIn('fresh=',segment)
   self.assertEqual(urllib.request.urlopen(key).read(),b'fixture');self.assertEqual(urllib.request.urlopen(segment).read(),b'fixture')
   self.assertEqual(len(seen),5);self.assertTrue(all(x[3]=='session=fixture' for x in seen[1:]));self.assertIn('/segment?fresh=1',[x[0] for x in seen])
  finally:proxy.close();server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
