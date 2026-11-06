"""Runs the library tools' pages (library_tools_page.py draws them, library_tools.py says what they show).

open_queue      Library status › Waiting › Edit order
open_space      Library status › the Phone space card
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
    """The Queue page's content right now: requests not yet applied by the service show at once (as Library status)."""
    import debrid_drive
    import prepare_downloads
    now = time.time() if now is None else now
    state = prepare_downloads.apply_to(prepare_downloads.snapshot(profile), prepare_downloads.pending_requests(profile), now)
    view = prepare_downloads.library_view(state, now=lambda: now)
    return lt.queue_view(view, lt.debrid_jobs(debrid_drive.load(profile)), now)


def open_queue(profile=None):
    import xbmc
    import xbmcgui
    import prepare_downloads
    profile = profile or _profile()

    class Queue(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.stop = threading.Event()
            self.lock = threading.Lock()
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
                self.line = q['line']
                for k, v in lt.queue_properties(q).items():
                    self.setProperty(k, v)

        def onAction(self, action):
            if action.getId() in BACK:
                self.finish()

        def finish(self):
            self.stop.set()
            self.close()

        def onClick(self, control):
            if control == page.BACK:
                self.finish()
                return
            for base, action in ((page.UP, 'up'), (page.DOWN, 'down')):
                n = control - base
                if 1 <= n <= page.QUEUE_SLOTS and n <= len(self.line):
                    if self.line[n - 1].get(action):
                        prepare_downloads.request(profile, action, self.line[n - 1]['id'])
                        self.refresh()
                    return
    show(Queue, page.QUEUE)


def _elementum_paths(home):
    paths = []
    try:
        import xbmcaddon
        import xbmcvfs
        configured = xbmcaddon.Addon('plugin.video.elementum').getSetting('download_path')
        if configured:
            paths.append(xbmcvfs.translatePath(configured).rstrip('/'))
    except Exception:
        pass
    try:
        import updates
        paths.append(str(updates.updates_folder(home).with_name('Elementum Downloads')))
    except Exception:
        pass
    return paths


def _torrents():
    """Elementum's torrent list, or None when it did not answer (then nothing of Elementum's is cleared)."""
    try:
        import notices
        listed = notices.torrent_list()
        return listed if isinstance(listed, list) else None
    except Exception:
        return None


def open_space(profile=None):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import phone_space
    profile = profile or _profile()
    home = xbmcvfs.translatePath('special://home/')
    dialog = xbmcgui.Dialog()

    def places():
        try:
            app = xbmcvfs.translatePath('special://xbmc/')
        except Exception:
            app = ''
        return lt.space_places(profile, home, _elementum_paths(home), app)

    class Space(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.stop = threading.Event()
            self.measured = None
            self.show_numbers()
            self.measure()

        def measure(self):
            def run():
                try:
                    self.measured = lt.measure(places(), _torrents(), time.time())
                except Exception as error:
                    _log('phone space: %s' % error)
                    self.measured = {k: {'bytes': 0, 'clear': None} for k, *_ in lt.SPACE_KINDS}
                if not self.stop.is_set():
                    self.show_numbers()
            threading.Thread(target=run, daemon=True).start()

        def show_numbers(self):
            try:
                free = phone_space.free(profile)
            except OSError:
                free = None
            props, cumulative = lt.space_properties(self.measured, free)
            for k, v in props.items():
                self.setProperty(k, v)
            for n in range(1, page.SPACE_ROWS + 1):
                try:
                    self.getControl(page.BAR + n).setPercent(float(cumulative[n - 1]) if cumulative else 0.0)
                except Exception:
                    pass

        def onAction(self, action):
            if action.getId() in BACK:
                self.finish()

        def finish(self):
            self.stop.set()
            self.close()

        def onClick(self, control):
            if control == page.BACK:
                self.finish()
            elif page.CLEAR < control <= page.CLEAR + page.SPACE_ROWS and self.measured:
                key, name, _, _, _, can = lt.SPACE_KINDS[control - page.CLEAR - 1]
                found = self.measured.get(key) or {}
                if not can or not found.get('clear'):
                    return
                if not dialog.yesno('Phone space', 'Clear %s of %s?' % (lt.size_text(found['bytes']), name.lower()),
                                    nolabel='Cancel', yeslabel='Clear'):
                    return
                # Measured again just before deleting: what Elementum or Kodi started meanwhile is left alone.
                now = lt.measure(places(), _torrents(), time.time()).get(key) or {}
                freed = lt.clear(now.get('clear'), lambda: not self.stop.is_set())
                dialog.notification('Phone space', 'Cleared %s of %s' % (lt.size_text(freed), name.lower()), xbmcgui.NOTIFICATION_INFO, 2500)
                self.measured = None
                self.show_numbers()
                self.measure()
    show(Space, page.SPACE)


def open_history(profile=None):
    import xbmcgui
    import transfer_history as th
    profile = profile or _profile()

    class History(xbmcgui.WindowXMLDialog):
        def onInit(self):
            self.day = getattr(self, 'day', 'today')
            self.refresh()

        def refresh(self):
            now = time.time()
            h = lt.history_view(th.load(profile).get('finished') or [], th.failures(profile, now), now, self.day)
            for k, v in lt.history_properties(h, self.day).items():
                self.setProperty(k, v)

        def onAction(self, action):
            if action.getId() in BACK:
                self.close()

        def onClick(self, control):
            if control == page.BACK:
                self.close()
            elif page.DAY < control <= page.DAY + len(lt.DAYS):
                self.day = lt.DAYS[control - page.DAY - 1][0]
                self.refresh()
    show(History, page.HISTORY)


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


PAGES = {'queue': open_queue, 'space': open_space, 'history': open_history, 'airplay': open_airplay}


def run(args=()):
    name = (list(args) or ['queue'])[0]
    PAGES.get(name, open_queue)()
