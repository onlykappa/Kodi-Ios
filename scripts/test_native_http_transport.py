"""Compile the actual Foundation transport and exercise stalled/oversized HTTP on macOS; no iOS/TV claim."""
import http.server,json,subprocess,sys,tempfile,threading,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(sys.platform=='darwin','Foundation transport executes on the macOS candidate runner')
class Transport(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();cls.root=Path(cls.tmp.name)
  source=(ROOT/'migration/airplay-ios/build-airplay.sh').read_text()
  start=source.index('@interface KodiHTTPResult');end=source.index('__attribute__((visibility("default"))) void kodi_airplay_play(',start)
  main=r'''
int main(int argc,char **argv) {
    @autoreleasepool {
        if(argc!=5)return 2;
        int limit=atoi(argv[4]),used=0;char *out=calloc((size_t)limit+1,1),fields[65536];
        char *payload=calloc(1024*1024,1);memset(payload,'x',1024*1024);
        double before=NSProcessInfo.processInfo.systemUptime;
        int status=kodi_http_send(argv[2],argv[1],"Range: bytes=0-15\n",payload,
            !strcmp(argv[2],"PUT")?1024*1024:0,atof(argv[3]),fields,sizeof fields,out,limit,&used);
        double elapsed=NSProcessInfo.processInfo.systemUptime-before;
        free(payload);free(out); // a late canceled upload may not retain this borrowed pointer
        [[NSRunLoop currentRunLoop] runUntilDate:[NSDate dateWithTimeIntervalSinceNow:0.1]];
        printf("{\"status\":%d,\"bytes\":%d,\"seconds\":%.3f}\n",status,used,elapsed);
        return 0;
    }
}
'''
  path=cls.root/'transport.m';path.write_text('#import <Foundation/Foundation.h>\n#import <dispatch/dispatch.h>\n#include <math.h>\n#include <stdio.h>\n#include <stdlib.h>\n#include <string.h>\n'+source[start:end]+main)
  cls.binary=cls.root/'transport'
  subprocess.run(['xcrun','--sdk','macosx','clang','-fobjc-arc','-fblocks','-O1',str(path),'-framework','Foundation','-o',str(cls.binary)],check=True)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def setUp(self):
  self.release=threading.Event();owner=self
  class Handler(http.server.BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_PUT(self):
    self.rfile.read(int(self.headers.get('Content-Length','0')))
    owner.release.wait(3)
   def do_GET(self):
    try:
     if self.path=='/headers':owner.release.wait(3);return
     self.send_response(200 if self.path=='/ignored' else 206)
     self.send_header('Connection','close')
     if self.path=='/ignored':self.send_header('Content-Length','20000000000')
     elif self.path!='/chunked':self.send_header('Content-Length','16')
     self.end_headers()
     if self.path=='/body':self.wfile.write(b'x');self.wfile.flush();owner.release.wait(3)
     else:self.wfile.write(b'x'*(4096 if self.path=='/chunked' else 16))
    except (BrokenPipeError,ConnectionResetError):pass
  self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler);self.server.daemon_threads=True
  threading.Thread(target=self.server.serve_forever,daemon=True).start()
 def tearDown(self):self.release.set();self.server.shutdown();self.server.server_close()
 def run_request(self,path,method='GET',budget=.3,limit=16):
  answer=subprocess.run([str(self.binary),'http://127.0.0.1:%d%s'%(self.server.server_address[1],path),method,str(budget),str(limit)],capture_output=True,text=True,timeout=5,check=True)
  return json.loads(answer.stdout)
 def test_exact_range_succeeds(self):
  r=self.run_request('/range');self.assertEqual((r['status'],r['bytes']),(206,16))
 def test_headers_body_and_upload_have_absolute_deadlines(self):
  for path,method in (('/headers','GET'),('/body','GET'),('/upload','PUT')):
   with self.subTest(path=path):
    r=self.run_request(path,method);self.assertEqual(r['status'],-1);self.assertLess(r['seconds'],1.5)
 def test_ignored_range_and_unknown_length_cannot_exceed_the_response_limit(self):
  for path in ('/ignored','/chunked'):
   with self.subTest(path=path):
    r=self.run_request(path);self.assertEqual(r['status'],-1);self.assertEqual(r['bytes'],0)

if __name__=='__main__':unittest.main()
