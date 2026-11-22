"""Where a page's opening time goes (owner, 2026-11-22, log 71e31b26) and what Sports shows first."""
import sys,types,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import page_clock

class Clock(unittest.TestCase):
    def test_one_line_with_the_total_and_each_step(self):
        t=[0.0];lines=[];c=page_clock.Clock('upcoming',lines.append,lambda:t[0])
        t[0]=.25;c.lap('provider');t[0]=1.0;c.lap('rows')
        c.done();c.done()   # logged once
        self.assertEqual(lines,['page: upcoming: first frame in 1000 ms (provider 250, rows 750)'])
    def test_no_steps_no_brackets(self):
        lines=[];c=page_clock.Clock('x',lines.append,lambda:5.0);c.done('opened empty')
        self.assertEqual(lines,['page: x: opened empty in 0 ms'])

class Wiring(unittest.TestCase):
    BOOT=ROOT/'migration/bundled-bootstrap'
    def test_the_pages_log_their_first_frame(self):
        for name in ('sports_live.py','sports_upcoming.py','sports_leagues.py'):
            src=(self.BOOT/name).read_text();self.assertIn('page_clock.Clock(',src,name);self.assertIn('.done(',src,name)
    def test_the_background_search_waits_for_a_quiet_finger(self):
        src=(self.BOOT/'service.py').read_text()
        self.assertIn("System.IdleTime(5)",src)
    def test_live_now_draws_before_it_waits_for_any_logo(self):
        src=(self.BOOT/'sports_live.py').read_text()
        self.assertIn('first_frame(page, sports_provider',src);self.assertIn('get=_offline',src)
        self.assertLess(src.index('get=_offline'),src.index('props = with_crests(props, profile)'))
if __name__=='__main__':unittest.main()
