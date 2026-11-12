"""V1 (DEC-039/042, video-picture-mockups round 4): the Picture menu's rules — slider stops, scope, Saturation,
Apply to, AirPlay states, Prepare a copy."""
import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import picture as pc
import picture_menu as pm

NARUTO = {'type': 'tv', 'tmdb': '31910', 'show': 'Naruto Shippuden', 'title': 'Naruto Shippuden S01E03', 'drive_id': 'ep3'}
DUNE = {'type': 'movie', 'tmdb': '693134', 'show': 'Dune: Part Two', 'drive_id': 'dune'}
STREAM = {'type': 'tv', 'show': 'Dragon Ball', 'title': 'Dragon Ball S01E01', 'drive_id': ''}


class Board_A(unittest.TestCase):
    def setUp(self):
        self.s = pc.load(tempfile.mkdtemp())

    def test_only_sizes_above_the_video(self):
        self.assertEqual(pm.model(NARUTO, 854, 480, self.s)['stops'], ['Off', '720p', '1080p', '1440p', '4K'])
        self.assertEqual(pm.model(NARUTO, 1920, 1080, self.s)['stops'], ['Off', '1440p', '4K'])
        four_k = pm.model(DUNE, 3840, 2160, self.s)
        self.assertEqual((four_k['stops'], four_k['show_upscale']), ([], False))     # a 4K film: Saturation only

    def test_tag_scope_and_chosen(self):
        pc.apply(self.s, 'show', NARUTO, upscale='4K UHD', saturation=12)
        m = pm.model(NARUTO, 1920, 1080, self.s)
        self.assertEqual((m['src'], m['scope_words'], m['chosen'], m['sel'], m['saturation_text']), ('1080p', 'This show', '4K', 2, '+12'))
        self.assertEqual(pm.model(DUNE, 1920, 1080, self.s)['scope_words'], 'All videos')
        pc.apply(self.s, 'show', DUNE, saturation=-5)
        self.assertEqual(pm.model(DUNE, 1920, 1080, self.s)['scope_words'], 'This movie')

    def test_a_tap_writes_where_the_picture_lives(self):
        pm.choose_stop(self.s, NARUTO, 1920, 1080, 2)                 # no own picture: the default changes
        self.assertEqual(self.s['default']['upscale'], '4K UHD')
        pc.apply(self.s, 'show', NARUTO, upscale='1440p')
        pm.choose_stop(self.s, NARUTO, 1920, 1080, 0)                 # the show keeps its own: Off for the show only
        self.assertEqual((self.s['shows']['tv:31910']['upscale'], self.s['default']['upscale']), ('Off', '4K UHD'))
        pm.choose_stop(self.s, NARUTO, 1920, 1080, 9)                 # out of range: nothing changes
        self.assertEqual(self.s['shows']['tv:31910']['upscale'], 'Off')

    def test_saturation_steps_and_clamps(self):
        for _ in range(20):
            pm.nudge_saturation(self.s, DUNE, +1)
        self.assertEqual(pm.model(DUNE, 1920, 1080, self.s)['saturation'], 50)
        pm.nudge_saturation(self.s, DUNE, -1)
        self.assertEqual(pm.props(pm.model(DUNE, 1920, 1080, self.s))['sat'], '+45')

    def test_props_for_the_window(self):
        p = pm.props(pm.model(NARUTO, 1920, 1080, self.s))
        self.assertEqual((p['stops'], p['stop.0'], p['stop.2'], p['stop.3'], p['upscale'], p['sel']), ('3', 'Off', '4K', '', 'true', '0'))
        self.assertEqual(p['satpct'], '50')


