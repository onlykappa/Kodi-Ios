"""A server that was too slow for the cache's opening a moment ago is played directly at once, not waited on for 2 s again (owner, build 639 log 9f7b4ab2: both
Umbrella opens logged route=direct wait_ms=2008 ready=False)."""
import sys,unittest
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'
sys.dont_write_bytecode=True;sys.path.insert(0,str(LIB))
import remote_media as rm

class Home:
    def __init__(self):self.p={}
    def getProperty(self,k):return self.p.get(k,'')
    def setProperty(self,k,v):self.p[k]=v

LINK='https://dl.example.invalid/secret/Episode.mkv|User-Agent=Kodi'
class Skip(unittest.TestCase):
    def test_a_slow_server_is_remembered_for_its_host_only_and_for_a_while(self):
        home=Home();t=[1000.0]
        self.assertFalse(rm.slow_recently(home,LINK,now=lambda:t[0]))
        rm.note_slow(home,LINK,now=lambda:t[0])
        self.assertTrue(rm.slow_recently(home,LINK,now=lambda:t[0]))
        self.assertTrue(rm.slow_recently(home,'https://dl.example.invalid/other.mkv',now=lambda:t[0]))
        self.assertFalse(rm.slow_recently(home,'https://fast.example.invalid/a.mkv',now=lambda:t[0]))
        t[0]+=rm.SLOW_SKIP+1;self.assertFalse(rm.slow_recently(home,LINK,now=lambda:t[0]))   # tried again later
        self.assertNotIn('secret',home.p[rm.SLOW_PROPERTY])
    def test_nothing_raises_without_a_window(self):
        rm.note_slow(None,LINK);self.assertFalse(rm.slow_recently(None,LINK))
    def test_for_kodi_asks_and_records(self):
        text=(LIB/'remote_media.py').read_text()
        self.assertIn('if slow_recently(home,source) and not _kept(source):',text);self.assertIn('note_slow(home,source)',text)
if __name__=='__main__':unittest.main()
