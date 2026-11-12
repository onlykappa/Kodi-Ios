"""Roadmap 1A.1: the app's own Drive streaming proxy (replaces the Google Drive add-on's for Library playback)."""
import io,sys,time,unittest,urllib.request
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import drive_proxy as dp
import driveupload as du

DATA=bytes(range(256))*4096   # 1 MiB

class FakeResp(io.BytesIO):
    def __init__(self,status,body,headers):super().__init__(body);self.status=status;self.h=headers
    def getheader(self,k,d=None):return self.h.get(k,d)

class FakeConn(object):
    log=[];expired=set()
    def request(self,method,path,headers):self.last=(path,dict(headers));FakeConn.log.append(self.last)
    def getresponse(self):
        path,h=self.last
        if h['Authorization']=='Bearer old' and 'old' in FakeConn.expired:return FakeResp(401,b'{}',{})
        if 'files/missing' in path:return FakeResp(404,b'',{})
        rng=h.get('Range')
        if rng:
            a,b=rng.split('=')[1].split('-');a=int(a);b=int(b) if b else len(DATA)-1
            body=DATA[a:b+1]
            return FakeResp(206,body,{'Content-Length':str(len(body)),'Content-Range':'bytes %d-%d/%d'%(a,b,len(DATA)),'Content-Type':'video/mp4'})
        return FakeResp(200,DATA,{'Content-Length':str(len(DATA)),'Content-Type':'video/mp4'})
    def close(self):pass

class Proxy(unittest.TestCase):
    def setUp(self):
        FakeConn.log=[];FakeConn.expired=set();self.tokens=[]
        def token(force):
            t='new' if force else 'old';self.tokens.append(t);return t
        self.server,self.port=dp.start(token,connect=FakeConn)
    def tearDown(self):self.server.shutdown();self.server.server_close()
    def fetch(self,path,headers=None,method='GET'):
        req=urllib.request.Request('http://127.0.0.1:%d%s'%(self.port,path),headers=headers or {},method=method)
        return urllib.request.urlopen(req,timeout=10)
    def test_whole_file_and_a_seek(self):
        with self.fetch('/drive/F1/Movie.mp4') as r:self.assertEqual((r.status,r.read()),(200,DATA))
        with self.fetch('/drive/F1/Movie.mp4',{'Range':'bytes=1000-1999'}) as r:
            self.assertEqual((r.status,r.headers['Content-Range'],r.read()),(206,'bytes 1000-1999/1048576',DATA[1000:2000]))
        self.assertIn('/drive/v3/files/F1?alt=media',FakeConn.log[-1][0]);self.assertEqual(FakeConn.log[-1][1]['Range'],'bytes=1000-1999')
    def test_head_reports_the_size_from_a_one_byte_read(self):
        with self.fetch('/drive/F2/Show.S01E01.mkv',method='HEAD') as r:
            self.assertEqual((r.headers['Content-Length'],r.headers['Accept-Ranges']),('1048576','bytes'))
        self.assertEqual(FakeConn.log[-1][1]['Range'],'bytes=0-0')
    def metadata_response(self,status,headers,body=b'x'):
        reads=[]
        class TrackedResp(FakeResp):
            def read(self,n=-1):
                reads.append(n)
                if n<0:raise AssertionError('An unbounded metadata read would download the movie')
                return super().read(n)
        class Conn(FakeConn):
            def getresponse(self):return TrackedResp(status,body,headers)
        self.server.RequestHandlerClass.upstream.connect=Conn
        return reads
    def test_head_ignored_range_uses_length_without_downloading_video(self):
        reads=self.metadata_response(200,{'Content-Length':'20000000000'})
        with self.fetch('/drive/large/Movie.mp4',method='HEAD') as r:
            self.assertEqual(r.headers['Content-Length'],'20000000000')
        self.assertEqual(reads,[])
    def test_head_partial_response_reads_only_one_byte(self):
        reads=self.metadata_response(206,{'Content-Range':'bytes 0-0/20000000000','Content-Length':'1'})
        with self.fetch('/drive/large/Movie.mp4',method='HEAD') as r:
            self.assertEqual(r.headers['Content-Length'],'20000000000')
        self.assertEqual(reads,[1])
    def test_head_missing_or_malformed_size_never_drains_the_body(self):
        for status,headers in ((200,{}),(206,{'Content-Range':'bytes 0-0/*'})):
            reads=self.metadata_response(status,headers)
            with self.assertRaises(urllib.error.HTTPError):self.fetch('/drive/unknown/Movie.mp4',method='HEAD')
            self.assertEqual(reads,[])
    def test_head_upstream_failure_returns_an_http_error(self):
        def failed(*args):raise OSError('synthetic upstream failure')
        self.server.RequestHandlerClass.upstream.get=failed
        with self.assertRaises(urllib.error.HTTPError) as e:self.fetch('/drive/offline/Movie.mp4',method='HEAD')
        self.assertEqual(e.exception.code,502)
    def test_expired_token_gets_one_fresh_retry(self):
        FakeConn.expired={'old'}
        with self.fetch('/drive/F1/Movie.mp4',{'Range':'bytes=0-9'}) as r:self.assertEqual(r.read(),DATA[:10])
        self.assertEqual(self.tokens,['old','new'])
    def test_actual_drive_token_source_refreshes_a_rejected_unexpired_token(self):
        account={'access_tokens':{'access_token':'old','refresh_token':'synthetic','date':time.time(),'expires_in':3600}}
        refreshes=[]
        def refresh(token):
            refreshes.append(token)
            return {'access_token':'new','expires_in':3600}
        drive=du.Drive(du.token_source(lambda:{'a':account},lambda acc:None,refresh),None)
        self.server.RequestHandlerClass.upstream.token=drive.token
        FakeConn.expired={'old'}
        with self.fetch('/drive/F1/Movie.mp4',{'Range':'bytes=0-9'}) as r:self.assertEqual(r.read(),DATA[:10])
        self.assertEqual(refreshes,['synthetic'])
        self.assertEqual([h['Authorization'] for _,h in FakeConn.log],['Bearer old','Bearer new'])
    def test_unknown_paths_and_files(self):
        for path in ('/other/x','/drive/missing/x.mp4'):
            with self.assertRaises(urllib.error.HTTPError) as e:self.fetch(path)
            self.assertEqual(e.exception.code,404)
    def test_url_and_path_round_trip(self):
        u=dp.url(self.port,'1oH7yt-Hx','Home Alone (1990).mp4')
        self.assertEqual(dp.parse_path(u.split(str(self.port),1)[1]),'1oH7yt-Hx')

if __name__=='__main__':unittest.main()
