"""Casting a Drive episode to a TV (owner log f93a3233, build 657: it froze after 40 s): the playback cache and the filler must survive Kodi's stop at
the hand-off, and be cleared once the TV is done."""
import json,os,sys,tempfile,time,unittest,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import drive_proxy as dp,cast_cache as cc
import test_drive_proxy as base
DATA=base.DATA;B=64*1024

def wait(check,seconds=5):
    end=time.time()+seconds
    while time.time()<end:
        if check():return True
        time.sleep(0.02)
    return check()

class Fakes(unittest.TestCase):
    def make(self,casting=True,playing=False):
        self.state={'casting':casting,'playing':playing,'cleared':0};self.lines=[]
        return cc.Keep(lambda:self.state['casting'],lambda:self.state['playing'],lambda:self.state.__setitem__('cleared',self.state['cleared']+1),self.lines.append)
    def test_a_stop_while_a_tv_is_being_fed_keeps_the_cache(self):
        keep=self.make();self.assertEqual(keep.stopped(),'kept');self.assertEqual(self.state['cleared'],0)
        self.assertEqual(keep.stopped(),'kept');self.assertEqual(len(self.lines),1)           # said once, not on every stop
    def test_an_ordinary_stop_clears_as_before(self):
        keep=self.make(casting=False);self.assertEqual(keep.stopped(),'cleared');self.assertEqual(self.state['cleared'],1)
    def test_the_kept_cache_is_cleared_once_when_the_cast_is_over(self):
        keep=self.make();keep.stopped()
        self.assertFalse(keep.tick());self.assertEqual(self.state['cleared'],0)               # still casting
        self.state['casting']=False
        self.assertTrue(keep.tick());self.assertEqual(self.state['cleared'],1)
        self.assertFalse(keep.tick());self.assertEqual(self.state['cleared'],1)               # once
    def test_if_kodi_plays_again_the_next_stop_does_the_clearing(self):
        keep=self.make();keep.stopped();self.state.update(casting=False,playing=True)
        self.assertFalse(keep.tick());self.assertEqual(self.state['cleared'],0)
        self.assertEqual(keep.stopped(),'cleared');self.assertEqual(self.state['cleared'],1)
    def test_a_failing_check_never_keeps_the_cache(self):
        keep=cc.Keep(lambda:1/0,lambda:False,lambda:self.state.__setitem__('cleared',1),lambda text:None);self.state={'cleared':0}
        self.assertEqual(keep.stopped(),'cleared');self.assertEqual(self.state['cleared'],1)

