"""A subtitle zip that SubDL itself says is for this episode is used when its file names the same episode number under another season (owner, build 646 log d8f39741:
Black Clover S2E8, five SubDL results, "No subtitle file for this episode" every time)."""
import io,sys,unittest,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import track_menu as tm,subtitle_sources as ss

def zipped(*names):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for n in names:z.writestr(n,'1\n00:00:01,000 --> 00:00:02,000\nHello\n')
    return buf.getvalue()

class Loose(unittest.TestCase):
    def test_exact_season_and_episode_always_wins(self):
        got=tm.subtitle_from_zip(zipped('Show.S02E08.srt','Show.S02E07.srt'),2,8)
        self.assertEqual(got[0],'Show.S02E08.srt')
    def test_another_season_number_is_refused_unless_the_provider_says_it_is_this_episode(self):
        blob=zipped('Black.Clover.S05E08.1080p.srt')
        self.assertIsNone(tm.subtitle_from_zip(blob,2,8));self.assertIn('Black.Clover.S05E08.1080p.srt',tm.ZIP_NAMES)
        self.assertEqual(tm.subtitle_from_zip(blob,2,8,loose=True)[0],'Black.Clover.S05E08.1080p.srt')
    def test_a_pack_gives_the_one_file_with_this_episode_number_only_when_it_is_unique(self):
        pack=zipped('Show.S05E07.srt','Show.S05E08.srt','Show.S05E09.srt')
        self.assertEqual(tm.subtitle_from_zip(pack,2,8,loose=True)[0],'Show.S05E08.srt')
        self.assertIsNone(tm.subtitle_from_zip(pack,2,8))
        two=zipped('Show.S01E08.srt','Show.S05E08.srt')   # two seasons with an episode 8: not guessed
        self.assertIsNone(tm.subtitle_from_zip(two,2,8,loose=True))
    def test_a_file_for_another_episode_is_never_taken(self):
        self.assertIsNone(tm.subtitle_from_zip(zipped('Show.S05E09.srt'),2,8,loose=True))
    def test_subdl_marks_a_result_whose_own_episode_matches(self):
        body='{"status":true,"subtitles":[{"url":"/subtitle/1-1.zip","lang":"EN","release_name":"r","episode":8},{"url":"/subtitle/2-2.zip","lang":"EN","release_name":"pack","episode":0}]}'
        found=ss.subdl_parse(body,'en',2,8)
        self.assertEqual([r['episode_match'] for r in found],[True,False])
    def test_the_failed_download_names_the_files(self):
        text=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertIn("log('subtitle files in the last zip: %s'",text)
if __name__=='__main__':unittest.main()
