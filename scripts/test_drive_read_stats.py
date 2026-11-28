"""ISSUE-491: one summary line a minute about the reads to Drive (second tries and why, first-byte times)."""
import sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import drive_proxy as dp


class Stats(unittest.TestCase):
    def test_nothing_before_a_minute_then_one_line_and_a_fresh_count(self):
        s = dp.ReadStats()
        for n, ms in enumerate((300, 350, 400, 900, 2400)):
            s.add(206, 1 if n else 2, ms, 100.0 + n)
        s.retried('ConnectionResetError', 101.0)
        s.retried('RemoteDisconnected', 102.0)
        s.retried('ConnectionResetError', 103.0)
        self.assertIsNone(s.line(150.0))
        line = s.line(161.0)
        self.assertIn('5 reads, 3 second tries (ConnectionResetError 2, RemoteDisconnected 1)', line)
        self.assertIn('median 400 ms', line); self.assertIn('slowest 2400 ms', line); self.assertIn('statuses 206 5', line)
        self.assertIsNone(s.line(162.0))   # counts start again
    def test_no_reads_no_line(self):
        self.assertIsNone(dp.ReadStats().line(1000.0))
    def test_the_proxy_records_every_read_and_every_second_try(self):
        text = (ROOT / 'migration/bundled-bootstrap/resources/lib/drive_proxy.py').read_text()
        for needle in ("READS.retried(type(error).__name__", "READS.add(resp.status, attempt + 1, headers_ms", "summary = READS.line("):
            self.assertIn(needle, text)


if __name__ == '__main__':
    unittest.main()
