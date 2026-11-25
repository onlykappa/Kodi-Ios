"""Subtitles that are there without asking (owner, build 646 logs: "make subtitles work reliably everytime everywhere")."""
import sys,tempfile,unittest
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'migration/bundled-bootstrap/resources/lib'))
import auto_subtitles as a

FORCED={'index':0,'language':'eng','name':'American English','isforced':True}
FULL={'index':1,'language':'eng','name':'English','isforced':False}
GERMAN={'index':2,'language':'ger','name':'German'}

class Need(unittest.TestCase):
    def test_a_forced_only_track_is_not_a_subtitle_track_for_the_dialogue(self):   # Black Clover: "#0 eng American English forced"
        yes,why=a.needed([FORCED],'en','jpn',False);self.assertTrue(yes,why)
    def test_no_track_in_the_language_at_all(self):
        yes,_=a.needed([GERMAN],'en','jpn',False);self.assertTrue(yes)
        yes,_=a.needed([],'en','jpn',False);self.assertTrue(yes)
    def test_a_full_track_is_enough(self):
        self.assertFalse(a.needed([FORCED,FULL],'en','jpn',False)[0])
    def test_a_track_whose_cues_have_no_length_does_not_count(self):   # the Lanterns copies
        self.assertTrue(a.needed([FULL],'en','jpn',False,zero=lambda index:index==1)[0])
        self.assertFalse(a.needed([FULL],'en','jpn',False,zero=lambda index:None)[0])
    def test_a_downloaded_file_counts(self):
        self.assertFalse(a.needed([dict(FULL,name='123456 (External)')],'en','jpn',False)[0])
    def test_only_when_a_subtitle_is_wanted(self):
        self.assertFalse(a.needed([],'en','eng',False)[0])           # English sound, English subtitles not asked for all the time
        self.assertTrue(a.needed([],'en','eng',True)[0])             # asked for all the time
        self.assertFalse(a.needed([],'en','',False)[0])              # sound language unknown: not guessed
        self.assertFalse(a.needed([],'','jpn',False)[0])             # no subtitle language

class Once(unittest.TestCase):
    def test_a_video_is_tried_once_per_window(self):
        root=tempfile.mkdtemp();t=[1000.0]
        self.assertTrue(a.allowed(root,'tv|show|2|8',lambda:t[0]));self.assertFalse(a.allowed(root,'tv|show|2|8',lambda:t[0]+10))
        self.assertTrue(a.allowed(root,'tv|other|1|1',lambda:t[0]+10));self.assertTrue(a.allowed(root,'tv|show|2|8',lambda:t[0]+a.EVERY+1))
        self.assertFalse(a.allowed(root,'',lambda:t[0]))
    def test_consider_starts_the_fetch_only_for_a_long_enough_video_that_needs_it(self):
        root=tempfile.mkdtemp();launched=[];logs=[]
        go=lambda **k:a.consider(root,k.get('key','tv|a|1|1'),k.get('duration',1400),k.get('streams',[FORCED]),'en',k.get('audio','jpn'),False,lambda i:None,lambda:launched.append(1),logs.append)
        self.assertEqual(go(duration=120),'too short');self.assertEqual(launched,[])
        self.assertEqual(go(streams=[FULL]).split(' ')[0],'a');self.assertEqual(launched,[])
        self.assertEqual(go(),'started');self.assertEqual(launched,[1]);self.assertIn('auto subtitles',logs[0])
        self.assertEqual(go(),'tried lately');self.assertEqual(launched,[1])
    def test_it_never_raises(self):
        def boom():raise RuntimeError('x')
        self.assertEqual(a.consider(tempfile.mkdtemp(),'k',1400,[],'en','jpn',False,lambda i:None,boom,lambda t:None),'failed')

class Wiring(unittest.TestCase):
    def test_the_service_and_the_script_use_it(self):
        portrait=(ROOT/'migration/bundled-bootstrap/resources/lib/portrait.py').read_text()
        self.assertIn('auto_subtitles.consider(',portrait);self.assertIn("RunScript(service.kodi.ios.bootstrap,tracks,auto)",portrait)
        tracks=(ROOT/'migration/bundled-bootstrap/tracks.py').read_text()
        self.assertIn("if mode == 'auto':",tracks);self.assertIn("'speed', 'auto')",tracks);self.assertIn("for name in ('item', 'video', 'played', 'search', 'fetch_result', 'apply'):",tracks)
if __name__=='__main__':unittest.main()
