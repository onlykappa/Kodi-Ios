"""The anticipated-episodes bell (mockup board G): only for shows with an episode to come, two switches per show, alerts that
never download, and the skin pieces (bell textures, show-page button, Library > Favourites)."""
import datetime
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import anticipated as bell
import episode_watch as watch

TODAY = datetime.date(2026, 11, 14)


def stamp(day):
    return datetime.datetime.fromisoformat(day + 'T12:00:00').replace(tzinfo=datetime.timezone.utc).timestamp()


class Upcoming(unittest.TestCase):
    def test_next_episode_to_air_gives_the_bell(self):
        info = bell.upcoming({'next_episode_to_air': {'season_number': 5, 'episode_number': 1, 'air_date': '2026-11-21'}}, TODAY)
        self.assertEqual(info, {'season': 5, 'episode': 1, 'date': '2026-11-21'})
        self.assertEqual(bell.label(info), 'Next: Season 5 · Episode 1 · Sat 21 Nov')

    def test_an_announced_season_counts_as_its_first_episode(self):
        info = bell.upcoming({'seasons': [{'season_number': 1, 'air_date': '2020-01-01'}, {'season_number': 2, 'air_date': '2027-02-01'}]}, TODAY)
        self.assertEqual((info['season'], info['episode']), (2, 1))

    def test_no_bell_without_an_episode_to_come(self):
        for details in ({}, None, {'next_episode_to_air': None}, {'next_episode_to_air': {'season_number': 1, 'episode_number': 2, 'air_date': '2026-11-01'}},
                        {'next_episode_to_air': {'season_number': 1, 'episode_number': 2, 'air_date': None}},
                        {'seasons': [{'season_number': 0, 'air_date': '2027-01-01'}]}, {'status': 'Ended', 'seasons': [{'season_number': 1, 'air_date': '2010-01-01'}]}):
            self.assertIsNone(bell.upcoming(details, TODAY), details)

    def test_lookups_are_kept_for_six_hours(self):
        calls, now = [], [1000.0]
        lookup = bell.Lookup('k', clock=lambda: now[0], fetch=lambda t: calls.append(t) or {'next_episode_to_air': {
            'season_number': 2, 'episode_number': 3, 'air_date': '2999-01-01'}})
        lookup.upcoming('5')
        lookup.upcoming('5')
        self.assertEqual(calls, ['5'])
        now[0] += bell.TTL + 1
        lookup.upcoming('5')
        self.assertEqual(calls, ['5', '5'])


