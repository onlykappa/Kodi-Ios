"""Runs the library tools' pages (library_tools_page.py draws them, library_tools.py says what they show).

open_queue      Library status › Waiting › Edit order
open_history    Transfers › History
open_airplay    Play on TV › Last time (landscape, over the video), or a tap on an AirPlay notification
Each page refreshes while it is open; every choice goes through the module that owns it (prepare_downloads.request for
the queue), never by writing another part's state. RunScript(service.kodi.ios.bootstrap,tool_pages,<page>) opens one.
"""
import os
import threading
import time

import library_tools as lt
import library_tools_page as page

BACK = (9, 10, 92, 110)
ADDON = 'service.kodi.ios.bootstrap'


def _here():
    """The bootstrap add-on's folder (the window files are looked up in its skin, as Library status does)."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def show(cls, xml, setup=None):
    """Construct and run one page. A window file added while Kodi runs is "missing" until Kodi lists the skin folder
    again (build 173): list it and try once more."""
    import xbmcvfs
    try:
        window = cls(xml, _here(), 'Default', '1080i')
    except RuntimeError:
        skin = xbmcvfs.translatePath('special://skin/')
        for folder in ('portrait', '1080i'):
            try:
                xbmcvfs.listdir(os.path.join(skin, folder) + '/')
            except Exception:
                pass
        window = cls(xml, _here(), 'Default', '1080i')
    if setup:
        setup(window)
    window.doModal()
    if hasattr(window, 'stop'):
        window.stop.set()
    del window


def _profile():
    import xbmcvfs
    return xbmcvfs.translatePath('special://profile/')


def _log(text):
    try:
        import xbmc
        xbmc.log('Kodi iOS library tools: %s' % text, xbmc.LOGWARNING)
    except Exception:
        pass


def queue_snapshot(profile, now=None):
    """The Queue page's metadata and published order; the service reflects requests in its next two-second snapshot."""
    import prepare_downloads
    now = time.time() if now is None else now
    import work_state
    model = work_state.current(profile, now)
    state = work_state.align(prepare_downloads.snapshot(profile), model)   # build 193: the status model
    state = prepare_downloads.apply_to(state, prepare_downloads.pending_requests(profile), now)
    view = prepare_downloads.library_view(state, now=lambda: now)
    import library_rows
    view=library_rows.with_model(view,model)
    return lt.queue_view(view, now=now)


