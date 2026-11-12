"""Roadmap 1A.1: the app's own Drive streaming proxy (replaces the Google Drive add-on's for Library playback)."""
import io,sys,threading,time,unittest,urllib.request
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

class ProxyBase(unittest.TestCase):
    def setUp(self):
        FakeConn.log=[];FakeConn.expired=set();self.tokens=[]
        def token(force):
            t='new' if force else 'old';self.tokens.append(t);return t
        self.server,self.port=dp.start(token,connect=FakeConn)
    def tearDown(self):self.server.shutdown();self.server.server_close()
    def fetch(self,path,headers=None,method='GET'):
        req=urllib.request.Request('http://127.0.0.1:%d%s'%(self.port,path),headers=headers or {},method=method)
        return urllib.request.urlopen(req,timeout=10)

class Proxy(ProxyBase):
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

class Warming(ProxyBase):
    """Roadmap 1A.4: a title's page opening makes the proxy read its start and index before Play is tapped."""
    def setUp(self):
        super().setUp()
        dp.WARM_HEAD,dp.WARM_TAIL=4096,1024   # DATA is 1 MiB; small windows keep the test about the logic
    def tearDown(self):
        dp.WARM_HEAD,dp.WARM_TAIL=4*1024*1024,1024*1024
        super().tearDown()
    def warm_and_wait(self,file_id='W1'):
        self.assertTrue(dp.ask_warm(self.port,file_id,'Movie (2020).mp4'))
        warm=self.server.RequestHandlerClass.warm
        for _ in range(100):
            if warm.get(file_id):break
            time.sleep(.02)
        return warm.get(file_id)
    def test_page_open_reads_the_start_and_the_end_once(self):
        entry=self.warm_and_wait()
        self.assertEqual(entry['size'],len(DATA));self.assertEqual([(s,len(d)) for s,d in entry['chunks']],[(0,4096),(len(DATA)-1024,1024)])
        ranges=[h['Range'] for _,h in FakeConn.log]
        self.assertEqual(ranges,['bytes=0-4095','bytes=%d-%d'%(len(DATA)-1024,len(DATA)-1)])
        self.assertEqual(self.server.RequestHandlerClass.warm.start(None,{},'W1'),'cached')   # a second page open reads nothing
    def test_first_requests_are_answered_without_asking_drive(self):
        self.warm_and_wait();FakeConn.log.clear()
        with self.fetch('/drive/W1/Movie.mp4',method='HEAD') as r:self.assertEqual(r.headers['Content-Length'],str(len(DATA)))
        with self.fetch('/drive/W1/Movie.mp4',{'Range':'bytes=100-199'}) as r:self.assertEqual(r.read(),DATA[100:200])
        with self.fetch('/drive/W1/Movie.mp4',{'Range':'bytes=%d-'%(len(DATA)-500)}) as r:
            self.assertEqual((r.status,r.headers['Content-Range'],r.read()),(206,'bytes %d-%d/%d'%(len(DATA)-500,len(DATA)-1,len(DATA)),DATA[-500:]))
        self.assertEqual(FakeConn.log,[])
        self.assertEqual(self.server.stats.take()['warm_hits'],2)
    def test_a_read_past_the_warm_start_continues_from_drive_exactly(self):
        self.warm_and_wait();FakeConn.log.clear()
        with self.fetch('/drive/W1/Movie.mp4',{'Range':'bytes=0-'}) as r:
            self.assertEqual((r.status,r.headers['Content-Length']),(206,str(len(DATA))));self.assertEqual(r.read(),DATA)
        self.assertEqual([h['Range'] for _,h in FakeConn.log],['bytes=4096-%d'%(len(DATA)-1)])
    def test_warm_keeps_only_two_titles(self):
        for name in ('A','B','C'):self.warm_and_wait(name)
        warm=self.server.RequestHandlerClass.warm
        self.assertEqual((warm.get('A'),bool(warm.get('B')),bool(warm.get('C'))),(None,True,True))
    def test_a_stale_warm_start_is_not_used(self):
        self.warm_and_wait()
        warm=self.server.RequestHandlerClass.warm;warm.clock=lambda:time.time()+dp.WARM_MAX_AGE+1
        self.assertIsNone(warm.get('W1'))

