"""Sports pages open on last time's answer and redraw when the real one arrives (owner, build 618: black screens for a second as the pages updated)."""
import json,os,sys,tempfile,threading,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap/resources/lib'))
import sports_espn as se
import sports_fresh as fresh
import sports_model as sm

def board(state='pre'):
    return {'events':[{'id':'e1','date':'2026-11-21T00:00Z','competitions':[{'status':{'type':{'state':state}},'competitors':[
        {'homeAway':'away','score':'0','team':{'id':'a','displayName':'Away FC','shortDisplayName':'Away','abbreviation':'AWY'}},
        {'homeAway':'home','score':'0','team':{'id':'h','displayName':'Home FC','shortDisplayName':'Home','abbreviation':'HOM'}}]}]}]}

class Disk(unittest.TestCase):
    def make(self,path,answers,now=[1_795_000_000]):
        calls=[]
        def fetch(url):
            calls.append(url)
            if not answers:raise OSError('offline')
            return answers[0]
        p=se.EspnProvider(fetch=fetch,clock=lambda:now[0],leagues={'NHL'},snapshot_path=path);p.calls=calls;return p
    def test_a_fetched_answer_is_kept_and_a_new_start_offers_it_without_waiting(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'s','snap.json');first=self.make(path,[board()])
            first.refresh();self.assertTrue(os.path.exists(path));self.assertFalse(first.remembered())
            second=self.make(path,[board()],[1_795_000_100]);self.assertTrue(second.remembered())
            started=time.monotonic();second.upcoming_games();self.assertLess(time.monotonic()-started,1)
            self.assertTrue(second.snapshot.get('remembered') or not second.remembered())
    def test_the_remembered_answer_is_replaced_by_the_real_one_in_the_background(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');self.make(path,[board()]).refresh()
            second=self.make(path,[board()],[1_795_000_100])
            second.upcoming_games()                      # remembered, offered at once
            for _ in range(200):
                if not second.remembered():break
                time.sleep(.01)
            self.assertFalse(second.remembered());self.assertTrue(second.calls)   # the real fetch ran by itself
    def test_an_offline_start_keeps_offering_the_remembered_answer(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');self.make(path,[board()]).refresh()
            second=self.make(path,[],[1_795_000_100])
            self.assertEqual(len(second.upcoming_games()),1)
    def test_an_old_or_corrupt_file_is_ignored(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');Path(path).write_text('{no')
            self.assertFalse(self.make(path,[board()]).remembered())
            Path(path).write_text(json.dumps({'at':1,'live':[],'upcoming':[],'leagues':[]}))
            self.assertFalse(self.make(path,[board()]).remembered())

    def test_an_answer_the_service_just_wrote_is_used_as_it_is_and_a_page_refresh_does_not_ask_espn(self):
        # Owner, build 619: "it should always know what is live ... load instantly ... it shouldn't ever need to refresh". The service keeps the file fresh.
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');self.make(path,[board()]).refresh()
            page=self.make(path,[board()],[1_795_000_020])                 # 20 s later: the service's file is still fresh
            self.assertFalse(page.remembered());self.assertEqual(len(page.upcoming_games()),1)
            self.assertEqual(page.calls,[])                                 # no request to ESPN at all
    def test_a_newer_file_replaces_the_pages_older_answer_without_a_request(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');now=[1_795_000_000]
            service=self.make(path,[board()],now);service.refresh(block=True)
            page=self.make(path,[board()],now);page.upcoming_games()
            now[0]+=30;service.refresh(block=True);os.utime(path,(time.time()+5,time.time()+5))   # the service refreshed 30 s later
            page.refresh();self.assertEqual(page.snapshot['at'],now[0]);self.assertEqual(page.calls,[])   # a page's own refresh adopts it too

    def test_a_page_never_waits_when_an_answer_is_saved(self):
        # Owner, build 620 (log 02bd6dd7): every Sports page sat on "Checking..." because a page's refresh asked ESPN whenever the saved answer was over 10 s old
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');now=[1_795_000_000]
            self.make(path,[board()],now).refresh(block=True)                   # the service saved an answer
            now[0]+=40;page=self.make(path,[board()],now)
            gate=threading.Event();fetch=page.fetch
            page.fetch=lambda url:(gate.wait(5),fetch(url))[1]                 # ESPN is slow
            started=time.monotonic();page.refresh()
            self.assertLess(time.monotonic()-started,0.5)                       # drawn at once from the saved answer
            self.assertEqual(len(page.upcoming_games()),1);self.assertEqual(page.snapshot['at'],1_795_000_000)
            gate.set()
            for _ in range(50):
                if page.snapshot['at']==now[0]:break
                time.sleep(0.02)
            self.assertEqual(page.snapshot['at'],now[0])                        # the newer answer followed in the background
    def test_a_page_waits_only_with_nothing_saved(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
            path=os.path.join(d,'snap.json');now=[1_795_000_000]
            page=self.make(path,[board()],now);page.refresh()
            self.assertTrue(page.calls);self.assertEqual(page.snapshot['at'],now[0])
            old=self.make(path,[board()],now);now[0]+=se.SHOW_SAVED+5
            old.refresh();self.assertEqual(old.snapshot['at'],now[0])           # too old to draw: asked and waited

class Page(unittest.TestCase):
    def test_the_page_redraws_once_the_real_answer_has_arrived(self):
        state={'remembered':True};drawn=[];stop=threading.Event()
        class P:
            def remembered(self):return state['remembered']
        thread=fresh.start(P(),stop,lambda:drawn.append(1),step=.005)
        time.sleep(.03);self.assertEqual(drawn,[]);state['remembered']=False;thread.join(2);self.assertEqual(drawn,[1])
    def test_nothing_starts_when_the_answer_is_not_remembered_and_a_closed_page_stops_watching(self):
        class P:
            def remembered(self):return False
        self.assertIsNone(fresh.start(P(),threading.Event(),lambda:None))
        stop=threading.Event();stop.set();drawn=[]
        class Q:
            def remembered(self):return True
        t=fresh.start(Q(),stop,lambda:drawn.append(1),step=.005);t.join(1);self.assertEqual(drawn,[])
    def test_the_pages_use_it(self):
        boot=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
        for name in ('sports_upcoming.py','sports_leagues.py','sports_live.py','sports.py'):
            self.assertIn('sports_fresh',(boot/name).read_text(),name)

class Service(unittest.TestCase):
    def test_the_service_keeps_espns_answer_fresh_and_the_refresh_buttons_are_gone(self):
        boot=Path(__file__).resolve().parents[1]/'migration/bundled-bootstrap'
        text=(boot/'service.py').read_text()
        self.assertIn('def sports_data_loop():',text);self.assertIn('threading.Thread(target=sports_data_loop,daemon=True).start()',text)
        self.assertIn("never competes with a video",text)
        for name in ('sports_page.py','sports_live_page.py','sports_upcoming_page.py','sports_leagues_page.py','sports_game_page.py'):
            self.assertNotIn('hdr_refresh.png',(boot/'resources/lib'/name).read_text(),name)
            self.assertNotIn('arrows-rotate.png',(boot/'resources/lib'/name).read_text(),name)

if __name__=='__main__':unittest.main()
