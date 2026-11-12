"""DEC-039/DEC-040: AI Upscale sizes (only sizes above the video, never larger than asked) and per-show pictures."""
import json, os, sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'migration/bundled-bootstrap/resources/lib'))
import picture as pc


class Sizes(unittest.TestCase):
    def test_only_sizes_above_the_video(self):
        self.assertEqual(pc.above(854, 480), ['720p', '1080p', '1440p', '2K', '4K UHD'])   # a 480p show gets all five
        self.assertEqual(pc.above(1280, 720), ['1080p', '1440p', '2K', '4K UHD'])
        self.assertEqual(pc.above(1920, 1080), ['1440p', '2K', '4K UHD'])                 # a 1080p film starts at 1440p
        self.assertEqual(pc.above(2560, 1440), ['2K', '4K UHD'])
        self.assertEqual(pc.above(3840, 2160), [])                                        # a 4K film: no upscaler
        self.assertEqual(pc.above(0, 0), [])

    def test_scope_and_cropped_pictures_count_as_their_size(self):
        self.assertEqual(pc.above(1920, 800), ['1440p', '2K', '4K UHD'])
        self.assertEqual(pc.above(1916, 1036), ['1440p', '2K', '4K UHD'])
        self.assertEqual(pc.above(1280, 536), ['1080p', '1440p', '2K', '4K UHD'])
        self.assertEqual(pc.above(3840, 1600), [])
        self.assertEqual(pc.above(3996, 2160), [])

    def test_target_is_never_larger_than_asked(self):
        self.assertEqual(pc.target(1920, 1080, '4K UHD'), '4K UHD')
        self.assertEqual(pc.target(1920, 1080, '1440p'), '1440p')
        self.assertIsNone(pc.target(1920, 1080, '1080p'))     # not above the video
        self.assertIsNone(pc.target(1920, 1080, '720p'))
        self.assertIsNone(pc.target(3840, 2160, '4K UHD'))     # 4K sources are never upscaled
        self.assertIsNone(pc.target(1920, 1080, 'Off'))
        self.assertIsNone(pc.target(1920, 1080, 'bogus'))
        self.assertEqual(pc.target(1280, 720, '2K'), '2K')

    def test_fitted_keeps_the_shape(self):
        self.assertEqual(pc.fitted(1920, 1080, '4K UHD'), (3840, 2160))
        self.assertEqual(pc.fitted(1280, 720, '4K UHD'), (3840, 2160))
        self.assertEqual(pc.fitted(1920, 800, '4K UHD'), (3840, 1600))
        self.assertEqual(pc.fitted(1440, 1080, '4K UHD'), (2880, 2160))      # 4:3 stays 4:3
        self.assertEqual(pc.fitted(1920, 1080, '2K'), (2880, 1620))
        self.assertIsNone(pc.fitted(3840, 2160, '4K UHD'))
        self.assertIsNone(pc.fitted(1920, 1080, '1080p'))

    def test_box_order_matches_the_slider(self):
        self.assertEqual(pc.LABELS, ('720p', '1080p', '1440p', '2K', '4K UHD'))
        heights = [h for _, _, h in pc.SIZES]
        self.assertEqual(heights, sorted(heights))
        with self.assertRaises(ValueError):
            pc.box('8K')


NARUTO = {'type': 'episode', 'tmdb': '31910', 'show': 'Naruto Shippūden', 'drive_id': 'ep3'}
NARUTO_4 = dict(NARUTO, drive_id='ep4')
DUNE = {'type': 'movie', 'tmdb': '693134', 'title': 'Dune: Part Two', 'drive_id': 'dune'}


class Settings(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def test_default_until_a_show_has_its_own(self):
        data = pc.load(self.dir)
        self.assertEqual(pc.resolve(data, NARUTO), ('default', {'upscale': 'Off', 'saturation': 0}))
        pc.apply(data, 'show', NARUTO, upscale='4K UHD', saturation=12, now=lambda: 5)
        self.assertEqual(pc.resolve(data, NARUTO_4), ('show', {'upscale': '4K UHD', 'saturation': 12}))
        self.assertEqual(pc.resolve(data, DUNE)[0], 'default')

    def test_this_video_wins_over_the_show(self):
        data = pc.load(self.dir)
        pc.apply(data, 'show', NARUTO, upscale='4K UHD')
        pc.apply(data, 'video', NARUTO, upscale='Off', saturation=-5)
        self.assertEqual(pc.resolve(data, NARUTO)[1]['upscale'], 'Off')
        self.assertEqual(pc.resolve(data, NARUTO_4)[1]['upscale'], '4K UHD')

    def test_all_videos_moves_the_show_to_the_default(self):
        data = pc.load(self.dir)
        pc.apply(data, 'show', NARUTO, upscale='1440p')
        pc.apply(data, 'default', NARUTO, upscale='2K')
        self.assertEqual(pc.resolve(data, NARUTO), ('default', {'upscale': '2K', 'saturation': 0}))
        self.assertEqual(data['shows'], {})

    def test_reset_this_show(self):
        data = pc.load(self.dir)
        pc.apply(data, 'show', NARUTO, upscale='4K UHD')
        pc.apply(data, 'reset', NARUTO)
        self.assertEqual(pc.resolve(data, NARUTO)[0], 'default')

    def test_saved_and_read_back(self):
        data = pc.load(self.dir)
        pc.apply(data, 'show', DUNE, saturation=99)            # clamped to +50
        pc.save(self.dir, data)
        again = pc.load(self.dir)
        self.assertEqual(pc.resolve(again, DUNE)[1]['saturation'], 50)
        self.assertEqual(again['downloads'], pc.DOWNLOADS)

    def test_broken_file_reads_as_defaults(self):
        os.makedirs(os.path.dirname(pc.path(self.dir)), exist_ok=True)
        Path(pc.path(self.dir)).write_text('{nope')
        self.assertEqual(pc.resolve(pc.load(self.dir), NARUTO)[0], 'default')
        Path(pc.path(self.dir)).write_text(json.dumps({'shows': {'tv:31910': {'upscale': '16K', 'saturation': 'x'}}}))
        self.assertEqual(pc.resolve(pc.load(self.dir), NARUTO), ('show', {'upscale': 'Off', 'saturation': 0}))

    def test_show_without_tmdb_still_has_its_own(self):
        self.assertEqual(pc.show_key({'show': '  Lanterns '}), 'title:lanterns')
        self.assertEqual(pc.show_key({'type': 'movie', 'tmdb': 157336}), 'movie:157336')
        self.assertEqual(pc.show_key({}), '')
        with self.assertRaises(ValueError):
            pc.apply(pc.load(self.dir), 'video', {'show': 'x'})

    def test_board_d_rows(self):
        data = pc.load(self.dir)
        pc.apply(data, 'show', NARUTO, upscale='4K UHD', saturation=12, now=lambda: 2)
        pc.apply(data, 'show', DUNE, saturation=-5, now=lambda: 3)
        rows = pc.own_pictures(data)
        self.assertEqual([r['title'] for r in rows], ['Dune: Part Two', 'Naruto Shippūden'])
        self.assertEqual(rows[1]['line'], 'Upscale to 4K UHD · Saturation +12')
        self.assertEqual(rows[0]['line'], 'Upscale off · Saturation -5')
        self.assertTrue(rows[0]['movie'])


if __name__ == '__main__':
    unittest.main()