def open_queue(profile=None):
    import xbmc
    import xbmcgui
    import prepare_downloads
    profile = profile or _profile()

    class Queue(xbmcgui.WindowXMLDialog):
        def onInit(self):
            import live_window
            self.guard = live_window.Guard(self)   # ISSUE-123: controls only while this page is open
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.offset=0
            self.line = []
            self.refresh()
            threading.Thread(target=self.loop, daemon=True).start()

        def loop(self):
            monitor = xbmc.Monitor()
            while not self.stop.is_set() and not monitor.waitForAbort(2):
                try:
                    self.refresh()
                except Exception as error:
                    _log('queue: %s' % error)

        def refresh(self):
            with self.lock:
                q = queue_snapshot(profile)
                # The existing page controls also page Drive jobs; none disappear beyond its three row slots.
                total=max(len(q['line']),((len(q['drive'])+page.DRIVE_SLOTS-1)//page.DRIVE_SLOTS)*page.QUEUE_SLOTS)
                self.offset=min(self.offset,max(0,(total-1)//page.QUEUE_SLOTS*page.QUEUE_SLOTS))
                self.line = q['line'][self.offset:self.offset+page.QUEUE_SLOTS]
                self.setProperty('pages','true' if total>page.QUEUE_SLOTS else '')
                self.setProperty('page.previous','true' if self.offset else '')
                self.setProperty('page.more','true' if self.offset+page.QUEUE_SLOTS<total else '')
                drive_offset=(self.offset//page.QUEUE_SLOTS)*page.DRIVE_SLOTS
                q=dict(q,line=self.line,drive=q['drive'][drive_offset:drive_offset+page.DRIVE_SLOTS])
                props = lt.queue_properties(q)
                for k, v in props.items():
                    self.setProperty(k, v)
                # Kodi cannot size a progress bar from a window property; set it only while the page is open.
                self.guard.percent(page.QBAR, props.get('now.pct') or 0)

        def onAction(self, action):
            if action.getId() in BACK:
                self.finish()

        def finish(self):
            self.stop.set()
            self.guard.close()

        def onClick(self, control):
            if control == page.BACK:
                self.finish()
                return
            if control in (page.QPREV,page.QNEXT):
                self.offset=max(0,self.offset+(page.QUEUE_SLOTS if control==page.QNEXT else -page.QUEUE_SLOTS));self.refresh();return
            for base, action in ((page.UP, 'up'), (page.DOWN, 'down')):
                n = control - base
                if 1 <= n <= page.QUEUE_SLOTS and n <= len(self.line):
                    if self.line[n - 1].get(action):
                        prepare_downloads.request(profile, action, self.line[n - 1]['id'])
                        self.refresh()
                    return
    show(Queue, page.QUEUE)


def open_history(profile=None):
    import xbmc
    import xbmcgui
    import transfer_history as th
    profile = profile or _profile()

    class History(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.offset=0
            self.day = getattr(self, 'day', 'today')
            self.stop=threading.Event()
            self.refresh()
            threading.Thread(target=self.loop,daemon=True).start()

        def loop(self):
            monitor=xbmc.Monitor()
            while not self.stop.is_set() and not monitor.waitForAbort(2):
                try:self.refresh()
                except Exception as error:_log('history: %s'%error)

        def refresh(self):
            now = time.time()
            h = lt.history_view(th.load(profile).get('finished') or [], th.failures(profile, now), now, self.day)
            total=len(h['rows'])
            self.offset=min(self.offset,max(0,(total-1)//page.HISTORY_SLOTS*page.HISTORY_SLOTS))
            self.setProperty('pages','true' if total>page.HISTORY_SLOTS else '')
            h=dict(h,rows=h['rows'][self.offset:self.offset+page.HISTORY_SLOTS])
            self.entries=h['rows']
            for entry in self.entries:
                entry['retry']=retry_target(profile,entry)
            for k, v in lt.history_properties(h, self.day).items():
                self.setProperty(k, v)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == page.BACK:
                self.close()
            elif control in (page.HPREV,page.HNEXT):
                self.offset=max(0,self.offset+(page.HISTORY_SLOTS if control==page.HNEXT else -page.HISTORY_SLOTS));self.refresh()
            elif page.RETRY < control <= page.RETRY + page.HISTORY_SLOTS:
                n=control-page.RETRY-1
                if n<len(self.entries) and self.entries[n].get('retry'):
                    retry_history(profile,self.entries[n]['retry']);self.refresh()
            elif page.DAY < control <= page.DAY + len(lt.DAYS):
                self.offset=0
                self.day = lt.DAYS[control - page.DAY - 1][0]
                self.refresh()
    show(History, page.HISTORY)


def retry_target(profile, entry):
    """Resolve a unique owning job. Ambiguous legacy titles must never retry another copy."""
    if entry.get('tone')=='ok':return None
    import prepare_downloads as prep
    import debrid_drive
    import drivelibrary
    if entry.get('kind')=='conv':
        matches=[j for j in (prep.load(profile).get('jobs') or {}).values()
                 if (j.get('source') or {}).get('id') and
                 drivelibrary.display_title(j['source'].get('name',''))==entry.get('title')]
        ids={j['source']['id'] for j in matches}
        stopped=any(j.get('blocked') and j.get('repack_failed') for j in matches)
        return ('conv',matches[0]['source']['id']) if len(ids)==1 and not stopped else None
    if entry.get('kind')=='up':
        matches=[j for j in debrid_drive.load(profile).get('jobs') or [] if j.get('status')=='failed' and
                 (j.get('title') or drivelibrary.display_title(j.get('name','')))==entry.get('title')]
        ids={(j['hash'],j.get('episode','')) for j in matches}
        return ('up',matches[-1]) if len(ids)==1 else None
    return None


def retry_history(profile, target):
    import prepare_downloads as prep
    import debrid_drive
    if target[0]=='conv':prep.request(profile,'retry',target[1])
    else:
        j=target[1]
        debrid_drive.queue(profile,{'id':j['hash'],'name':j['name']},j['kind'],j.get('title',''),j.get('season',''),j.get('episode',''),episodes=j.get('episodes') or [])


def airplay_properties(profile, now=None):
    import cast
    now = time.time() if now is None else now
    return lt.airplay_properties(lt.airplay_steps(lt.load_airplay(profile), cast.player_problem), now)


def open_airplay(profile=None):
    import xbmcgui
    profile = profile or _profile()

    class Check(xbmcgui.WindowXMLDialog):
        def onInit(self):
            for k, v in airplay_properties(profile).items():
                self.setProperty(k, v)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control in (page.BACK, page.CLOSE, 9099):
                self.close()
    show(Check, page.AIRPLAY)


PAGES = {'queue': open_queue, 'history': open_history, 'airplay': open_airplay}


def run(args=()):
    name = (list(args) or ['queue'])[0]
    PAGES.get(name, open_queue)()
