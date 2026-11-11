import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import interpreter_probe as p

class Probe(unittest.TestCase):
    def test_lateness(self):
        self.assertEqual(p.lateness([]),(0.0,0.0))
        self.assertEqual(p.lateness(list(range(1,101))),(51,95))
    def test_run_reports_late_wakeups(self):
        t=[0.0];reports=[]
        def sleep(s):t[0]+=s+0.005   # always 5 ms late
        p.run(lambda:len(reports)>=1,lambda m,q,n:reports.append((m,q,n)),step=0.02,every=1.0,clock=lambda:t[0],sleep=sleep)
        m,q,n=reports[0];self.assertAlmostEqual(m,5.0,places=0);self.assertGreater(n,30)

if __name__=='__main__':unittest.main()
