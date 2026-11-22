"""A debrid link is relayed from one streaming connection after the kept opening (owner, build 653 log d63069c3: block-by-block fetching through the cache was refused
almost every time and Kodi's reads waited up to 28 s; the opening from the phone's disk is what made Continue start in 1.2 s, and it stays)."""
import io,sys,unittest,urllib.request
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import remote_media as rm

DATA=bytes((i*7+i//251)%256 for i in range(30*1024*1024))   # 30 MiB: 8 blocks of 4 MiB
class Reply(io.BytesIO):
    def __init__(self,a,b):
        super().__init__(DATA[a:b+1]);self.status=206
        self.headers={'Content-Range':'bytes %d-%d/%d'%(a,min(b,len(DATA)-1),len(DATA))}
    def getcode(self):return self.status
calls=[]
def opener(request,timeout):
    a,b=map(int,request.get_header('Range')[6:].split('-'));calls.append((a,b));return Reply(a,min(b,len(DATA)-1))

def get(stream,first,last):
    request=urllib.request.Request(stream.media_url,headers={'Range':'bytes=%d-%d'%(first,last)})
    with urllib.request.urlopen(request,timeout=20) as answer:return answer.read()

class Relay(unittest.TestCase):
    def setUp(self):
        calls.clear()
        self.s=rm.Foreground('https://8sio2e.debrid.it/dl/x/Episode.mkv|User-Agent=Kodi',open_url=opener);self.addCleanup(self.s.close)
        self.s.blocks.sizes['media']=len(DATA);self.s.answered_size=len(DATA)
        for i in (0,1):self.s.blocks.data[('media',i)]=DATA[i*rm.BLOCK:(i+1)*rm.BLOCK]   # the kept opening
    def test_the_kept_opening_is_served_from_memory_without_asking_the_server(self):
        self.assertTrue(self.s.serial)
        self.assertEqual(get(self.s,100,3*1024*1024),DATA[100:3*1024*1024+1]);self.assertEqual(calls,[])
    def test_what_is_not_kept_comes_from_one_streaming_request_not_block_requests(self):
        first=3*rm.BLOCK+12345;last=len(DATA)-1
        got=get(self.s,first,last)
        self.assertEqual(len(got),last-first+1);self.assertEqual(got,DATA[first:last+1])
        self.assertEqual(calls,[(first,last)])   # one request from where the reader asked, to the end: as Kodi's own player would
    def test_a_read_that_runs_into_the_kept_opening_takes_it_from_memory(self):
        calls.clear();s=self.s
        s.blocks.data[('media',3)]=DATA[3*rm.BLOCK:4*rm.BLOCK]   # a kept block in the middle
        first=2*rm.BLOCK+5;last=5*rm.BLOCK-1
        got=get(s,first,last);self.assertEqual(got,DATA[first:last+1])
        self.assertEqual(calls[0][0],first)   # block 2 is relayed (not kept), block 3 comes from memory, block 4 is relayed again
        self.assertTrue(all(a>=first for a,b in calls))
    def test_only_a_serial_source_relays(self):
        s=rm.Foreground('https://fast.other.invalid/a.mkv',open_url=opener);self.addCleanup(s.close)
        self.assertEqual(s.relay_tail('media',0,10,lambda part:None),0)
    def test_an_upstream_that_does_not_answer_falls_back_to_the_block_path(self):
        s=self.s;real=s.open_url
        def refuse(request,timeout):raise OSError('no')
        s.open_url=refuse
        self.assertEqual(s.relay_tail('media',3*rm.BLOCK,len(DATA)-1,lambda part:None),0)

if __name__=='__main__':unittest.main()
