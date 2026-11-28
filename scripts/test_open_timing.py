"""Roadmap 1C.1: one 'open timing' line per video, tap to playing picture, with the stages where the time went."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import open_timing as ot

class Home(dict):
    def setProperty(self,k,v):self[k]=v
    def getProperty(self,k):return self.get(k,'')
    def clearProperty(self,k):self.pop(k,None)

class OpenTiming(unittest.TestCase):
    def test_logs_once_when_the_picture_plays(self):
        home,lines=Home(),[]
        ot.mark(home,'library',now=100.0)
        self.assertFalse(ot.check(home,lambda:False,lines.append,now=101.0))
        self.assertTrue(ot.check(home,lambda:True,lines.append,now=105.8))
        self.assertEqual(lines,['Kodi iOS open timing: 5.8 s via library [streams ready; first picture not measured]'])
        self.assertFalse(ot.check(home,lambda:True,lines.append,now=106.0))
    def test_the_first_picture_is_logged_when_the_playback_clock_moves(self):
        home,lines=Home(),[];ot.WAITING.clear()
        ot.mark(home,'library',now=100.0)
        ot.check(home,lambda:True,lines.append,now=101.3)
        self.assertFalse(ot.check_moving(lines.append,lambda:False,now=103.0))
        self.assertTrue(ot.check_moving(lines.append,lambda:True,now=104.4))
        self.assertIn('first picture (playback clock moving) 4.4 s after the tap via library, 3.1 s after streams ready',lines[-2])
        self.assertEqual(lines[-1],'Kodi iOS open record: via=library | source=- | route=- | tap=- | streams ready 1.3 s | stages - | first picture 4.4 s')
        self.assertFalse(ot.check_moving(lines.append,lambda:True,now=105.0))   # logged once
    def test_one_record_line_has_the_same_fields_for_every_open(self):
        home,lines=Home(),[];ot.WAITING.clear();ot.DETAIL.clear()
        ot.mark(home,'umbrella',now=200.0)
        home.setProperty(ot.ROUTE,'cache 3/3 wait 0.1 s');home.setProperty(ot.SOURCE,'alldebrid|torrentio');home.setProperty(ot.TAP,'S4E8 Heavy y=2/8')
        ot.check(home,lambda:True,lines.append,now=201.3,probe=lambda:{'media':True,'video':True})
        ot.check_moving(lines.append,lambda:True,now=203.2,home=home)
        record=lines[-1]
        self.assertTrue(record.startswith('Kodi iOS open record: via=umbrella | source=alldebrid|torrentio | route=cache 3/3 wait 0.1 s | tap=S4E8 Heavy y=2/8 | streams ready 1.3 s | stages '))
        self.assertTrue(record.endswith('| first picture 3.2 s'))
        self.assertEqual(record.count(' | '),6);self.assertEqual(home.getProperty(ot.TAP),'')   # the tap is named once, then cleared
        self.assertEqual(ot.DETAIL,{})   # nothing left behind
        home2,lines2=Home(),[]
        ot.mark(home2,'umbrella',now=300.0)   # a new open clears the earlier route and source
        self.assertEqual((home2.getProperty(ot.ROUTE),home2.getProperty(ot.SOURCE)),('',''))
    def test_a_clock_that_never_moves_leaves_no_record_behind(self):
        home,lines=Home(),[];ot.WAITING.clear();ot.DETAIL.clear()
        ot.mark(home,'library',now=100.0);ot.check(home,lambda:True,lines.append,now=101.0)
        ot.check_moving(lines.append,lambda:False,now=140.0)
        self.assertEqual((ot.WAITING,ot.DETAIL),({},{}));self.assertFalse(any('open record' in l for l in lines))
    def test_the_late_verdict_comes_with_the_first_picture_or_when_none_came(self):
        home,lines,told=Home(),[],[];ot.WAITING.clear();ot.DETAIL.clear();ot.LATE[:]=[lambda ok,via,seconds:told.append((ok,via,round(seconds,1)))]
        try:
            ot.mark(home,'umbrella',now=100.0);ot.check(home,lambda:True,lines.append,now=104.5)
            ot.check_moving(lines.append,lambda:True,now=108.5,home=home)
            ot.mark(home,'umbrella',now=200.0);ot.check(home,lambda:True,lines.append,now=203.0)
            ot.check_moving(lines.append,lambda:False,now=240.0,home=home)
        finally:ot.LATE[:]=[]
        self.assertEqual(told,[(True,'umbrella',8.5),(False,'umbrella',40.0)])
    def test_a_clock_that_never_moves_is_reported_then_forgotten(self):
        home,lines=Home(),[];ot.WAITING.clear()
        ot.mark(home,'library',now=100.0);ot.check(home,lambda:True,lines.append,now=101.0)
        self.assertTrue(ot.check_moving(lines.append,lambda:False,now=131.0))
        self.assertIn('playback clock still not moving 31 s after the tap',lines[-1]);self.assertEqual(ot.WAITING,{})
    def test_a_stale_mark_is_dropped(self):
        home,lines=Home(),[]
        ot.mark(home,'drive copy',now=0.0)
        self.assertTrue(ot.check(home,lambda:False,lines.append,now=121.0))
        self.assertIn('no picture after 121 s via drive copy',lines[0])

class Stages(unittest.TestCase):
    def run_open(self,steps,playing_at,via='library',resolved=None):
        """steps: {time: (media, video)} the probe reports from that time on."""
        home,lines=Home(),[]
        ot.mark(home,via,now=100.0)
        state={'now':100.0}
        probe=lambda:dict(zip(('media','video'),max(((t,v) for t,v in steps.items() if t<=state['now']),default=(0,(False,False)))[1]))
        t=100.0
        while t<=playing_at+0.01:
            state['now']=t
            if resolved is not None and t>=resolved:ot.stamp_resolved(home,now=resolved)
            if ot.check(home,lambda:t>=playing_at,lines.append,now=t,probe=probe):break
            t=round(t+0.2,3)
        return lines
    def test_one_line_names_where_the_time_went(self):
        lines=self.run_open({100:(False,False),100.8:(True,False),104.6:(True,True)},105.6,resolved=100.4)
        self.assertEqual(lines,['Kodi iOS open timing: 5.6 s via library (resolve 0.4 s, handoff 0.4 s, open 3.8 s, ready 1.0 s) [streams ready; first picture not measured]'])
    def test_stages_that_were_not_seen_are_left_out(self):
        lines=self.run_open({100:(False,False),103.0:(True,True)},104.0)     # no resolve stamp; media and video seen together
        self.assertEqual(lines,['Kodi iOS open timing: 4.0 s via library (handoff 3.0 s, open 0.0 s, ready 1.0 s) [streams ready; first picture not measured]'])
        lines=self.run_open({100:(False,False)},101.0)                       # nothing seen: only the total
        self.assertEqual(lines,['Kodi iOS open timing: 1.0 s via library [streams ready; first picture not measured]'])
    def test_an_earlier_video_still_playing_is_not_counted_as_this_open(self):
        # media/video are already true when the mark is set (the old video): never seen off, so no stage from them
        lines=self.run_open({100:(True,True)},102.0)
        self.assertEqual(lines,['Kodi iOS open timing: 2.0 s via library [streams ready; first picture not measured]'])
    def test_a_resolved_stamp_from_an_older_open_is_ignored(self):
        home,lines=Home(),[]
        ot.stamp_resolved(home,now=50.0);ot.mark(home,'library',now=100.0)
        self.assertEqual(home.getProperty(ot.RESOLVED),'')     # mark() clears it
        home[ot.RESOLVED]='50.0'                               # a plugin that set it earlier and stale
        ot.check(home,lambda:True,lines.append,now=102.0,probe=lambda:{})
        self.assertEqual(lines,['Kodi iOS open timing: 2.0 s via library [streams ready; first picture not measured]'])
    def test_a_give_up_line_says_which_stages_were_reached(self):
        home,lines=Home(),[]
        ot.mark(home,'library',now=0.0)
        flags={'v':(False,False)}
        ot.check(home,lambda:False,lines.append,now=1.0,probe=lambda:{'media':False,'video':False})
        ot.check(home,lambda:False,lines.append,now=3.0,probe=lambda:{'media':True,'video':False})
        ot.check(home,lambda:False,lines.append,now=121.0,probe=lambda:{'media':True,'video':False})
        self.assertEqual(lines,['Kodi iOS open timing: no picture after 121 s via library (media at 3.0 s)'])
    def test_the_marks_cleans_up_after_itself(self):
        home=Home();ot.mark(home,'library',now=1.0);ot.check(home,lambda:True,lambda t:None,now=2.0)
        self.assertEqual(dict(home),{});self.assertEqual(ot._seen,{})

class Wiring(unittest.TestCase):
    def test_the_library_route_stamps_the_hand_over_and_the_service_probes_kodi(self):
        root=Path(__file__).resolve().parents[1]
        lib=(root/'migration/import-overlays/plugin.video.kodi.ios.watch/resources/lib/ios_library.py').read_text()
        self.assertIn("mark_resolved()\n xbmcplugin.setResolvedUrl(handle,True,li)",lib)
        self.assertIn("'KodiIOS.OpenResolved'",lib)
        self.assertEqual(ot.RESOLVED,'KodiIOS.OpenResolved')
        service=(root/'migration/bundled-bootstrap/service.py').read_text()
        self.assertIn("Player.HasMedia",service);self.assertIn("Player.HasVideo'",service)
    def test_a_player_closed_before_the_picture_gives_no_verdict(self):
        # ISSUE-488 (owner log ff742bd7): closed 3 s after "streams ready", 12 s later "still not moving" ranked a good source last
        ot.WAITING.clear(); told = []; ot.LATE.append(lambda ok, via, seconds: told.append(ok))
        try:
            ot.WAITING[100.0] = (103.0, 'umbrella'); lines = []
            self.assertTrue(ot.check_moving(lines.append, lambda: False, now=140.0, alive=lambda: False))
            self.assertEqual(told, [])
            self.assertIn('no verdict', lines[0])
            ot.WAITING[200.0] = (203.0, 'umbrella')   # a video still there that never gets going is still judged
            self.assertTrue(ot.check_moving(lines.append, lambda: False, now=240.0, alive=lambda: True))
            self.assertEqual(told, [False])
        finally:
            ot.LATE.pop(); ot.WAITING.clear()

    def test_a_slow_resolution_is_not_a_no_picture_verdict(self):
        # ISSUE-494 (owner log e41f48ad): streams ready 38 s after the tap (Umbrella scanning a 158-file pack) was judged "no picture" in the same instant
        ot.WAITING.clear(); told = []; ot.LATE.append(lambda ok, via, seconds: told.append(ok))
        try:
            ot.WAITING[100.0] = (138.0, 'umbrella'); lines = []
            self.assertFalse(ot.check_moving(lines.append, lambda: False, now=143.0))      # 43 s after the tap, 5 s after ready: still opening
            self.assertEqual(told, [])
            self.assertTrue(ot.check_moving(lines.append, lambda: False, now=160.0))       # 22 s after ready: really no picture
            self.assertEqual(told, [False])
        finally:
            ot.LATE.pop(); ot.WAITING.clear()


if __name__=='__main__':unittest.main()
