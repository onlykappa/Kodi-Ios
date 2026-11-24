"""A tap on a Continue Watching card raises the loading circle at once (owner, build 646: "make it start loading when i click it ... i shouldnt have time to tap it again")."""
import sys,unittest
from pathlib import Path
sys.dont_write_bytecode=True
LIB=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'
sys.path.insert(0,str(LIB))
import portrait as p

class PlayNow(unittest.TestCase):
    def test_the_circle_comes_first_and_then_the_play(self):
        text=p.play_now()
        self.assertLess(text.index('ActivateWindow(busydialognocancel)'),text.index('PlayMedia('))
        self.assertIn('$ESCINFO[ListItem.FileNameAndPath]',text)
    def test_a_row_plays_its_own_list_not_whatever_control_has_focus(self):   # build 682 log 1355c1d8
        self.assertIn('PlayMedia($ESCINFO[Container(5001).ListItem(0).FileNameAndPath])',p.play_now(5001))
        widget={'label':'Continue Watching','path':'plugin://x/','target':'videos','style':'continue'}
        row=p.row(0,widget,False);self.assertIn('Container(5001).ListItem(0).FileNameAndPath',row);self.assertNotIn('$ESCINFO[ListItem.FileNameAndPath]',row)
    def test_the_tap_sets_the_flag_that_keeps_the_circle_up(self):   # build 663 log 63e92ff2
        text=p.play_now()
        self.assertLess(text.index('SetProperty(KodiIOS.ContinueOpening,1,home)'),text.index('ActivateWindow(busydialognocancel)'))
        service=(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn('continue_guard.Circle(',service);self.assertIn('circle=circle',service);self.assertIn("KodiIOS.ContinueOpening",service)
    def test_only_the_continue_watching_row_has_it(self):
        widget={'label':'Continue Watching','path':'plugin://x/','target':'videos','style':'continue'}
        other={'label':'Trending','path':'plugin://y/','target':'videos','style':'card'}
        self.assertIn('busydialognocancel',p.row(0,widget,False))
        self.assertNotIn('busydialognocancel',p.row(1,other,False))
    def test_the_service_closes_the_circle_when_the_video_starts(self):
        text=(LIB/'portrait.py').read_text()
        self.assertIn("Dialog.Close(busydialognocancel,true)')   # the circle a Continue Watching tap raised",text)
if __name__=='__main__':unittest.main()