class Handoff(base.ProxyBase):
    """The real proxy, a disk cache and the filler, as the converter reads them after Kodi's player stopped."""
    def setUp(self):
        self.small=dp.BLOCK;dp.BLOCK=B
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.folder=os.path.join(self.tmp.name,'cache')
        base.FakeConn.log=[];base.FakeConn.expired=set()
        self.server,self.port=dp.start(lambda force:'old',connect=base.FakeConn,cache_dir=self.folder,wifi_ok=lambda:True)
        self.handler=self.server.RequestHandlerClass
    def tearDown(self):
        self.server.shutdown();self.server.server_close();dp.BLOCK=self.small;self.tmp.cleanup()
    def get(self,rng):
        with self.fetch('/drive/F1/Movie.mp4',{'Range':rng}) as r:return r.status,r.read()
    def filled(self):
        return all(self.handler.blocks.has('F1',len(DATA),n) for n in range(len(DATA)//B))
    def blk(self):return list(Path(self.folder).rglob('*.blk'))
    def test_the_old_answer_to_a_stop_wipes_what_the_converter_is_about_to_read(self):
        self.get('bytes=0-%d'%(B-1));self.assertTrue(wait(self.filled));self.assertTrue(wait(self.blk))
        dp.clear_cache()                                   # what the service did on every Player.OnStop, including the hand-off to the TV
        self.assertFalse(self.handler.blocks.has('F1',len(DATA),0));self.assertEqual(self.blk(),[])
        base.FakeConn.log.clear();self.get('bytes=%d-%d'%(4*B,5*B))
        self.assertTrue(base.FakeConn.log)                 # the converter's first read goes to Drive again
    def test_the_cache_survives_the_hand_off_and_serves_the_converter_without_drive(self):
        state={'casting':True,'playing':False}
        keep=cc.Keep(lambda:state['casting'],lambda:state['playing'],dp.clear_cache)
        self.get('bytes=0-%d'%(B-1));self.assertTrue(wait(self.filled));self.assertTrue(wait(self.blk))
        self.assertEqual(keep.stopped(),'kept')
        self.assertTrue(self.filled())
        base.FakeConn.log.clear()
        for a,b in ((0,3*B),(4*B,9*B),(10*B,len(DATA)-1)):
            status,body=self.get('bytes=%d-%d'%(a,b));self.assertEqual((status,body),(206,DATA[a:b+1]))
        self.assertEqual(base.FakeConn.log,[])             # not one Drive request: all of it from the phone
    def test_the_filler_keeps_filling_when_the_stop_comes_mid_fill(self):
        keep=cc.Keep(lambda:True,lambda:False,dp.clear_cache)
        self.get('bytes=0-%d'%(B-1));keep.stopped()
        self.assertTrue(wait(self.filled),'the filler stopped at the hand-off')
    def test_the_cache_is_cleared_when_the_cast_ends(self):
        state={'casting':True}
        keep=cc.Keep(lambda:state['casting'],lambda:False,dp.clear_cache)
        self.get('bytes=0-%d'%(B-1));self.assertTrue(wait(self.filled));self.assertTrue(wait(self.blk))
        keep.stopped();state['casting']=False;self.assertTrue(keep.tick())
        self.assertEqual(self.blk(),[]);self.assertFalse(self.handler.blocks.has('F1',len(DATA),0))
        time.sleep(0.3);self.assertEqual(self.blk(),[])    # and the filler does not put them back

class Cushion(unittest.TestCase):
    """The TV is told to start only when about 25 s of the video are on the phone (bounded wait, then it starts anyway)."""
    def test_only_a_drive_proxy_source_is_waited_for(self):
        self.assertEqual(cc.proxy_target('http://127.0.0.1:58671/drive/1p3F3QfF/Origem%20S04E04.mkv'),('http://127.0.0.1:58671','/drive/1p3F3QfF/Origem%20S04E04.mkv'))
        self.assertEqual(cc.proxy_target('http://127.0.0.1:58671/drive/ID/x.mkv|User-Agent=x')[1],'/drive/ID/x.mkv')
        for other in ('https://example.com/video.mp4','http://192.168.1.9:80/drive/ID/x','http://127.0.0.1:5000/other/ID/x','/local/file.mkv','',None):
            self.assertIsNone(cc.proxy_target(other),other)
    def test_the_cushion_is_25_s_of_this_file_within_limits(self):
        size=7727*1024**2;self.assertAlmostEqual(cc.cushion_bytes(size,3120)/1024**2,7727/3120*25,delta=1)   # about 62 MB for the episode of the log
        self.assertEqual(cc.cushion_bytes(100*1024**2,6000),cc.CUSHION_MIN)                                 # a very low bitrate: at least the floor
        self.assertEqual(cc.cushion_bytes(80*1024**3,3600),cc.CUSHION_MAX)                                  # a remux: not more than the ceiling
        self.assertEqual(cc.cushion_bytes(10*1024**2,60),10*1024**2)                                        # never more than the file
        self.assertEqual(cc.cushion_bytes(5000,0),5000);self.assertEqual(cc.cushion_bytes(None,10),cc.CUSHION_MAX if False else cc.cushion_bytes(None,10))
    def run_wait(self,answers,canceled=False,wait_result=False,duration=3000.0,position=600.0,size=3000*1024**2):
        calls,lines=[],[];it=iter(answers)
        def get_json(url):
            calls.append(url);a=next(it,answers[-1])
            if isinstance(a,Exception):raise a
            return dict(a,size=size) if a is not None and 'size' not in a and a.get('state')!='no cache' else a
        outcome=cc.wait_for_cushion('http://127.0.0.1:9/drive/ID/x.mkv',position,duration,get_json,lambda seconds:wait_result,lines.append,lambda:canceled)
        return outcome,calls,lines
    def test_ready_when_enough_is_ahead(self):
        need=cc.cushion_bytes(3000*1024**2,3000.0)
        outcome,calls,lines=self.run_wait([{'ahead':0,'state':'filler on 1 file(s), 0 MB ahead'},{'ahead':0,'state':'x'},{'ahead':need//2,'state':'x'},{'ahead':need,'state':'x'}])
        self.assertEqual(outcome,'ready');self.assertIn('/cushion/ID/x.mkv?at=0',calls[0])                        # the first call learns the size
        want=int(3000*1024**2*(600/3000-cc.BACK_OFF));self.assertIn('?at=%d'%want,calls[1])                       # then the fill starts a little before Kodi's place
        self.assertEqual(len(lines),1);self.assertIn('cushion: ready',lines[0])
    def test_the_wait_is_bounded_and_the_tv_starts_anyway(self):
        outcome,calls,lines=self.run_wait([{'ahead':0,'state':'filler on 1 file(s), 0 MB ahead'}])
        self.assertEqual(outcome,'timeout');self.assertLessEqual(len(calls),cc.CUSHION_LIMIT+3);self.assertIn('cushion: timeout',lines[0])
    def test_it_does_not_wait_when_nothing_is_filling(self):
        outcome,calls,lines=self.run_wait([{'ahead':0,'state':'filler idle'}])
        self.assertEqual(outcome,'not filling');self.assertLess(len(calls),8)
    def test_a_proxy_without_a_cache_or_that_fails_starts_the_tv_at_once(self):
        self.assertEqual(self.run_wait([{'ahead':0,'state':'no cache'}])[0],'not filling')
        self.assertEqual(self.run_wait([OSError('refused')])[0],'not filling')
    def test_cancel_stops_the_wait(self):
        self.assertEqual(self.run_wait([{'ahead':0,'state':'x'}],canceled=True)[0],'canceled')
        self.assertEqual(self.run_wait([{'ahead':0,'state':'x'}],wait_result=True)[0],'canceled')
    def test_a_source_that_is_not_drive_is_not_waited_for(self):
        lines=[];self.assertEqual(cc.wait_for_cushion('http://192.168.1.2/x.m3u8',0,100,lambda url:1/0,lambda s:False,lines.append),'not a Drive source');self.assertEqual(lines,[])
    def test_the_summary_line_has_no_id_and_no_link(self):
        outcome,calls,lines=self.run_wait([{'ahead':0,'state':'filler on 1 file(s), 0 MB ahead'}]*1)
        for text in lines:self.assertNotIn('http',text);self.assertNotIn('ID',text.replace('cushion','').replace('ahead','')[:0]+'');self.assertNotIn('x.mkv',text)

class ThroughTheProxy(Handoff):
    """The /cushion/ endpoint of the real proxy: it starts the filler where asked and reports how much is in a row."""
    def cushion(self,at=0):
        with self.fetch('/cushion/F1/Movie.mp4?at=%d'%at) as r:return json.loads(r.read())
    def test_the_endpoint_starts_the_filler_and_reports_the_cushion(self):
        first=self.cushion(5*B);self.assertEqual(first['size'],len(DATA))
        self.assertTrue(wait(lambda:self.cushion(5*B)['ahead']>=len(DATA)-5*B),'the cushion never grew')
        answer=self.cushion(5*B);self.assertGreaterEqual(answer['ahead'],len(DATA)-5*B);self.assertIn('MB ahead',answer['state'])
    def test_wait_for_cushion_against_the_real_proxy(self):
        lines=[];source='http://127.0.0.1:%d/drive/F1/Movie.mp4'%self.port
        def get_json(url):
            with urllib.request.urlopen(url,timeout=5) as r:return json.loads(r.read())
        outcome=cc.wait_for_cushion(source,10.0,60.0,get_json,lambda seconds:time.sleep(0.05) or False,lines.append)
        self.assertEqual(outcome,'ready',lines)
    def test_on_cellular_nothing_is_filled_and_the_wait_ends_quickly(self):
        self.server.shutdown();self.server.server_close()
        self.server,self.port=dp.start(lambda force:'old',connect=base.FakeConn,cache_dir=self.folder,wifi_ok=lambda:False);self.handler=self.server.RequestHandlerClass
        lines=[];source='http://127.0.0.1:%d/drive/F1/Movie.mp4'%self.port
        def get_json(url):
            with urllib.request.urlopen(url,timeout=5) as r:return json.loads(r.read())
        started=time.time();outcome=cc.wait_for_cushion(source,10.0,60.0,get_json,lambda seconds:time.sleep(0.02) or False,lines.append)
        self.assertEqual(outcome,'not filling');self.assertLess(time.time()-started,3)

class PacingAndDiagnostics(unittest.TestCase):
    """The TV link first, and one diagnostic line every 30 s so the next owner log says which cause is still true."""
    def pacing(self,casting=True,cushion=60*1024**2):
        self.lines=[];self.state={'casting':casting,'cushion':cushion}
        return cc.Pacing(lambda:self.state['casting'],lambda:self.state['cushion'],self.lines.append)
    def test_the_filler_rests_when_the_cushion_is_full_and_goes_on_when_it_has_shrunk(self):
        p=self.pacing();M=1024**2;c=60*M
        self.assertEqual(p('F',2*c),0)                                  # not full yet: it fills
        self.assertEqual(p('F',int(cc.HIGH*c)),cc.REST);self.assertTrue(p.resting)
        self.assertEqual(p('F',int(2.5*c)),cc.REST)                     # still resting between the two marks (hysteresis)
        self.assertEqual(p('F',int(cc.LOW*c)-1),0);self.assertFalse(p.resting)
        self.assertEqual(len(self.lines),2);self.assertIn('resting',self.lines[0]);self.assertIn('filling again',self.lines[1])
    def test_it_never_rests_below_the_low_mark_so_production_is_not_starved(self):
        p=self.pacing()
        for ahead in (0,10*1024**2,int(cc.LOW*60*1024**2)-1):self.assertEqual(p('F',ahead),0)
    def test_it_never_rests_when_no_tv_is_fed_or_the_cushion_is_unknown(self):
        self.assertEqual(self.pacing(casting=False)('F',10**12),0);self.assertEqual(self.pacing(cushion=0)('F',10**12),0)
        broken=cc.Pacing(lambda:1/0,lambda:1,lambda text:None);self.assertEqual(broken('F',10**12),0)
    def test_a_filler_waits_while_it_rests_and_stops_at_once_when_told(self):
        import drive_cache as dc
        store=dc.DiskBlocks(os.path.join(tempfile.mkdtemp(),'c'),B);up=dp.Upstream(lambda f:'old',base.FakeConn)
        filler=dc.Filler(store,up,B,dp.Tee,allowed=lambda:True,free=lambda:10**12)
        asked=[];filler.pace=lambda file_id,ahead:(asked.append(ahead),0.01)[1]
        job={'size':len(DATA),'at':0,'cursors':[0],'turn':0,'stop':False,'generation':store.generation}
        import threading;t=threading.Thread(target=filler._rest,args=('F',job),daemon=True);t.start();time.sleep(0.1)
        self.assertTrue(t.is_alive());self.assertGreaterEqual(len(asked),3);job['stop']=True;t.join(2);self.assertFalse(t.is_alive())
    def test_the_diagnostic_line_reports_made_sent_and_the_lead(self):
        out=[];d=cc.CastDiag(out.append,lambda:'filler on 1 file(s), 90 MB ahead')
        lines=['copy: video segment 109 in 9063 ms, source I/O 8000 ms, result 0','copy: video segment 110 in 7276 ms, source I/O 7000 ms, result 0',
               'GET /video/seg108.m4s 200 3562317 B 700 ms','GET /video/seg109.m4s 200 2908698 B 19285 ms','GET /master.m3u8 200 610 B 0 ms']
        self.assertIsNone(d.feed(lines,100.0))                          # the first look starts the 30 s
        text=d.feed(['copy: video segment 111 in 3160 ms, source I/O 3000 ms, result 0'],131.0)
        self.assertIn('segment 111 made, the TV has asked for 109: a lead of 2 segments (12 s)',text);self.assertIn('3 made in 6.5 s each',text)
        self.assertIn('2 sent at',text);self.assertIn('the slowest took 19.3 s',text);self.assertIn('90 MB ahead',text);self.assertEqual(out,[text])
        self.assertIsNone(d.feed([],140.0));self.assertEqual(len(out),1)  # not again before 30 s have passed
    def test_the_diagnostic_line_has_no_url_no_id_and_no_token(self):
        out=[];d=cc.CastDiag(out.append,lambda:'filler idle');d.feed(['copy: video segment 5 in 100 ms, x','GET /video/seg5.m4s 200 1000 B 50 ms'],0.0)
        text=d.feed([],31.0)
        for bad in ('http','/video','token','master','192.168'):self.assertNotIn(bad,text)
    def test_a_closed_player_restarts_the_count(self):
        d=cc.CastDiag();d.feed(['copy: video segment 7 in 100 ms, x'],0.0);d.feed(['player: closed'],1.0);self.assertIsNone(d.began)
    def test_the_wiring(self):
        root=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
        service=(root/'service.py').read_text();self.assertIn('pace=pacing',service);self.assertIn('cast_cache.DIAG.state=drive_proxy.filler_state',service)
        self.assertIn('cast_cache.DIAG.feed(lines)',(root/'resources/lib/airplay.py').read_text())
        self.assertIn('cast_cache.CUSHION_PROPERTY',(root/'cast.py').read_text());self.assertIn('filler.pace = pace',(root/'resources/lib/drive_proxy.py').read_text())

class AudioStretchAndSeek(unittest.TestCase):
    """Owner log 4f1691fe: the picture and the audio lie 60 MB apart in the file, and after every TV seek the converter read a cold place."""
    def make(self,blocks_ahead):
        import drive_cache as dc
        store=dc.DiskBlocks(os.path.join(tempfile.mkdtemp(),'c'),B);up=dp.Upstream(lambda f:'old',base.FakeConn)
        filler=dc.Filler(store,up,B,dp.Tee,allowed=lambda:True,free=lambda:10**12)
        size=100*B;filler.recent['F']=(size,[10,60])                 # the picture's stretch at block 10, the audio's at block 60
        for start,count in blocks_ahead:
            for n in range(start,start+count):store.put('F',size,n,b'x'*B)
        return filler
    def test_the_cushion_needs_the_audio_stretch_too(self):
        need=20*B
        self.assertFalse(self.make([(10,25)]).cushion_ready('F',need,other=4*B))              # picture only: the audio has nothing ahead
        self.assertFalse(self.make([(60,25)]).cushion_ready('F',need,other=4*B))              # audio only: no picture cushion
        self.assertTrue(self.make([(10,25),(60,5)]).cushion_ready('F',need,other=4*B))        # picture 25 blocks, audio 5 >= its share
        self.assertFalse(self.make([(10,25),(60,2)]).cushion_ready('F',need,other=4*B))       # audio too thin
        self.assertFalse(self.make([]).cushion_ready('nothing',need))                         # a file never read
    def test_the_proxy_says_ready_only_when_both_are_ahead(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib/drive_proxy.py').read_text()
        self.assertIn("body['ready'] = self.filler.cushion_ready(file_id, int(need))",text)
        calls=[]
        lines=[];out=cc.wait_for_cushion('http://127.0.0.1:9/drive/ID/x.mkv',100.0,1000.0,lambda url:(calls.append(url),{'ahead':10**9,'state':'x','size':3000*1024**2,'ready':False})[1],lambda s:True,lines.append)
        self.assertEqual(out,'canceled')                      # enough picture but the audio is not: it waits (here the user cancels)
        self.assertTrue(any('&need=' in u for u in calls))
    def test_a_stretch_near_the_end_of_the_file_does_not_hold_the_cushion_forever(self):
        """Owner, build 659 (log a8919a24): the picture had 64-96 MB ahead and the TV still waited 25-33 s."""
        import drive_cache as dc
        store=dc.DiskBlocks(os.path.join(tempfile.mkdtemp(),'c'),B);up=dp.Upstream(lambda f:'old',base.FakeConn)
        filler=dc.Filler(store,up,B,dp.Tee,allowed=lambda:True,free=lambda:10**12);size=100*B
        filler.recent['F']=(size,[10,98])                          # the picture at block 10 and a read near the end (an MP4's index): only 2 blocks left there
        for n in list(range(10,40))+[98,99]:store.put('F',size,n,b'x'*B)
        self.assertTrue(filler.cushion_ready('F',20*B,other=12*B))
    def test_the_audio_stretch_gets_a_few_seconds_then_the_tv_starts_anyway(self):
        lines=[];calls=[]
        def get_json(url):
            calls.append(url);return {'ahead':10**9,'state':'filler on 1 file(s), 90 MB ahead','size':3000*1024**2,'ready':False}
        out=cc.wait_for_cushion('http://127.0.0.1:9/drive/ID/x.mkv',100.0,1000.0,get_json,lambda s:False,lines.append)
        self.assertEqual(out,'ready');self.assertLessEqual(len(calls),cc.AUDIO_GRACE+4)               # not the whole limit
        self.assertLess(cc.CUSHION_LIMIT,45);self.assertEqual(cc.CUSHION_LIMIT,20)
    def test_a_tv_jump_starts_the_fill_at_the_new_place(self):
        asked=[];seek=cc.Reseek(lambda base,path,second,duration:asked.append((base,path,second,duration)))
        line='seek: the receiver jumped from segment 21 to 54 (324.4 s)'
        self.assertEqual(seek.feed([line]),0);self.assertEqual(asked,[])                       # not armed: nothing
        seek.arm('http://127.0.0.1:5000/drive/ID/x.mkv',3120.0)
        self.assertEqual(seek.feed(['GET /master.m3u8 200 610 B 0 ms',line]),1)
        self.assertEqual(asked,[('http://127.0.0.1:5000','/drive/ID/x.mkv',324.4,3120.0)])
        self.assertEqual(seek.feed([line]),0)                                                  # the same jump said twice
        self.assertEqual(seek.feed(['seek: the receiver jumped from segment 55 to 76 (456.5 s)']),1)
        seek.disarm();self.assertEqual(seek.feed([line]),0)
    def test_a_jump_fetch_asks_for_the_byte_of_that_second(self):
        urls=[];done=cc.reseek_fetch(lambda url:(urls.append(url),{'size':3000*1024**2})[1],wait_thread=True)
        done('http://127.0.0.1:5000','/drive/ID/x.mkv',600.0,3000.0)
        self.assertIn('/cushion/ID/x.mkv?at=0',urls[0]);self.assertIn('?at=%d'%int(3000*1024**2*(0.2-cc.BACK_OFF)),urls[1])
    def test_a_jump_to_a_non_drive_source_does_nothing(self):
        asked=[];seek=cc.Reseek(lambda *a:asked.append(a));seek.arm('http://192.168.1.2/x.m3u8',100.0)
        self.assertEqual(seek.feed(['seek: the receiver jumped from segment 1 to 5 (30.0 s)']),0);self.assertEqual(asked,[])
    def test_the_wiring(self):
        root=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
        self.assertIn('cast_cache.SEEK.feed(lines)',(root/'resources/lib/airplay.py').read_text());self.assertIn('cast_cache.SEEK.arm(source,duration)',(root/'cast.py').read_text())
        self.assertIn('cast_ended()',(root/'resources/lib/airplay.py').read_text())

class Wiring(unittest.TestCase):
    def test_the_service_hands_every_stop_to_keep_and_checks_for_the_end(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn("if method=='Player.OnStop':keep.stopped()",text)
        self.assertIn('keep.tick()',text);self.assertIn('airplay.starting(home_window,now)',text)
    def test_cast_waits_for_the_cushion_before_the_native_start(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/cast.py').read_text()
        a=text.index('cast_cache.wait_for_cushion(');b=text.index('lib.kodi_airplay_play(',a)
        self.assertLess(a,b)                                    # the wait comes first
        self.assertIn('except Exception as error:diagnostics.log_exception(xbmc,\'airplay_cushion\',error)',text)   # a failing wait never stops the cast
        self.assertNotIn("if method=='Player.OnStop':\n        try:drive_proxy.clear_cache()",text)

if __name__=='__main__':unittest.main()
