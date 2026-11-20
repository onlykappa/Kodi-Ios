"""A busy dialog nobody lowers is closed after a few seconds; one belonging to a video that is opening is never touched."""
import sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import busy_watchdog as bw

class Dog(unittest.TestCase):
    def make(self,up=('busydialognocancel',),video=False):
        self.t=[0.0];self.closed=[];self.logs=[];self.up=set(up);self.video=[video]
        return bw.Watchdog(lambda n:n in self.up,lambda:self.video[0],self.closed.append,self.logs.append,clock=lambda:self.t[0])
    def at(self,dog,t):self.t[0]=t;return dog.tick()
    def test_a_dialog_up_for_longer_than_the_grace_is_closed_once(self):
        dog=self.make()
        self.assertEqual(self.at(dog,0.0),[]);self.assertEqual(self.at(dog,bw.GRACE-0.1),[])
        self.assertEqual(self.at(dog,bw.GRACE),['busydialognocancel']);self.assertEqual(self.closed,['busydialognocancel'])
        self.up.clear();self.assertEqual(self.at(dog,bw.GRACE+1),[])
    def test_a_short_flash_is_left_alone_and_the_clock_restarts(self):
        dog=self.make();self.at(dog,0.0);self.up.clear();self.at(dog,2.0);self.up.add('busydialognocancel')
        self.at(dog,3.0);self.assertEqual(self.at(dog,3.0+bw.GRACE-0.5),[])   # up again since 3.0, not since 0.0
    def test_nothing_is_closed_while_a_video_is_opening_or_playing(self):
        dog=self.make(video=True);self.at(dog,0.0);self.assertEqual(self.at(dog,60.0),[]);self.assertEqual(self.closed,[])
        self.video[0]=False;self.assertEqual(self.at(dog,61.0),[])           # the clock starts when the video is over
        self.assertEqual(self.at(dog,61.0+bw.GRACE),['busydialognocancel'])
    def test_both_dialog_names_are_watched_and_errors_are_not_fatal(self):
        dog=self.make(up=('busydialog','busydialognocancel'));self.at(dog,0.0)
        self.assertEqual(sorted(self.at(dog,10.0)),['busydialog','busydialognocancel'])
        bad=bw.Watchdog(lambda n:1/0,lambda:1/0,self.closed.append);self.assertEqual(bad.tick(),[])
if __name__=='__main__':unittest.main()
