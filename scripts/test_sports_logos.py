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

    def test_an_untranslated_profile_path_writes_nothing(self):
        # The first version of the page code fetched logos during the Leagues test and wrote PNGs into the repo.
        calls = []
        self.assertEqual(sl.fetch('special://profile/', 'NFL', lambda u: calls.append(u) or PNG), '')
        self.assertEqual(calls, [])

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


class DarkLogos(unittest.TestCase):
    """Live Now's league headers sit on black (owner, 2026-11-21): ESPN's 500-dark logos, because the NHL's own is black."""
    def test_the_dark_address_is_espns_500_dark_folder(self):
        self.assertEqual(sl.dark_url('NHL'), 'https://a.espncdn.com/i/teamlogos/leagues/500-dark/nhl.png')
        self.assertEqual(sl.dark_url('LIGA'), 'https://a.espncdn.com/i/leaguelogos/soccer/500-dark/15.png')
        self.assertEqual(sl.dark_url('NCAAF'), '')    # college football has no such logo: the page draws a football glyph
        self.assertEqual(sl.dark_url('BOX'), '')

    def test_fetched_once_kept_and_nothing_bad_is_saved(self):
        with tempfile.TemporaryDirectory() as profile:
            calls = []
            got = sl.fetch_dark(profile, 'NBA', lambda u: calls.append(u) or PNG)
            self.assertTrue(got.endswith('NBA-dark.png'))
            self.assertEqual(sl.fetch_dark(profile, 'NBA', lambda u: calls.append(u) or PNG), got)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sl.fetch_dark(profile, 'NHL', lambda u: b'<html>blocked</html>'), '')
            self.assertEqual(sl.fetch_dark('special://profile/', 'NFL', lambda u: PNG), '')


class Crests(unittest.TestCase):
    PNG = b'\x89PNG' + b'0' * 200
    URL = 'https://a.espncdn.com/i/teamlogos/nfl/500/ind.png'

    def test_a_crest_is_downloaded_once_and_kept(self):
        import tempfile
        calls = []
        def get(url):
            calls.append(url)
            return self.PNG
        with tempfile.TemporaryDirectory() as profile:
            first = sl.crest(profile, self.URL, get)
            self.assertTrue(first.endswith('.png') and Path(first).is_file())
            self.assertEqual(sl.crest(profile, self.URL, get), first)
            self.assertEqual(len(calls), 1)

    def test_only_espns_image_host_and_real_pngs_are_kept(self):
        import tempfile
        with tempfile.TemporaryDirectory() as profile:
            self.assertEqual(sl.crest(profile, 'https://example.com/x.png', lambda u: self.PNG), '')
            self.assertEqual(sl.crest(profile, self.URL, lambda u: b'not a png' * 30), '')
            self.assertEqual(sl.crest(profile, self.URL, lambda u: self.PNG + b'0' * 500000), '')   # too big
            self.assertEqual(sl.crest(profile, '', lambda u: self.PNG), '')
            def down(u):
                raise OSError('offline')
            self.assertEqual(sl.crest(profile, self.URL, down), '')
        self.assertEqual(sl.crest('special://profile/', self.URL, lambda u: self.PNG), '')   # never writes beside the code

    def test_several_crests_at_once(self):
        import tempfile
        other = 'https://a.espncdn.com/i/teamlogos/nfl/500/hou.png'
        with tempfile.TemporaryDirectory() as profile:
            found = sl.crests(profile, [self.URL, other, self.URL, '', 'https://example.com/y.png'], lambda u: self.PNG)
            self.assertEqual(sorted(found), sorted([self.URL, other]))


if __name__ == '__main__':
    unittest.main()
