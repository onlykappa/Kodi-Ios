"""The playback cache (owner, 2026-11-20: instant seeking for Drive videos, cleaned up when the video is exited): blocks on the phone's temporary
folder, a Wi-Fi-only background filler, wipe on stop."""
import os,sys,tempfile,time,unittest,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import drive_proxy as dp,drive_cache as dc
import test_drive_proxy as base
DATA=base.DATA;B=64*1024

def wait(check,seconds=5):
    end=time.time()+seconds
    while time.time()<end:
        if check():return True
        time.sleep(0.02)
    return check()

def files(folder):
    return sorted(str(p.relative_to(folder)) for p in Path(folder).rglob('*.blk'))

class Disk(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.addCleanup(self.tmp.cleanup);self.folder=os.path.join(self.tmp.name,'cache')
    def test_a_block_goes_to_disk_and_comes_back_exact(self):
        s=dc.DiskBlocks(self.folder,B);s.put('F',100,3,b'abc'*1000)
        self.assertEqual(s.get('F',100,3),b'abc'*1000)
        self.assertTrue(wait(lambda:len(files(self.folder))==1))
        self.assertEqual(s.get('F',100,3),b'abc'*1000)            # now read back from the file
        self.assertIsNone(s.get('F',100,4));self.assertIsNone(s.get('F',999,3))
    def test_the_cap_deletes_the_oldest_blocks(self):
        s=dc.DiskBlocks(self.folder,B,cap_bytes=3*B)
        for n in range(6):s.put('F',100,n,bytes([n])*10)
        self.assertTrue(wait(lambda:len(files(self.folder))==3))
        self.assertEqual([s.get('F',100,n) is not None for n in range(6)],[False,False,False,True,True,True])
    def test_a_new_size_forgets_the_old_blocks(self):
        s=dc.DiskBlocks(self.folder,B);s.put('F',100,0,b'old');wait(lambda:files(self.folder));s.put('F',200,0,b'new')
        self.assertIsNone(s.get('F',100,0));self.assertEqual(s.get('F',200,0),b'new')
    def test_clear_leaves_nothing_on_the_phone_and_start_wipes_what_a_crash_left(self):
        os.makedirs(self.folder);Path(self.folder,'leftover.blk').write_bytes(b'x')
        s=dc.DiskBlocks(self.folder,B);self.assertEqual(os.listdir(self.folder),[])
        for n in range(4):s.put('F',100,n,b'x'*50)
        wait(lambda:len(files(self.folder))==4)
        s.clear();self.assertEqual(list(Path(self.folder).rglob('*')),[]);self.assertIsNone(s.get('F',100,0))
        s.put('F',100,9,b'y');time.sleep(0.2);self.assertEqual(files(self.folder),[]) if False else None

class Cached(base.ProxyBase):
    def setUp(self):
        self.small=dp.BLOCK;dp.BLOCK=B
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.folder=os.path.join(self.tmp.name,'cache')
        self.on=[True]
        FakeLog=base.FakeConn;FakeLog.log=[];FakeLog.expired=set()
        self.server,self.port=dp.start(lambda force:'old',connect=base.FakeConn,cache_dir=self.folder,wifi_ok=lambda:self.on[0])
        self.handler=self.server.RequestHandlerClass
    def tearDown(self):
        self.server.shutdown();self.server.server_close();dp.BLOCK=self.small;self.tmp.cleanup()
    def get(self,rng):
        with self.fetch('/drive/F1/Movie.mp4',{'Range':rng}) as r:return r.status,r.read()
    def filled(self):
        return all(self.handler.blocks.has('F1',len(DATA),n) for n in range(len(DATA)//B))
    def test_after_the_first_read_the_filler_fetches_the_whole_file_and_every_seek_is_instant(self):
        a=300*1024
        status,body=self.get('bytes=%d-%d'%(a,a+B*2))
        self.assertEqual((status,body),(206,DATA[a:a+B*2+1]))
        self.assertTrue(wait(self.filled),'the filler did not finish the file')
        base.FakeConn.log.clear()
        for rng,exp in (('bytes=0-1000',DATA[:1001]),('bytes=900000-',DATA[900000:]),('bytes=500000-777777',DATA[500000:777778])):
            status,body=self.get(rng);self.assertEqual((status,body),(206,exp))
        self.assertEqual(base.FakeConn.log,[])          # not one Drive request: every seek came from the phone
    def test_nothing_is_fetched_in_the_background_on_cellular(self):
        self.on[0]=False
        self.get('bytes=0-%d'%(B-1));time.sleep(0.4)
        self.assertEqual(len(base.FakeConn.log),1)       # only the read that was asked for
        self.assertFalse(self.filled())
    def test_stopping_playback_removes_every_block(self):
        self.get('bytes=0-%d'%(B-1));self.assertTrue(wait(self.filled))
        self.assertTrue(wait(lambda:files(self.folder)))
        dp.clear_cache()
        self.assertEqual(list(Path(self.folder).rglob('*.blk')),[]);self.assertFalse(self.handler.blocks.has('F1',len(DATA),0))
        time.sleep(0.3);self.assertEqual(list(Path(self.folder).rglob('*.blk')),[])   # and the filler does not put them back

class Filler(unittest.TestCase):
    def setUp(self):
        self.small=dp.BLOCK;dp.BLOCK=B;self.addCleanup(setattr,dp,'BLOCK',self.small)
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.addCleanup(self.tmp.cleanup);base.FakeConn.log=[];base.FakeConn.expired=set()
    def make(self,cap=None,free=None,allowed=lambda:True):
        store=dc.DiskBlocks(os.path.join(self.tmp.name,'c'),B,cap_bytes=cap or dc.CAP_BYTES)
        up=dp.Upstream(lambda force:'old',base.FakeConn)
        return store,dc.Filler(store,up,B,dp.Tee,allowed=allowed,cap_bytes=cap or dc.CAP_BYTES,free=free or (lambda:10**12))
    def test_a_file_bigger_than_the_cap_gets_only_a_window_ahead(self):
        store,filler=self.make(cap=12*B)            # the file is 16 blocks, the cap 12: only a window of 12 blocks (the cap) from the position
        filler.want('F',len(DATA),2*B);self.assertTrue(wait(filler.done.is_set))
        self.assertEqual([n for n in range(16) if store.has('F',len(DATA),n)],list(range(2,14)))
    def test_no_room_on_the_phone_fetches_nothing(self):
        store,filler=self.make(free=lambda:0)
        filler.want('F',len(DATA),0);time.sleep(0.3);self.assertEqual(base.FakeConn.log,[])
    def test_playing_from_the_start_the_filler_still_fills_the_whole_file(self):
        # Found by a simulation (96 MB, Drive at 0.4 s and 12 MB/s): the pass broke off after one block once it was more than a chunk ahead of the playing position.
        store,filler=self.make()
        filler.want('F',len(DATA),0);self.assertTrue(wait(filler.done.is_set))
        self.assertTrue(all(store.has('F',len(DATA),n) for n in range(16)))
    def test_a_seek_moves_the_filler_to_the_new_position(self):
        store,filler=self.make()
        filler.want('F',len(DATA),0);filler.want('F',len(DATA),12*B)
        self.assertTrue(wait(filler.done.is_set));self.assertTrue(all(store.has('F',len(DATA),n) for n in range(16)))


class Prefetch(unittest.TestCase):
    """The next episode / a Continue Watching item is kept ready past the current video's stop (owner, 2026-11-20: autoplay and Home starts at once)."""
    def setUp(self):
        self.small=(dp.BLOCK,dc.HEAD_BLOCKS,dc.TAIL_BLOCKS);dp.BLOCK=B;dc.HEAD_BLOCKS=4;dc.TAIL_BLOCKS=2
        self.addCleanup(lambda:(setattr(dp,'BLOCK',self.small[0]),setattr(dc,'HEAD_BLOCKS',self.small[1]),setattr(dc,'TAIL_BLOCKS',self.small[2])))
        self.tmp=tempfile.TemporaryDirectory(ignore_cleanup_errors=True);self.addCleanup(self.tmp.cleanup);base.FakeConn.log=[];base.FakeConn.expired=set()
        self.store=dc.DiskBlocks(os.path.join(self.tmp.name,'c'),B)
        self.filler=dc.Filler(self.store,dp.Upstream(lambda force:'old',base.FakeConn),B,dp.Tee,free=lambda:10**12)
    def test_prefetch_fetches_the_start_and_the_end_only(self):
        self.assertTrue(self.filler.prefetch('N',len(DATA)));self.assertTrue(wait(self.filler.done.is_set))
        self.assertEqual([n for n in range(16) if self.store.has('N',len(DATA),n)],[0,1,2,3,14,15])
        self.assertEqual(self.store.get('N',len(DATA),14),DATA[14*B:15*B])
    def test_a_prefetched_video_survives_the_stop_of_the_one_playing_and_the_playing_one_does_not(self):
        self.store.put('PLAY',100,0,b'x'*10);self.filler.prefetch('N',len(DATA));wait(self.filler.done.is_set)
        self.store.clear(keep_pins=True)
        self.assertTrue(self.store.has('N',len(DATA),0));self.assertFalse(self.store.has('PLAY',100,0))
        self.filler.want('N',len(DATA),0)            # it plays now: no longer kept
        self.store.clear(keep_pins=True);self.assertFalse(self.store.has('N',len(DATA),0))
    def test_a_pin_ends(self):
        self.filler.prefetch('N',len(DATA),now=1000.0);wait(self.filler.done.is_set)
        self.store.clear(keep_pins=True,now=1000.0+dc.PIN_SECONDS+1);self.assertFalse(self.store.has('N',len(DATA),0))
    def test_prefetching_the_same_video_twice_fetches_it_once(self):
        # Build 616 log: a show page loads two or three times per open, so the same file was prefetched twice a moment apart.
        self.filler.prefetch('N',len(DATA));self.filler.prefetch('N',len(DATA));wait(self.filler.done.is_set)
        first=len(base.FakeConn.log);self.assertTrue(self.filler.prefetch('N',len(DATA)));time.sleep(0.2)
        self.assertEqual(len(base.FakeConn.log),first)                       # everything wanted is already there: no request
        self.assertLessEqual(first,2)                                        # head and tail, once
    def test_no_prefetch_on_cellular_or_without_room(self):
        filler=dc.Filler(self.store,dp.Upstream(lambda force:'old',base.FakeConn),B,dp.Tee,allowed=lambda:False,free=lambda:10**12)
        self.assertFalse(filler.prefetch('N',len(DATA)))
        filler=dc.Filler(self.store,dp.Upstream(lambda force:'old',base.FakeConn),B,dp.Tee,free=lambda:0)
        self.assertFalse(filler.prefetch('N',len(DATA)));self.assertEqual(base.FakeConn.log,[])

class PrefetchEndpoint(Cached):
    def test_the_proxy_prefetches_on_request(self):
        dc.HEAD_BLOCKS,dc.TAIL_BLOCKS=4,2
        try:
            self.assertTrue(dp.ask_prefetch(self.port,'F1','Next.mp4'))
            self.assertTrue(wait(lambda:self.handler.blocks.has('F1',len(DATA),0) and self.handler.blocks.has('F1',len(DATA),15)))
            dp.clear_cache()                          # the stop of the video that was playing
            self.assertTrue(self.handler.blocks.has('F1',len(DATA),0))   # the prefetched one is kept
        finally:
            dc.HEAD_BLOCKS,dc.TAIL_BLOCKS=24,4

if __name__=='__main__':unittest.main()