class ReadAhead(ProxyBase):
    """Roadmap 1A.5: a seek's new request is timed, streamed ahead of Kodi and can use a connection opened in advance."""
    def test_seek_requests_are_timed_but_a_start_from_zero_is_not(self):
        with self.fetch('/drive/F1/Movie.mp4',{'Range':'bytes=0-9'}) as r:r.read()
        with self.fetch('/drive/F1/Movie.mp4',{'Range':'bytes=500000-'}) as r:self.assertEqual(r.read(),DATA[500000:])
        taken=self.server.stats.take()
        self.assertEqual((taken['requests'],len(taken['seeks'])),(2,1));self.assertLess(taken['seeks'][0],2)
        self.assertEqual(self.server.stats.take()['requests'],0)   # taking the summary resets it
    def test_the_whole_body_arrives_in_order_through_the_read_ahead_queue(self):
        with self.fetch('/drive/F1/Movie.mp4') as r:self.assertEqual(r.read(),DATA)
    def test_a_stalled_reader_does_not_pin_the_read_ahead_thread(self):
        before=threading.active_count()
        for _ in range(3):
            r=self.fetch('/drive/F1/Movie.mp4',{'Range':'bytes=0-'});r.read(10);r.close()
        time.sleep(1.5)
        self.assertLessEqual(threading.active_count(),before+2)
    def test_a_spare_connection_is_opened_in_advance_and_used_by_the_next_request(self):
        opened=[]
        class Conn(FakeConn):
            def __init__(self):opened.append(self)
            def connect(self):self.connected=True
        up=dp.Upstream(lambda force:'t',Conn,spare=True)
        up._conn()                       # the first request opens one and asks for the next to be prepared
        for _ in range(100):
            if up.spare is not None:break
            time.sleep(.02)
        spare=up.spare;self.assertIsNotNone(spare);self.assertTrue(spare.connected)
        up.drop();self.assertIs(up._conn(),spare)   # after a seek (drop) the next request starts on the spare
    def test_an_old_spare_connection_is_not_trusted(self):
        class Conn(FakeConn):
            def connect(self):pass
        up=dp.Upstream(lambda force:'t',Conn,spare=True);up.spare=Conn();up.spare_at=time.time()-dp.SPARE_MAX_AGE-1
        self.assertIsNone(up._take_spare())

class HoldWhileAirPlayStarts(unittest.TestCase):
    """Roadmap 1G.3: Kodi's own read-ahead (a paused video's file cache) waits while Play on TV starts; the AirPlay
    reader going through the same proxy does not."""
    def setUp(self):
        FakeConn.log=[]
        self.flag={'on':True}
        self.server,self.port=dp.start(lambda force:'t',connect=FakeConn,hold=lambda:self.flag['on'])
        self.saved=dp.HOLD_MAX;dp.HOLD_MAX=1.0
    def tearDown(self):
        dp.HOLD_MAX=self.saved;self.flag['on']=False
        self.server.shutdown();self.server.server_close()
    def timed(self,agent):
        req=urllib.request.Request('http://127.0.0.1:%d/drive/H1/Movie.mp4'%self.port,headers={'User-Agent':agent,'Range':'bytes=0-1023'})
        started=time.time()
        with urllib.request.urlopen(req,timeout=10) as r:body=r.read()
        return time.time()-started,body
    def test_kodi_waits_but_the_airplay_reader_does_not(self):
        took,body=self.timed('Lavf/60.16.100');self.assertLess(took,0.5);self.assertEqual(body,DATA[:1024])
        took,body=self.timed('Kodi/21.3 (iPhone) App_Bitness/64');self.assertGreaterEqual(took,0.9);self.assertEqual(body,DATA[:1024])   # bounded by HOLD_MAX
    def test_kodi_goes_on_the_moment_the_mark_clears(self):
        threading.Timer(0.3,lambda:self.flag.update(on=False)).start()
        took,_=self.timed('Kodi/21.3 (iPhone)');self.assertGreaterEqual(took,0.25);self.assertLess(took,0.9)
    def test_without_a_mark_nothing_waits(self):
        self.flag['on']=False
        took,_=self.timed('Kodi/21.3 (iPhone)');self.assertLess(took,0.5)

class StartingMark(unittest.TestCase):
    def test_mark_is_fresh_for_a_minute_and_clearable(self):
        import airplay
        class Home(dict):
            def setProperty(self,k,v):self[k]=v
            def getProperty(self,k):return self.get(k,'')
        h=Home()
        self.assertFalse(airplay.starting(h,1000.0))
        airplay.mark_starting(h,1000.0)
        self.assertTrue(airplay.starting(h,1030.0));self.assertFalse(airplay.starting(h,1000.0+airplay.STARTING_FOR+1))
        airplay.clear_starting(h);self.assertFalse(airplay.starting(h,1001.0))
    def test_play_on_tv_marks_the_start_and_clears_it_on_every_way_out(self):
        src=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/cast.py').read_text()
        self.assertEqual(src.count('airplay.mark_starting(home,time.time())'),1)
        self.assertEqual(src.count('airplay.clear_starting(home)'),3)     # failure while starting, TV playing, every other outcome
        self.assertLess(src.index('airplay.mark_starting(home,time.time())'),src.index("airplay.clear_starting(home)"))

if __name__=='__main__':unittest.main()
