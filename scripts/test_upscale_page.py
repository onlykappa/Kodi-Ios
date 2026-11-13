"""Settings › AI Upscale (upscale_page.py, ai-upscale-settings-mockups.html boards A-C, DEC-042)."""
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
LIB = Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0, str(LIB))
import picture  # noqa: E402
import upscale_page as up  # noqa: E402


def job(i, w, h, hdr=False):
    return {'status': 'done', 'prepared_id': 'id%d' % i, 'source': {'id': 'id%d' % i, 'name': 'file%d.mp4' % i},
            'probe': {'width': w, 'height': h, 'hdr': hdr, 'duration': 1400}}


PREP = {'jobs': {'a': job(1, 1920, 1080), 'b': job(2, 1920, 1080), 'c': job(3, 1280, 720), 'd': job(4, 3840, 2160)}}
MEDIA = {'id1': {'tmdb': '31910', 'type': 'tv', 'show': 'Naruto Shippūden'}, 'id2': {'tmdb': '31910', 'type': 'tv', 'show': 'Naruto Shippūden'},
         'id3': {'tmdb': '60625', 'type': 'tv', 'show': 'Rick and Morty'}, 'id4': {'tmdb': '157336', 'type': 'movie', 'show': 'Interstellar'}}
media_for = lambda j: MEDIA[j['prepared_id']]


class Page(unittest.TestCase):
    def test_settings_row_summary(self):
        s = picture.load('/none')
        self.assertEqual(up.summary(s), 'Off')
        s['downloads']['prepare'] = True
        self.assertEqual(up.summary(s), 'On · 4K')
        s = picture.load('/none')
        picture.apply(s, 'show', MEDIA['id3'], upscale='1440p')
        self.assertEqual(up.summary(s), 'On · 1440p')

    def test_status_card_states(self):
        self.assertEqual(up.status_row({'upscales': False, 'model': -1})['label'], 'Not available on this iPhone')
        self.assertEqual(up.status_row({'upscales': True, 'model': 2})['label'], 'Ready on this iPhone')
        need = up.status_row({'upscales': True, 'model': 0})
        self.assertEqual((need['label'], need['action']), ("Apple's AI model is needed", 'model'))

    def test_shows_and_movies_with_what_they_can_become(self):
        data = {'copies': {'id1': {'status': 'ready', 'label': '4K UHD', 'size': 2e9}, 'id2': {'status': 'running', 'label': '4K UHD',
                           'progress': 42, 'eta': 'about 18 min', 'name': 'Naruto S01E02.mp4'}}}
        groups = up.library(PREP, media_for, data)
        self.assertEqual([g['title'] for g in groups], ['Naruto Shippūden', 'Rick and Morty', 'Interstellar'])
        s = picture.load('/none')
        picture.apply(s, 'show', MEDIA['id1'], upscale='4K UHD')
        rows = up.rows(s, data, groups, {'upscales': True, 'model': 2})
        by = {r['label']: r for r in rows}
        self.assertEqual((by['Naruto Shippūden']['sub'], by['Naruto Shippūden']['value']), ('2 ep · 1080p → 4K · 1 ready', '4K'))
        self.assertEqual((by['Rick and Morty']['sub'], by['Rick and Morty']['value']), ('1 ep · 720p · can go 4K', 'Off'))
        self.assertNotIn('Interstellar', by)                                  # 4K is kept as it is
        self.assertIn('1 video already in 4K or HDR', by)
        making = [r for r in rows if r.get('sub', '').startswith('To 4K UHD')]
        self.assertEqual(making[0]['sub'], 'To 4K UHD · 42 % · about 18 min')
        self.assertIn('Upscaled copies use 2.0 GB on Google Drive.', by)
        self.assertEqual(rows[-1]['action'], 'test')

    def test_a_show_offers_only_sizes_above_its_videos(self):
        groups = {g['title']: g for g in up.library(PREP, media_for, {})}
        self.assertEqual(up.show_sizes(groups['Naruto Shippūden']), ['Off', '1440p', '4K UHD'])
        self.assertEqual(up.show_sizes(groups['Rick and Morty']), ['Off', '1080p', '1440p', '4K UHD'])
        s = up.set_show(picture.load('/none'), groups['Rick and Morty'], '1080p')
        self.assertEqual(s['shows']['tv:60625']['upscale'], '1080p')

    def test_one_show_page(self):
        # V3, board C: the show's size, its episodes with their state, make the rest, remove the copies.
        import upscale_queue as uq
        data = {'copies': {'id1': {'status': 'ready', 'label': '4K UHD', 'size': 640e6}, 'id2': {'status': 'running', 'label': '4K UHD',
                                                                                                    'progress': 42, 'eta': 'about 18 min'}}}
        media = dict(MEDIA, id1=dict(MEDIA['id1'], season=1, episode=1), id2=dict(MEDIA['id2'], season=1, episode=2))
        groups = up.library(PREP, lambda j: media[j['prepared_id']], data)
        g = next(g for g in groups if g['title'] == 'Naruto Shippūden')
        settings = picture.load('/none')
        v = up.show_view(settings, g)
        self.assertEqual((v['chosen'], v['choices']), (picture.OFF, [picture.OFF, '1440p', '4K UHD']))
        self.assertEqual([(r['chip'], r['line']) for r in v['rows']], [('Ready', '4K copy · 640 MB'), ('Making', '42 % · about 18 min')])
        self.assertEqual((v['primary'], v['remove']), ('', 'Remove the 4K copy…'))   # every episode already has one
        self.assertEqual(v['sub'], '2 episodes · 1080p')
        settings = up.set_show(settings, g, '4K UHD')
        self.assertEqual(up.show_view(settings, g)['chosen'], '4K UHD')
        settings, data = up.remove_copies(settings, data, g)
        self.assertEqual(sorted(data['remove']), ['id1', 'id2'])
        self.assertEqual(up.show_view(settings, g)['chosen'], picture.OFF)          # Off: nothing is made again
        fresh = up.library(PREP, lambda j: media[j['prepared_id']], {'copies': {}})
        g2 = next(g for g in fresh if g['title'] == 'Naruto Shippūden')
        v2 = up.show_view(picture.load('/none'), g2)
        self.assertTrue(v2['primary'].startswith('Upscale all 2 · about '), v2['primary'])
        self.assertEqual(v2['primary_size'], '4K UHD')
        self.assertEqual(v2['remove'], '')

    def test_toggles(self):
        s = up.toggle(picture.load('/none'), 'prepare')
        self.assertTrue(s['downloads']['prepare'])
        self.assertFalse(up.toggle(s, 'only_charging')['downloads']['only_charging'])


