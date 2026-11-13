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
