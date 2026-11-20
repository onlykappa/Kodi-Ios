"""The scroll probe: frame rates are kept only while the screen is touched, per window, and summarised in one line each."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import scroll_probe as sp

def make(fps_values,touched=lambda:True,window=lambda:(13005,'Home'),busy=lambda:False):
    logs=[];values=iter(fps_values)
    return sp.Probe(lambda:next(values),touched,window,logs.append,busy),logs

class Tests(unittest.TestCase):
    def test_the_line_names_the_typical_and_slowest_tenth(self):
        probe,logs=make([60]*18+[20,20])
        for _ in range(20):probe.tick()
        probe.flush();self.assertEqual(logs,["Kodi iOS scroll: window 13005 'Home': 60 fps typical, 20 fps slowest tenth, 20 samples while touched"])
    def test_too_few_samples_say_nothing(self):
        probe,logs=make([60]*5)
        for _ in range(5):probe.tick()
        probe.flush();self.assertEqual(logs,[])
    def test_nothing_is_sampled_while_idle_or_during_video(self):
        probe,logs=make([30]*20,touched=lambda:False)
        for _ in range(20):probe.tick()
        self.assertEqual(probe.samples,{})
        probe,_=make([30]*20,busy=lambda:True)
        for _ in range(20):probe.tick()
        self.assertEqual(probe.samples,{})
    def test_a_window_change_reports_the_window_left(self):
        state={'w':(13002,'Upcoming')};logs=[];values=iter([40]*10+[60]*10)
        probe=sp.Probe(lambda:next(values),lambda:True,lambda:state['w'],logs.append)
        for _ in range(10):probe.tick()
        state['w']=(10000,'Home')
        for _ in range(10):probe.tick()
        self.assertEqual(len(logs),1);self.assertIn("window 13002 'Upcoming': 40 fps",logs[0])
        probe.flush();self.assertIn("window 10000 'Home': 60 fps",logs[1])
    def test_a_broken_reader_never_raises(self):
        logs=[];probe=sp.Probe(lambda:'n/a',lambda:True,lambda:(1,''),logs.append);probe.tick();self.assertEqual(probe.samples,{})
    def test_watch_samples_until_abort_and_flushes_at_the_end(self):
        probe,logs=make([50]*12);calls=[0]
        def wait(step):
            calls[0]+=1;return calls[0]>12
        sp.watch(probe,wait,flush_every=1e9,step=0.0);self.assertEqual(len(logs),1)
    def test_the_service_starts_it(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('scroll_probe.watch',text);self.assertIn("System.IdleTime(1)",text)

if __name__=='__main__':unittest.main()
