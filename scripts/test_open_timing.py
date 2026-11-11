"""Roadmap 1C.1: one 'open timing' line per video, tap to playing picture."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import open_timing as ot

class Home(dict):
    def setProperty(self,k,v):self[k]=v
    def getProperty(self,k):return self.get(k,'')
    def clearProperty(self,k):self.pop(k,None)

class OpenTiming(unittest.TestCase):
    def test_logs_once_when_the_picture_plays(self):
        home,lines=Home(),[]
        ot.mark(home,'library',now=100.0)
        self.assertFalse(ot.check(home,lambda:False,lines.append,now=101.0))
        self.assertTrue(ot.check(home,lambda:True,lines.append,now=105.8))
        self.assertEqual(lines,['Kodi iOS open timing: 5.8 s via library'])
        self.assertFalse(ot.check(home,lambda:True,lines.append,now=106.0))
    def test_a_stale_mark_is_dropped(self):
        home,lines=Home(),[]
        ot.mark(home,'drive copy',now=0.0)
        self.assertTrue(ot.check(home,lambda:False,lines.append,now=121.0))
        self.assertIn('no picture after 121 s via drive copy',lines[0])

if __name__=='__main__':unittest.main()