class Board_B(unittest.TestCase):
    def setUp(self):
        self.s = pc.load(tempfile.mkdtemp())

    def test_apply_to_moves_the_picture(self):
        pc.apply(self.s, 'default', NARUTO, upscale='1440p', saturation=10)
        pm.apply_to(self.s, NARUTO, 'show')
        self.assertEqual(pc.resolve(self.s, NARUTO), ('show', {'upscale': '1440p', 'saturation': 10}))
        pm.apply_to(self.s, NARUTO, 'video')
        self.assertEqual(pc.resolve(self.s, NARUTO)[0], 'video')
        pm.apply_to(self.s, NARUTO, 'reset')
        self.assertEqual(pc.resolve(self.s, NARUTO)[0], 'default')

    def test_rows(self):
        m = pm.model(NARUTO, 1920, 1080, self.s)
        self.assertEqual(pm.apply_rows(m, NARUTO), [('video', 'This video only', False), ('show', 'This show · Naruto Shippuden', False),
                                                    ('default', 'All videos (my default)', True)])
        self.assertEqual([r[0] for r in pm.apply_rows(pm.model(STREAM, 1920, 1080, self.s), STREAM)], ['show', 'default'])


class Board_E(unittest.TestCase):
    def setUp(self):
        self.s = pc.load(tempfile.mkdtemp())
        pc.apply(self.s, 'show', NARUTO, upscale='4K UHD')

    def test_three_states(self):
        ready = pm.model(NARUTO, 1920, 1080, self.s, {'copies': {'ep3': {'status': 'ready', 'label': '4K UHD'}}}, airplay=True)
        self.assertEqual(pm.airplay_lines(ready['airplay'])[0], '4K UHD copy ready on Google Drive')
        making = pm.model(NARUTO, 1920, 1080, self.s, {'copies': {'ep3': {'status': 'running', 'label': '4K UHD', 'progress': 42, 'eta': 'about 18 min'}}}, airplay=True)
        self.assertEqual(pm.airplay_lines(making['airplay']), ('Preparing', 'Upscaling to 4K UHD · 42 % · about 18 min', ''))
        offer = pm.model(NARUTO, 1920, 1080, self.s, {'copies': {}}, airplay=True)
        self.assertEqual(pm.airplay_lines(offer['airplay'])[2], 'Prepare a 4K UHD copy')
        self.assertEqual(pm.props(offer)['tv.state'], 'offer')
        none = pm.model(NARUTO, 1920, 1080, self.s, {'copies': {}}, airplay=True, ai_available=False)
        self.assertEqual(pm.airplay_lines(none['airplay'])[0], 'Not available on this iPhone')

    def test_prepare_a_copy_once(self):
        data = pm.prepare_copy({'copies': {}}, NARUTO, 1920, 1080, '4K UHD', clock=lambda: 5)
        self.assertEqual(data['copies']['ep3']['status'], 'waiting')
        data['copies']['ep3']['status'] = 'running'
        self.assertEqual(pm.prepare_copy(data, NARUTO, 1920, 1080, '4K UHD')['copies']['ep3']['status'], 'running')
        self.assertEqual(pm.prepare_copy({'copies': {}}, STREAM, 1920, 1080, '4K UHD'), {'copies': {}})

    def test_streams_say_downloads_only(self):
        m = pm.model(STREAM, 1920, 1080, self.s, {}, airplay=True)
        self.assertEqual((m['airplay'], m['note']), (None, 'AI Upscale works on downloads (a copy is made on Google Drive).'))


class Window(unittest.TestCase):
    def test_no_double_negation_in_conditions(self):
        # Rig (build of V1): the card's background never showed: '!' + '!String.IsEmpty(...)' reads as '!String.IsEmpty'.
        import picture_osd
        from xml.dom import minidom
        text = picture_osd.menu()
        minidom.parseString(text.encode())
        self.assertNotIn('!!', text)
        self.assertIn('String.IsEmpty(Window().Property(upscale))', text)

    def test_every_stop_has_its_own_button(self):
        import picture_osd as po
        xml = po.menu()
        ids = [po.stop_id(n, k) for n in range(2, 6) for k in range(n)]
        self.assertEqual(len(ids), len(set(ids)))
        for i in ids:
            self.assertIn('id="%d"' % i, xml)


if __name__ == '__main__':
    unittest.main()