if __name__ == '__main__':
    unittest.main()


class OneRowPerShow(unittest.TestCase):
    """Owner screenshot (2026-11-13): "Phony" was listed twice: some episodes matched TMDb, others only by name."""
    def test_a_name_only_group_joins_the_tmdb_group(self):
        jobs = {}
        for n in range(1, 6):
            jobs['p%d' % n] = {'status': 'done', 'prepared_id': 'p%d' % n, 'source': {'id': 'p%d' % n, 'name': 'Phony S01E%02d.mkv' % n},
                               'probe': {'width': 1920, 'height': 1080, 'hdr': False, 'duration': 1400}}
        def media_for(job):
            n = int(job['source']['name'].split('E')[-1][:2])
            return {'type': 'tv', 'show': 'Phony', 'tmdb': '250000' if n <= 3 else '', 'season': 1, 'episode': n}
        groups = up.library({'jobs': jobs}, media_for, {'copies': {}})
        self.assertEqual([(g['key'], len(g['videos'])) for g in groups], [('tv:250000', 5)])
        self.assertEqual(sorted(i['episode'] for i in groups[0]['items']), [1, 2, 3, 4, 5])

    def test_different_shows_stay_apart(self):
        jobs = {'a': {'status': 'done', 'prepared_id': 'a', 'source': {'id': 'a', 'name': 'Phony S01E01.mkv'},
                      'probe': {'width': 1920, 'height': 1080, 'hdr': False}},
                'b': {'status': 'done', 'prepared_id': 'b', 'source': {'id': 'b', 'name': 'Lanterns S01E01.mkv'},
                      'probe': {'width': 1920, 'height': 1080, 'hdr': False}}}
        media = {'a': {'type': 'tv', 'show': 'Phony', 'tmdb': '1'}, 'b': {'type': 'tv', 'show': 'Lanterns', 'tmdb': ''}}
        groups = up.library({'jobs': jobs}, lambda job: media[job['prepared_id']], {'copies': {}})
        self.assertEqual(sorted(g['key'] for g in groups), ['title:lanterns', 'tv:1'])


