"""Sports league logos: fetched on the phone, cached, never in Git; a league without one gets '' (a neutral ring)."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'migration/bundled-bootstrap/resources/lib'))
import sports_logos as sl  # noqa: E402

PNG = b'\x89PNG\r\n\x1a\n' + b'x' * 300


class Logos(unittest.TestCase):
    def test_every_espn_league_has_a_logo_address(self):
        import sports_espn
        for code, *_ in sports_espn.LEAGUES:
            self.assertTrue(sl.url_for(code).startswith('https://a.espncdn.com/'), code)
        for code in ('UFC', 'F1', 'PGA', 'LPGA'):
            self.assertTrue(sl.url_for(code), code)
        self.assertEqual(sl.url_for('BOX'), '')   # boxing has none: the page draws a neutral ring

    def test_fetched_once_then_kept(self):
        calls = []
        def get(url):
            calls.append(url)
            return PNG
        with tempfile.TemporaryDirectory() as profile:
            first = sl.fetch(profile, 'NFL', get)
            self.assertTrue(first.endswith('sports-logos/NFL.png') and Path(first).read_bytes() == PNG)
            self.assertEqual(sl.fetch(profile, 'NFL', get), first)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sl.cached(profile, 'NFL'), first)

    def test_nothing_bad_is_kept(self):
        with tempfile.TemporaryDirectory() as profile:
            self.assertEqual(sl.fetch(profile, 'BOX', lambda u: PNG), '')                  # no address
            self.assertEqual(sl.fetch(profile, 'NBA', lambda u: b'<html>blocked</html>'), '')   # not a PNG
            self.assertEqual(sl.fetch(profile, 'NBA', lambda u: PNG + b'x' * sl.MAX_BYTES), '')  # too big
            def down(url):
                raise OSError('offline')
            self.assertEqual(sl.fetch(profile, 'NBA', down), '')
            self.assertEqual(sl.fetch(profile, '../x', lambda u: PNG), '')                 # a code is never a path
            self.assertEqual(sl.paths(profile, ['MLB', 'BOX'], lambda u: PNG)['BOX'], '')


if __name__ == '__main__':
    unittest.main()
