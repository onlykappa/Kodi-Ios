"""One log line per touch gesture on the dialog pages (owner, build 622: flicks do nothing on the Sports pages and Favourites): tells a drag that stops
at once from a flick Kodi glides on, with no native change."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BOOT=ROOT/'migration/bundled-bootstrap'
sys.dont_write_bytecode=True;sys.path.insert(0,str(BOOT/'resources/lib'))
import gesture_note as g

class Act:
    def __init__(self,i,y=0.0):self.i,self.y=i,y
    def getId(self):return self.i
    def getAmount2(self):return self.y

def run(events):
    now=[0.0];logs=[];t=g.Tracker(logs.append,lambda:now[0])
    for dt,ident,y in events:
        now[0]+=dt;t.feed(Act(ident,y))
    return logs

class Tracking(unittest.TestCase):
    def test_a_drag_that_stops_at_once(self):
        ev=[(0,g.BEGIN,0)]+[(0.02,g.PAN,100+i*20) for i in range(12)]+[(0.01,g.END,0)]
        logs=run(ev);self.assertEqual(len(logs),1)
        self.assertIn('12 pans',logs[0]);self.assertIn('stopped at once',logs[0]);self.assertIn('end after',logs[0])
    def test_a_flick_that_glides_on(self):
        ev=[(0,g.BEGIN,0)]+[(0.02,g.PAN,100+i*30) for i in range(60)]+[(0.0,g.END,0)]
        logs=run(ev);self.assertIn('glided on',logs[0]);self.assertIn('60 pans',logs[0])
    def test_swipe_actions_are_noted_and_a_bad_action_never_raises(self):
        logs=run([(0,531,0)]);self.assertIn('swipe action 531',logs[0])
        t=g.Tracker(lambda m:1/0);t.feed(object());t.feed(Act(g.END))
    def test_the_log_is_capped(self):
        now=[0.0];logs=[];t=g.Tracker(logs.append,lambda:now[0])
        for _ in range(100):
            t.feed(Act(g.BEGIN));now[0]+=.02;t.feed(Act(g.PAN,5));t.feed(Act(g.END))
        self.assertEqual(len(logs),g.MAX)
    def test_every_dialog_page_feeds_it(self):
        for name in ('sports','sports_live','sports_upcoming','sports_leagues','sports_game','favourites_page','notifications'):
            text=(BOOT/(name+'.py')).read_text()
            self.assertIn('self._gestures.feed(action)',text,name)

if __name__=='__main__':unittest.main()
