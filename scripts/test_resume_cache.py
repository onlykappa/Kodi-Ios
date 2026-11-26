"""The opening of the last Umbrella stream is kept on the phone so a second Continue starts from disk (owner, build 623 log 8c570737: 11.3 s, then 10.7 s)."""
import importlib.util,io,os,sys,tempfile,time,unittest,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
LIB=ROOT/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import remote_media as rm,resume_cache as rc

DATA=bytes((i*7+i//251)%256 for i in range(30*1024*1024))   # 30 MiB: 8 blocks
LINK='https://dl.example.invalid/secret-token/Episode.mkv|User-Agent=Kodi'

class Reply(io.BytesIO):
    def __init__(self,a,b):
        super().__init__(DATA[a:b+1]);self.status=206
        self.headers={'Content-Range':'bytes %d-%d/%d'%(a,min(b,len(DATA)-1),len(DATA))}
    def getcode(self):return self.status
calls=[]
def opener(request,timeout):
    a,b=map(int,request.get_header('Range')[6:].split('-'));calls.append((a,b));return Reply(a,min(b,len(DATA)-1))
def dead(request,timeout):
    calls.append('dead');raise OSError('network is slow or gone')

class Disk(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.mkdtemp();self.root=os.path.join(self.dir,'o');calls.clear()
        self.addCleanup(__import__('shutil').rmtree,self.dir,True)
    def test_the_plan_is_the_start_the_end_and_the_blocks_around_the_resume_point(self):
        self.assertEqual(rc.plan(len(DATA),0.5),[0,1,2,3,4,5,6,7])   # 8 blocks: 0-7 the opening (build 677 log: Kodi read blocks 6 and 7), 2,3,4 around block 3, 7 last
        self.assertEqual(rc.plan(len(DATA),None),[0,1,2,3,4,5,6,7]);self.assertEqual(rc.plan(len(DATA),0.02),[0,1,2,3,4,5,6,7]);self.assertEqual(rc.plan(0,.5),[])
        self.assertLessEqual(len(rc.plan(10**12,0.5)),rc.MAX_BLOCKS)
    def test_store_load_ready_round_trip_and_nothing_of_the_link_is_written(self):
        blocks={0:DATA[:rc.BLOCK],7:DATA[7*rc.BLOCK:]}
        self.assertEqual(rc.store(LINK,len(DATA),blocks,0.5,self.root),2)
        self.assertTrue(rc.ready(LINK,self.root));self.assertFalse(rc.ready(LINK+'x',self.root))
        size,found=rc.load(LINK,self.root);self.assertEqual(size,len(DATA));self.assertEqual(found,blocks)
        for path in Path(self.root).rglob('*'):
            if path.is_file() and path.suffix!='.blk':self.assertNotIn('secret-token',path.read_text())
        self.assertNotIn('secret-token',' '.join(p.name for p in Path(self.root).rglob('*')))
    def test_a_short_or_damaged_block_is_not_kept_or_not_used(self):
        self.assertEqual(rc.store(LINK,len(DATA),{0:b'short'},0.5,self.root),0);self.assertFalse(rc.ready(LINK,self.root))
        rc.store(LINK,len(DATA),{0:DATA[:rc.BLOCK],1:DATA[rc.BLOCK:2*rc.BLOCK]},0.5,self.root)
        (Path(self.root)/rc.key(LINK)/'1.blk').write_bytes(b'cut');self.assertEqual(sorted(rc.load(LINK,self.root)[1]),[0])
        (Path(self.root)/rc.key(LINK)/'meta.json').write_text('{no');self.assertFalse(rc.ready(LINK,self.root));self.assertIsNone(rc.load(LINK,self.root))
    def test_the_last_three_titles_are_kept_and_the_oldest_goes(self):
        links=['https://x.invalid/%d.mkv'%i for i in range(4)]
        for i,l in enumerate(links):rc.store(l,len(DATA),{0:DATA[:rc.BLOCK]},0.5,self.root,now=lambda i=i:1000.0+i)
        self.assertEqual([rc.ready(l,self.root) for l in links],[False,True,True,True])
        self.assertEqual(len(os.listdir(self.root)),3)
    def test_storing_a_title_again_replaces_only_that_title(self):
        a,b='https://x.invalid/a.mkv','https://x.invalid/b.mkv'
        rc.store(a,len(DATA),{0:DATA[:rc.BLOCK]},0.5,self.root);rc.store(b,len(DATA),{0:DATA[:rc.BLOCK]},0.5,self.root)
        rc.store(a,len(DATA),{0:DATA[:rc.BLOCK],1:DATA[rc.BLOCK:2*rc.BLOCK]},0.5,self.root)
        self.assertTrue(rc.ready(b,self.root));self.assertEqual(sorted(rc.load(a,self.root)[1]),[0,1])
    def test_a_title_older_than_72_hours_goes(self):
        a,b='https://x.invalid/a.mkv','https://x.invalid/b.mkv'
        rc.store(a,len(DATA),{0:DATA[:rc.BLOCK]},0.5,self.root,now=lambda:1000.0)
        rc.store(b,len(DATA),{0:DATA[:rc.BLOCK]},0.5,self.root,now=lambda:1000.0+73*3600)
        self.assertFalse(rc.ready(a,self.root));self.assertTrue(rc.ready(b,self.root))
    def test_the_old_one_title_files_are_removed(self):
        os.makedirs(self.root);(Path(self.root)/'0.blk').write_bytes(b'x');(Path(self.root)/'meta.json').write_text('{}')
        rc.store(LINK,len(DATA),{0:DATA[:rc.BLOCK]},0.5,self.root)
        self.assertEqual(sorted(os.listdir(self.root)),[rc.key(LINK)])
    def test_worst_case_size_is_144_mib(self):
        self.assertEqual(rc.TITLES*rc.MAX_BLOCKS*rc.BLOCK//(1024*1024),144)

class Capture(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.mkdtemp();self.root=os.path.join(self.dir,'o');calls.clear();self.logs=[]
        self.addCleanup(__import__('shutil').rmtree,self.dir,True)
    def test_a_stopped_stream_keeps_its_start_its_end_and_the_blocks_around_where_it_stopped(self):
        kept=rc.capture(LINK,0.5,lambda link:rm.Foreground(link,open_url=opener),self.root,self.logs.append)
        self.assertEqual(kept,8);self.assertTrue(rc.ready(LINK,self.root));self.assertIn('kept 8 of 8 blocks',self.logs[0])
        size,found=rc.load(LINK,self.root);self.assertEqual(sorted(found),[0,1,2,3,4,5,6,7]);self.assertEqual(found[4],DATA[4*rc.BLOCK:5*rc.BLOCK])
        before=len(calls);self.assertEqual(rc.capture(LINK,0.5,lambda link:rm.Foreground(link,open_url=opener),self.root),0)   # the same stop again: already kept
    def test_a_capture_lets_go_at_once_when_a_video_is_opening(self):
        # build 639 log 9f7b4ab2: six connections to the debrid server were still reading when Continue asked for the title
        import threading
        release=threading.Event()
        def slow(request,timeout):
            a,b=map(int,request.get_header('Range')[6:].split('-'))
            if a>=2*rc.BLOCK:release.wait(5)
            return Reply(a,min(b,len(DATA)-1))
        began=time.monotonic()
        kept=rc.capture(LINK,0.5,lambda link:rm.Foreground(link,open_url=slow),self.root,self.logs.append,stop=lambda:True,poll=0.01)
        release.set()
        self.assertLess(time.monotonic()-began,4);self.assertIn('stopped early',self.logs[-1]);self.assertLess(kept,6)
    def test_the_capture_reads_two_blocks_at_a_time_the_start_and_end_first_and_only_while_the_screen_is_untouched(self):
        """Owner log d78de521: ten blocks read at once slowed Sports from 0.15 s to 1.2 s and the Home list to 16 fps; the capture now has two readers, starts with the file's start and end,
        and starts a block only after the person has stopped touching the screen."""
        import threading
        size=10*rc.BLOCK;order=[];running=[0,0];lock=threading.Lock();state={'idle':False}
        class Stub:
            def __init__(self):
                self.sizes={'media':size};self.data={};self.lock=threading.RLock();self.blocks=self
            def get(self,name,index):
                with lock:
                    order.append(index);running[0]+=1;running[1]=max(running[1],running[0])
                time.sleep(0.03)
                with self.lock:self.data[('media',index)]=bytes(min(rc.BLOCK,size-index*rc.BLOCK))
                with lock:running[0]-=1
            def close(self):pass
        box={}
        def go():box['kept']=rc.capture(LINK,0.5,lambda link:Stub(),self.root,self.logs.append,poll=0.01,idle=lambda:state['idle'])
        t=threading.Thread(target=go);t.start();time.sleep(0.3)
        self.assertEqual(order,[0])   # only the size probe: nothing else starts while the screen is being touched
        state['idle']=True;t.join(10)
        self.assertEqual(running[1],2)                       # two at a time, never more
        self.assertEqual(sorted(order[1:3]),[0,9])           # the start and the end first
        self.assertEqual(box['kept'],len(rc.plan(size,0.5)))
    def test_a_failure_keeps_nothing_and_never_raises(self):
        self.assertEqual(rc.capture(LINK,0.5,lambda link:rm.Foreground(link,open_url=dead),self.root,self.logs.append),0);self.assertFalse(rc.ready(LINK,self.root))
    def test_only_an_umbrella_stream_with_a_place_to_resume_on_wifi_is_kept(self):
        made=[]
        def go(entry,wifi=True):
            t=rc.capture_later(entry,lambda link:(made.append(link),rm.Foreground(link,open_url=opener))[1],wifi=lambda:wifi,root=self.root)
            if t:t.join(20)
            return t
        good={'player':'umbrella','stream':{'url':LINK},'position':600,'total':1400}
        self.assertIsNone(go(dict(good,player='elementum')));self.assertIsNone(go(dict(good,position=2)));self.assertIsNone(go(dict(good,position=1350)))
        self.assertIsNone(go(dict(good,stream={'url':'http://127.0.0.1:1/x'})));self.assertIsNone(go({}));self.assertIsNone(go(good,wifi=False));self.assertEqual(made,[])
        self.assertIsNotNone(go(good));self.assertEqual(made,[LINK]);self.assertTrue(rc.ready(LINK,self.root))

class Planning(unittest.TestCase):
    """Owner log 94a6a00c: Kodi read blocks 6 and 7 of the file's start and block 97 at the resume point; 6 head blocks and a percentage guess had kept others."""
    def test_eight_head_blocks_and_the_resume_point_and_the_end_come_first_within_the_cap(self):
        size = 1826589681; last = (size - 1) // rc.BLOCK
        kept = rc.plan(size, 0.2246, cue_offset=410245402)
        self.assertLessEqual(len(kept), rc.MAX_BLOCKS)
        self.assertTrue({0, 1, 2, 3, 4, 5, 6, 7} <= set(kept)); self.assertIn(last, kept)
        self.assertTrue({410245402 // rc.BLOCK, 410245402 // rc.BLOCK + 1} <= set(kept))        # block 97 and the one after it
        self.assertEqual(kept, sorted(kept))
    def test_without_the_index_the_guess_keeps_three_blocks_around_it_and_the_cap_never_drops_the_resume_point_or_the_end(self):
        size = 30 * rc.BLOCK; kept = rc.plan(size, 0.5)
        self.assertTrue({14, 15, 16} <= set(kept)); self.assertIn(29, kept)
        self.assertEqual(len(rc.plan(size, 0.5)), len(set(rc.plan(size, 0.5))))
        small = rc.plan(3 * rc.BLOCK, 0.5); self.assertEqual(small, [0, 1, 2])
    def test_the_worst_case_is_still_144_mib_for_three_titles(self):
        self.assertEqual(rc.TITLES * rc.MAX_BLOCKS * rc.BLOCK // (1024 * 1024), 144)
    def test_capture_keeps_the_block_kodi_seeks_to_found_from_the_files_own_index(self):
        """A real Matroska file (made here with ffmpeg: about 75 MB, a keyframe every 2 s): the block Kodi reads at the resume time is found from the file's own Cues.
        In the rig an 81 MiB file resumed at 30 s was read from byte 39427588 while the percentage guess said 42.2 MB (3 blocks away)."""
        import shutil, subprocess, threading
        if not shutil.which('ffmpeg'):
            self.skipTest('needs ffmpeg')
        folder = tempfile.mkdtemp(); self.addCleanup(shutil.rmtree, folder, True)
        video = os.path.join(folder, 'v.mkv')
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=640x360:r=24:d=60', '-c:v', 'libx264', '-preset', 'ultrafast', '-b:v', '10M', '-minrate', '10M', '-maxrate', '10M', '-bufsize', '20M', '-x264-params', 'nal-hrd=cbr', '-g', '48', '-pix_fmt', 'yuv420p', video])
        data = Path(video).read_bytes(); size = len(data)
        self.assertGreater(size, 12 * rc.BLOCK)                       # enough blocks for the resume point to be away from the start
        import link_warm
        want = link_warm.resume_offset(data[:rc.BLOCK], data[-rc.BLOCK:], size, 30.0)
        self.assertIsNotNone(want)
        class Stub:
            def __init__(self):
                self.sizes = {'media': size}; self.data = {}; self.lock = threading.RLock(); self.blocks = self
            def get(self, name, index):
                chunk = data[index * rc.BLOCK:(index + 1) * rc.BLOCK]
                with self.lock: self.data[('media', index)] = chunk
            def close(self): pass
        root = os.path.join(folder, 'kept')
        kept = rc.capture('https://x.invalid/a.mkv', 30.0 / 60.0, lambda link: Stub(), root, poll=0.01, seconds=30.0)
        _, blocks = rc.load('https://x.invalid/a.mkv', root)
        self.assertIn(want // rc.BLOCK, blocks); self.assertIn(want // rc.BLOCK + 1, blocks)    # where Kodi seeks, and the block after it
        self.assertLessEqual(kept, rc.MAX_BLOCKS)


class Serving(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.mkdtemp();self.root=os.path.join(self.dir,'o');calls.clear()
        self.addCleanup(__import__('shutil').rmtree,self.dir,True)
        rc.capture(LINK,0.5,lambda link:rm.Foreground(link,open_url=opener),self.root);calls.clear()
        os.environ['KODI_IOS_RESUME_CACHE']=self.root;self.addCleanup(os.environ.pop,'KODI_IOS_RESUME_CACHE',None)
    def test_a_kept_opening_is_ready_at_once_and_kodis_reads_need_no_network(self):
        broker=rm.Broker(source_factory=lambda source:rm.Foreground(source,open_url=dead));self.addCleanup(broker.close)
        answer=rm._call(broker.url,{'action':'open','source':LINK,'player':'kodi','resume':0.5})
        stats={}
        for _ in range(100):
            stats=rm._call(broker.url,{'action':'stats','id':answer['id']})['stats']
            if stats.get('opening_ready'):break
            time.sleep(.02)
        self.assertTrue(stats['opening_ready']);self.assertEqual(stats['size'],len(DATA))
        with urllib.request.urlopen(urllib.request.Request(answer['url'],headers={'Range':'bytes=0-99999'}),timeout=5) as r:self.assertEqual(r.read(),DATA[:100000])        # the file's start
        at=int(len(DATA)*0.5)
        with urllib.request.urlopen(urllib.request.Request(answer['url'],headers={'Range':'bytes=%d-%d'%(at,at+99999)}),timeout=5) as r:self.assertEqual(r.read(),DATA[at:at+100000])   # the resume point
        with urllib.request.urlopen(urllib.request.Request(answer['url'],headers={'Range':'bytes=%d-%d'%(len(DATA)-5000,len(DATA)-1)}),timeout=5) as r:self.assertEqual(r.read(),DATA[-5000:])
    def test_another_link_is_not_given_these_blocks(self):
        broker=rm.Broker(source_factory=lambda source:rm.Foreground(source,open_url=opener));self.addCleanup(broker.close)
        rm._call(broker.url,{'action':'open','source':'https://other.invalid/z.mkv','player':'kodi'});time.sleep(.2)
        source=broker.current;self.assertEqual(rc.seed(source,'https://other.invalid/z.mkv',self.root),0)

class Wiring(unittest.TestCase):
    def test_the_pieces_are_connected(self):
        lib=ROOT/'migration/bundled-bootstrap/resources/lib'
        self.assertIn('seeded=resume_cache.seed(broker.current,source)',(lib/'remote_media.py').read_text())
        portrait=(lib/'portrait.py').read_text()
        self.assertIn('on_stop=keep_opening',portrait);self.assertIn('if on_stop and entry:',portrait);self.assertIn('resume_cache.capture_later(entry,',portrait)
        watch=(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py').read_text()
        self.assertIn('if route is None and _opening_kept(url):route=_cache_route',watch)
    def test_continue_uses_the_cache_only_when_the_opening_is_kept(self):
        spec=importlib.util.spec_from_file_location('watch_resume',ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_watch_dialog.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        sys.path.insert(0,str(ROOT/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib'));import ios_continue as c
        box={'t':'{}'};read=lambda l:box['t'];write=lambda l,t:box.__setitem__('t',t)
        import types
        pl=types.SimpleNamespace(tmdb_type='tv',tmdb_id='312359',season='1',episode='1',details=types.SimpleNamespace(infolabels={'title':'t','tvshowtitle':'s'},art={}))
        c.record(pl,read,write,choice='umbrella');c.update(read,write,350,1400,now=lambda:1000.0,stream='https://dl.example.invalid/f.mkv')
        P={'tmdb_type':'tv','tmdb_id':'312359','season':'1','episode':'1','ios_continue':'1'}
        for kept,want in ((True,'http://127.0.0.1:1/cache'),(False,'https://dl.example.invalid/f.mkv')):
            played=[];m._opening_kept=lambda url,k=kept:k;m._cache_route=lambda url,resume=None:'http://127.0.0.1:1/cache'
            self.assertTrue(m.fast_stream(7,P,read,alive=lambda url:True,play=lambda h,e,url,pos,total:played.append(url),now=lambda:1500.0));self.assertEqual(played,[want])
if __name__=='__main__':unittest.main()