class Switches(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name
        self.info = {'season': 5, 'episode': 1, 'date': '2026-11-21'}

    def test_everything_starts_off_and_the_sheet_says_so(self):
        state = bell.switches(self.profile, '99')
        self.assertEqual(state, {'alert': False, 'auto': False, 'on': False})
        self.assertEqual([r['tag'] for r in bell.rows(state)], ['Off', 'Off'])

    def test_alert_alone_follows_the_show_without_downloading(self):
        state = bell.flip(self.profile, '99', 'Show', 'alert', self.info, now=stamp('2026-11-14'))
        self.assertEqual(state, {'alert': True, 'auto': False, 'on': True})
        saved = watch.load(self.profile)['shows']['99']
        self.assertEqual((saved['floor'], saved['auto'], saved['alert']), ([5, 1], False, True))

    def test_both_off_again_stops_following_the_show(self):
        bell.flip(self.profile, '99', 'Show', 'alert', self.info)
        state = bell.flip(self.profile, '99', 'Show', 'alert', self.info)
        self.assertFalse(state['on'])
        self.assertNotIn('99', watch.load(self.profile)['shows'])

    def test_a_show_followed_before_the_bell_keeps_downloading_and_has_no_alert(self):
        watch.register(self.profile, '99', 'Show', 1, 1, {'quality': '1080p'})
        self.assertEqual(bell.switches(self.profile, '99'), {'alert': False, 'auto': True, 'on': True})

    def test_turning_downloads_on_later_starts_from_then_not_from_old_episodes(self):
        bell.flip(self.profile, '99', 'Show', 'alert', self.info, now=100)
        bell.flip(self.profile, '99', 'Show', 'auto', self.info, preference={'quality': '4k'}, now=500)
        saved = watch.load(self.profile)['shows']['99']
        self.assertEqual((saved['since'], saved['auto'], saved['alert'], saved['preference']['quality']), (500, True, True, '4k'))

    def test_alert_text(self):
        title, text = bell.alert_text({'title': 'Black Clover'}, {'season_number': 5, 'episode_number': 1, 'name': 'The Return'})
        self.assertEqual(title, 'Black Clover')
        self.assertEqual(text, 'Season 5 · Episode 1 (The Return) is out now.')
        self.assertEqual(bell.alert_text({'title': 'X'}, {'season_number': 1, 'episode_number': 2, 'name': 'Episode 2'})[1],
                         'Season 1 · Episode 2 is out now.')


class Sweeping(unittest.TestCase):
    """The alert and the download are separate: alert-only never searches, and an alert is sent once."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.profile = self.tmp.name
        self.now = stamp('2026-11-14')
        self.alerts, self.downloads = [], []
        self.rows = [{'season_number': 5, 'episode_number': 1, 'name': 'One', 'air_date': '2026-11-21'}]

    def sweep(self, **kwargs):
        args = dict(get_show=lambda ident: {'id': int(ident), 'seasons': [{'season_number': 5, 'air_date': '2026-11-21'}]},
                    get_season=lambda *a: {'episodes': [dict(r) for r in self.rows]}, existing=lambda s, r: False,
                    download=lambda s, r: self.downloads.append(r['episode_number']) or True, clock=lambda: self.now,
                    notify=lambda s, r: self.alerts.append(r['episode_number']) or True)
        args.update(kwargs)
        return watch.sweep(self.profile, **args)

    def test_alert_only_tells_you_once_and_never_downloads(self):
        watch.set_option(self.profile, '99', 'Show', 'alert', True, floor=(5, 1), now=self.now)
        self.assertEqual(self.sweep(), 0)
        self.assertEqual((self.alerts, self.downloads), ([], []))            # not out yet
        self.now = stamp('2026-11-21')
        self.sweep()
        self.now += watch.COOLDOWN + 1
        self.sweep()
        self.assertEqual((self.alerts, self.downloads), ([1], []))
        self.assertTrue(watch.load(self.profile)['shows']['99']['episodes']['5:1']['alerted'])

    def test_alert_and_download_together_do_both_once(self):
        watch.set_option(self.profile, '99', 'Show', 'alert', True, floor=(5, 1), now=self.now)
        watch.set_option(self.profile, '99', 'Show', 'auto', True, floor=(5, 1), preference={'quality': '1080p'}, now=self.now)
        self.now = stamp('2026-11-21')
        self.assertEqual(self.sweep(), 1)
        self.now += watch.COOLDOWN + 1
        self.sweep()
        self.assertEqual((self.alerts, self.downloads), ([1], [1]))
        self.assertEqual(watch.load(self.profile)['shows']['99']['episodes']['5:1']['status'], 'queued')

    def test_downloads_switched_off_in_settings_still_alerts_but_does_not_search(self):
        watch.set_option(self.profile, '99', 'Show', 'alert', True, floor=(5, 1), now=self.now)
        watch.set_option(self.profile, '99', 'Show', 'auto', True, floor=(5, 1), preference={'quality': '1080p'}, now=self.now)
        self.now = stamp('2026-11-21')
        self.sweep(auto_allowed=False)
        self.assertEqual((self.alerts, self.downloads), ([1], []))

    def test_a_notification_that_fails_is_tried_again_next_time(self):
        watch.set_option(self.profile, '99', 'Show', 'alert', True, floor=(5, 1), now=self.now)
        self.now = stamp('2026-11-21')
        self.sweep(notify=lambda s, r: False)
        self.assertEqual(self.alerts, [])
        self.now += watch.COOLDOWN + 1
        self.sweep()
        self.assertEqual(self.alerts, [1])


class Skin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import portrait
        cls.p = portrait

    def test_bell_textures_exist(self):
        glyphs = self.p.header_glyphs()
        for name in self.p.BELL_TEXTURES:
            self.assertTrue(glyphs[name].startswith(b'\x89PNG'), name)

    def test_bell_button_is_hidden_unless_the_open_show_has_upcoming_episodes(self):
        xml = self.p.bell_button()
        self.assertIn('id="9004"', xml)
        self.assertIn('Container.Content(seasons)', xml)
        self.assertIn('KodiIOS.Bell.Tmdb', xml)
        self.assertIn('Container(50).ListItem.Property(tvshow.tmdb_id)', xml)
        self.assertIn('anticipated_bell', xml)
        # off = outline, on = filled: both with the black edge under them
        for name in self.p.BELL_TEXTURES:
            self.assertIn(name, xml)

    def test_the_hit_area_is_the_navigation_buttons(self):
        self.assertIn('<width>%d</width><height>%d</height><texturefocus />' % (self.p.NAV_TOUCH, self.p.NAV_TOUCH), self.p.bell_button())

    def test_library_has_a_favourites_row(self):
        names = [n for n, icon, action in self.p.LIBRARY]
        self.assertEqual(names, ['Movies', 'TV Shows', 'Favourites'])

    def test_season_sheet_has_only_two_choices(self):
        source = (ROOT / 'migration/bundled-bootstrap/download.py').read_text()
        self.assertNotIn('Follow new episodes', source)
        self.assertIn('Full season', source)
        self.assertIn('Choose episodes', source)

    def test_bell_page_is_routable(self):
        source = (ROOT / 'migration/bundled-bootstrap/default.py').read_text()
        for page in ('anticipated_bell', 'favourites_import_page'):
            self.assertIn("'%s'" % page, source)


if __name__ == '__main__':
    unittest.main()
