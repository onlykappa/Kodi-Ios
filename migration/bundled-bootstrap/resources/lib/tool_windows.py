"""Runs the library tools' pages (library_tools_page.py draws them, library_tools.py says what they show).

open_queue      Library status › Waiting › Edit order
open_history    Transfers › History
open_airplay    Play on TV › Last time (landscape, over the video), or a tap on an AirPlay notification
Each page refreshes while it is open; every choice goes through the module that owns it (prepare_downloads.request for
the queue), never by writing another part's state. RunScript(service.kodi.ios.bootstrap,tool_pages,<page>) opens one.
"""
import page_wait
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
        import diagnostics
        xbmc.log('Kodi iOS library tools: %s' % diagnostics.redact(text, 400), xbmc.LOGWARNING)
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

    import queue_page as qp
    import transfer_artwork
    import drivelibrary
    import work_state
    art = drivelibrary.load_json(transfer_artwork.cache_path(profile), {})

    def poster(name):
        try:
            return transfer_artwork.describe(name, art)['poster'] if name else ''
        except Exception:
            return ''

    class Queue(xbmcgui.WindowXMLDialog):
        """DEC-045 board E: one scrolling list; Edit turns on – / lines in the same window."""
        def onInit(self):
            import live_window
            self.guard = live_window.Guard(self)   # ISSUE-123: controls only while this page is open
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.editing = False
            self.view = {'drive': [], 'prep': []}
            self.refresh()
            threading.Thread(target=self.loop, daemon=True).start()

        def loop(self):
            monitor = xbmc.Monitor()
            while not page_wait.idle(self.stop, monitor, 2):
                try:
                    self.refresh()
                except Exception as error:
                    _log('queue: %s' % error)

        def refresh(self):
            with self.lock:
                q = queue_snapshot(profile)
                model = work_state.current(profile)
                self.view = v = lt.queue_page_view(model, q['line'])
                props = {'edit.label': 'Done' if self.editing else 'Edit', 'editing': 'true' if self.editing else '',
                         'drive.head': ('DOWNLOADING TO GOOGLE DRIVE · %d' % len(v['drive'])) if v['drive'] else '',
                         'prep.head': ('PREPARING FOR KODI AND AIRPLAY · %d' % len(v['prep'])) if v['prep'] else '',
                         'cancelall': 'true' if any(r['hash'] for r in v['drive']) else '',
                         'empty': '' if v['drive'] or v['prep'] else 'Nothing is waiting.',
                         'more': ('and %d more' % (len(v['prep']) - qp.PREP_SLOTS)) if len(v['prep']) > qp.PREP_SLOTS else '',
                         'foot': ('Tap the lines on the right to move a video. – keeps a video as it is (it still plays on this '
                                  'iPhone); Library status can prepare it later.') if self.editing and v['prep'] else ''}
                for group, slots, bars in (('drive', qp.DRIVE_SLOTS, qp.DRIVE_BARS), ('prep', qp.PREP_SLOTS, qp.PREP_BARS)):
                    rows = v[group][:slots]
                    for n in range(slots):
                        r = rows[n] if n < len(rows) else {}
                        k = '%s.%d.' % (group, n)
                        props.update({k + 'title': r.get('title', ''), k + 'sub': r.get('sub', ''), k + 'pct': r.get('pct', ''),
                                      k + 'tint': ('FF0A84FF' if group == 'drive' else 'FFBF5AF2'),
                                      k + 'removable': 'true' if r.get('removable') else '', k + 'movable': 'true' if r.get('movable') else '',
                                      k + 'poster': poster(r.get('name') or r.get('title')),
                                      k + 'pos': ('only' if len(rows) == 1 else 'first' if n == 0 else 'last' if n == len(rows) - 1 else 'mid') if r else ''})
                        if r.get('pct'):
                            self.guard.percent(bars + n, r.get('bar') or 0)
                for key, value in props.items():
                    if self.getProperty(key) != value:
                        self.setProperty(key, value)

        def onAction(self, action):
            if action.getId() in BACK:
                self.finish()

        def finish(self):
            self.stop.set()
            self.guard.close()

        def remove(self, group, r):
            import xbmcgui
            dialog = xbmcgui.Dialog()
            if group == 'drive':
                if r['kind'] == 'down':
                    if dialog.yesno('Cancel download', 'Stop downloading %s and delete what has downloaded so far?' % r['title'],
                                    nolabel='Keep', yeslabel='Stop'):
                        import notices
                        notices.engine_action('cancel', r['id'])
                elif r['hash'] and dialog.yesno('Cancel download', 'Stop copying %s from AllDebrid to Google Drive? What has been '
                                                'copied so far is dropped.' % r['title'], nolabel='Keep', yeslabel='Stop'):
                    import transfer_control
                    transfer_control.cancel_copy(profile, r['hash'])
                return
            words = ('Stop converting %s? It stays in your library as it is and plays on this iPhone. Library status can '
                     'convert it later for Play on TV.' if r['moving'] else
                     '%s is kept as it is: it plays on this iPhone, and Library status can prepare it later.') % r['title']
            if dialog.yesno('Stop converting' if r['moving'] else 'Keep as it is?', words, nolabel='Cancel',
                            yeslabel='Stop' if r['moving'] else 'Keep As It Is'):
                prepare_downloads.request(profile, 'keep', r['id'])

        def onClick(self, control):
            import xbmcgui
            v = self.view
            if control == qp.BACK:
                self.finish()
                return
            if control == qp.EDIT:
                self.editing = not self.editing
            elif control == qp.CANCEL_ALL:
                import transfer_control
                n = len(transfer_control.unfinished_copies(profile))
                if xbmcgui.Dialog().yesno('Cancel all downloads', 'Stop the copy running now and remove all %d downloads to Google Drive '
                                          'from the queue? Videos already on Google Drive stay.' % n, nolabel='Keep', yeslabel='Remove All'):
                    xbmcgui.Dialog().notification('Kodi iOS', '%d downloads cancelled' % transfer_control.cancel_all_copies(profile),
                                                  xbmcgui.NOTIFICATION_INFO, 3000)
            elif qp.DRIVE_MINUS <= control < qp.DRIVE_MINUS + qp.DRIVE_SLOTS and control - qp.DRIVE_MINUS < len(v['drive']):
                self.remove('drive', v['drive'][control - qp.DRIVE_MINUS])
            elif qp.PREP_MINUS <= control < qp.PREP_MINUS + qp.PREP_SLOTS and control - qp.PREP_MINUS < len(v['prep']):
                self.remove('prep', v['prep'][control - qp.PREP_MINUS])
            elif qp.PREP_MOVE <= control < qp.PREP_MOVE + qp.PREP_SLOTS and control - qp.PREP_MOVE < len(v['prep']):
                r = v['prep'][control - qp.PREP_MOVE]
                pick = xbmcgui.Dialog().contextmenu(['Move to Top', 'Move Up', 'Move Down'])
                if pick < 0:
                    return
                prepare_downloads.request(profile, ('next', 'up', 'down')[pick], r['id'])
            elif qp.PREP_ROW <= control < qp.PREP_ROW + qp.PREP_SLOTS and control - qp.PREP_ROW < len(v['prep']):
                r = v['prep'][control - qp.PREP_ROW]
                labels = (['Prepare Next'] if r['movable'] else []) + ['Keep as It Is' if not r['moving'] else 'Stop Converting']
                pick = xbmcgui.Dialog().contextmenu(labels)
                if pick < 0:
                    return
                if labels[pick] == 'Prepare Next':
                    prepare_downloads.request(profile, 'next', r['id'])
                else:
                    self.remove('prep', r)
            elif qp.DRIVE_ROW <= control < qp.DRIVE_ROW + qp.DRIVE_SLOTS and control - qp.DRIVE_ROW < len(v['drive']):
                r = v['drive'][control - qp.DRIVE_ROW]
                if r['removable']:
                    self.remove('drive', r)
                return
            else:
                return
            self.refresh()
    show(Queue, qp.WINDOW)


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
            while not page_wait.idle(self.stop,monitor,2):
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