class MainPage(unittest.TestCase):
    """DEC-044 board A/B: the AI Upscale page model (upscale_main_page draws it)."""
    def data(self):
        copies = {'a': {'label': '4K UHD', 'status': 'running', 'name': 'Hell House LLC Origins S01E01.mkv', 'progress': 12,
                        'eta': '1 h 40 min', 'width': 1920, 'height': 1080, 'duration': 2640, 'added': 1},
                  'b': {'label': '4K UHD', 'status': 'waiting', 'name': 'Hell House LLC Origins S01E02.mkv', 'width': 1920,
                        'height': 1080, 'duration': 2640, 'added': 2},
                  'c': {'label': '4K UHD', 'status': 'waiting', 'name': 'Phony S01E01.mkv', 'width': 1920, 'height': 1080,
                        'duration': 1500, 'added': 3},
                  'd': {'label': '4K UHD', 'status': 'cancelled', 'name': 'Phony S01E02.mkv', 'added': 4},
                  'e': {'label': '4K UHD', 'status': 'ready', 'name': 'Lanterns S01E01.mkv', 'size': 3 * 10 ** 9, 'copy_id': 'x'}}
        return {'copies': copies, 'engine': {'upscales': True, 'model': 2}}

    def test_the_card_up_next_and_space(self):
        settings = picture.defaults() if hasattr(picture, 'defaults') else {'downloads': {}, 'shows': {}, 'default': {'upscale': picture.OFF}}
        v = up.main_view(settings, self.data(), [], {'upscales': True, 'model': 2})
        self.assertEqual((v['making']['title'], v['making']['line'], v['making']['grey']),
                         ('Hell House LLC Origins · E1', 'To 4K · 12 % · 1 h 40 min left', False))
        self.assertEqual([r['title'] for r in v['next']], ['Hell House LLC Origins · E2', 'Phony · E1'])   # not the cancelled one
        self.assertEqual(v['next'][0]['line'], '1080p → 4K · about 1 h 10 min')
        self.assertEqual(v['space'], '1 copy · 3.0 GB')
        self.assertTrue(v['can_cancel_all'])
        self.assertEqual(v['engine']['title'], 'Ready on this iPhone')

    def test_paused_and_waiting_say_why_and_never_show_a_blank_title(self):
        data = self.data()
        v = up.making(data, paused=True)
        self.assertEqual((v['line'], v['grey'], v['paused']), ('Paused by you', True, True))
        data['copies']['a'].update(status='waiting', note='Waiting for a charger')
        v = up.making(data)
        self.assertEqual((v['key'], v['line'], v['grey']), ('a', 'Waiting for a charger', True))
        self.assertEqual(up.copy_title({'name': ''}, 'abc'), 'abc')              # the rig's blank "Making now" row

    def test_the_copy_sheet(self):
        s = up.copy_sheet(self.data(), 'a', device={'charging': 1, 'thermal': 'nominal'})
        self.assertEqual((s['sub'], s['device'], s['pause']), ('Episode 1 · 1080p → 4K UHD', 'On charger · phone cool', 'Pause'))
        self.assertEqual([st for st, _ in s['stages']], ['done', 'now', 'next'])
        self.assertTrue(s['stages'][2][1].startswith('Saving to Google Drive · '))
        self.assertEqual(up.copy_sheet(self.data(), 'a', paused=True)['pause'], 'Resume')

    def test_the_windows_are_drawn(self):
        import portrait
        import upscale_main_page as mp
        page = mp.page(portrait)
        for ident in (mp.BACK, mp.MAKING, mp.MAKING_PAUSE, mp.EDIT, mp.NEXT + 2, mp.SHOW_ALL, mp.SHOW + mp.SHOW_SLOTS - 1, mp.NEW,
                      mp.SIZE, mp.CHARGE, mp.ENGINE, mp.SPACE, mp.CANCEL_ALL):
            self.assertIn('id="%d"' % ident, page)
        self.assertIn('Cancel All Upscaling', page)
        sheet = mp.sheet(portrait)
        for ident in (mp.SHEET_CLOSE, mp.SHEET_PAUSE, mp.SHEET_CANCEL):
            self.assertIn('id="%d"' % ident, sheet)
        edit = mp.edit(portrait)
        for ident in (mp.DONE, mp.REMOVE_ALL, mp.REMOVE, mp.MOVE + mp.EDIT_SLOTS - 1):
            self.assertIn('id="%d"' % ident, edit)
        files = portrait.portrait_files.__code__.co_names
        self.assertIn('upscale_main_page', (Path(portrait.__file__)).read_text())
