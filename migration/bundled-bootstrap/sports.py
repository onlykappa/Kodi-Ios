"""Library › Sports: the landing page (DEC-054, DEC-057; sports_page.py draws it, approved board 2).

The page opens at once (the tiles with "Checking…" lines), asks the provider for the overview in a thread and fills the tiles;
the refresh button asks again; no add-on answering shows "Can't load sports right now" with one Try again button. The tiles open
Live Now, Upcoming and Leagues. A page that is not built yet is never started: an unknown RunScript name would run the recovery
script, so the tile says it is coming instead.
"""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import sports_model as sm  # noqa: E402
import sports_page as sp  # noqa: E402
from sports_routes import available  # noqa: E402,F401  (the page tests and the tiles use it)

ROUTES = {sp.LIVE: 'sports_live', sp.UPCOMING: 'sports_upcoming', sp.LEAGUES: 'sports_leagues'}
BACK_KEYS = (9, 10, 92, 110)
ERROR = {'state': 'error', 'sub': 'Not updated', 'err.title': 'Can’t load sports right now',
         'err.text': 'The sports add-ons didn’t answer. Check the connection, then try again.', 'err.button': 'Try again'}


def sports_line(names):
    """'Football', 'Football and Hockey', 'Football, Basketball and 2 more' (sports in the app's order)."""
    names = sorted(set(names), key=lambda s: (sm.SPORT_ORDER.index(s) if s in sm.SPORT_ORDER else len(sm.SPORT_ORDER), s))
    if len(names) <= 1:
        return names[0] if names else ''
    if len(names) == 2:
        return '%s and %s' % tuple(names)
    return '%s, %s and %d more' % (names[0], names[1], len(names) - 2)


def _lines(props, key, text, limit):
    lines = sp.split_lines(text, limit) or ['']
    props[key + '.d1'] = lines[0]
    props[key + '.d2'] = lines[1] if len(lines) > 1 else ''
    props[key + '.lines'] = str(len(lines))


def _next_game(start, now, offset):
    """('Next at 7:30 PM', '9 more today') or ('Next tomorrow', '8:15 PM') for the Upcoming tile's two lines."""
    day = sm.day_label(start, now, offset)
    if day == 'Today':
        return 'Next at %s' % sm.clock_text(start, offset), ''
    return 'Next %s' % (day.lower() if day == 'Tomorrow' else day), sm.clock_text(start, offset)


def props_for(overview, now, offset):
    """Every window property of a loaded page, from the provider's overview."""
    props = {'state': 'ok', 'sub': sm.updated_text(overview['updated'], now, offset),
             'live.title': 'Live Now', 'up.title': 'Upcoming', 'lg.title': 'Leagues'}
    if overview.get('live'):
        props['live.mode'] = 'live'
        props['live.badge'] = '%d live' % overview['live']
        _lines(props, 'live', sports_line(overview.get('live_sports') or []), sp.FIT_BIG)
    else:
        props['live.mode'] = 'idle'
        props['live.badge'] = ''
        text = 'Nothing live right now.'
        if overview.get('next') is not None:
            day = sm.day_label(overview['next'], now, offset)
            when = '' if day == 'Today' else ' tomorrow' if day == 'Tomorrow' else ' ' + day
            text += ' Next game starts%s at %s.' % (when, sm.clock_text(overview['next'], offset))
        _lines(props, 'live', text, sp.FIT_BIG)
    if overview.get('next') is None:
        props['up.d1'], props['up.d2'], props['up.lines'] = 'No games', 'coming up', '2'   # not "No games coming / up"
    else:
        first, second = _next_game(overview['next'], now, offset)
        if not second and overview.get('more_today'):
            second = '%d more today' % overview['more_today']
        props['up.d1'], props['up.d2'] = first, second
        props['up.lines'] = '2' if second else '1'
    _lines(props, 'lg', sm.count_text(overview.get('leagues') or 0, 'league'), sp.FIT_HALF)
    props['fin'] = '%d replays' % overview['finished_today'] if overview.get('finished_today') else ''
    return props


def props_updating(last=None):
    """The same shape while the answer is on its way: the tiles stay, their small lines say so (approved board 7)."""
    props = dict(last or {})
    props.update({'state': 'ok', 'sub': 'Updating', 'live.title': 'Live Now', 'up.title': 'Upcoming', 'lg.title': 'Leagues',
                  'live.mode': props.get('live.mode') or 'live', 'live.badge': ''})
    _lines(props, 'live', 'Checking what is on', sp.FIT_BIG)
    _lines(props, 'up', 'Checking today’s games', sp.FIT_HALF)
    _lines(props, 'lg', 'Checking leagues', sp.FIT_HALF)
    props.setdefault('fin', '')
    return props


def load(provider, now=None, offset=None, refresh=False):
    """The properties for the page: refresh first when asked; no answer at all gives the can't-load state."""
    now = int(time.time()) if now is None else now
    offset = sm.device_offset(now) if offset is None else offset
    try:
        if refresh:
            provider.refresh()
        return props_for(provider.overview(), now, offset)
    except sm.SportsUnavailable:
        return dict(ERROR)


def run(args=()):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import sports_provider
    log = lambda message: xbmc.log('Kodi iOS Sports: ' + message, xbmc.LOGINFO)

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            import live_window
            self.guard = live_window.Guard(self)   # controls only while this page is open
            self.stop = threading.Event()
            self.last = {}
            self.show(props_updating())
            self.fetch(False)

        def show(self, props):
            for key, value in props.items():
                self.setProperty(key, value)

        def fetch(self, refresh):
            def work():
                try:
                    props = load(sports_provider.get(), refresh=refresh)
                except Exception as error:   # the page must never stay on "Updating"
                    log('could not load (%s)' % type(error).__name__)
                    props = dict(ERROR)
                if not self.stop.is_set():
                    if props.get('state') == 'ok':
                        self.last = props
                    self.show(props)
            if refresh:
                self.show(props_updating(self.last))
            threading.Thread(target=work, daemon=True).start()

        def onAction(self, action):
            if action.getId() in BACK_KEYS:
                self.finish()

        def onClick(self, control):
            if control == sp.BACK:
                self.finish()
            elif control in (sp.REFRESH, sp.RETRY):
                self.fetch(True)
            elif control in ROUTES:
                route = ROUTES[control]
                if available(route):
                    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,%s)' % route)
                else:
                    log('%s is not built yet' % route)
                    xbmcgui.Dialog().notification('Sports', 'That page is coming in an update.', xbmcgui.NOTIFICATION_INFO, 3000, False)
            elif control == sp.FINISHED:
                xbmcgui.Dialog().notification('Sports', 'Finished games are coming in an update.', xbmcgui.NOTIFICATION_INFO, 3000, False)

        def finish(self):
            self.stop.set()
            self.guard.close()

    here = HERE
    skin = xbmcvfs.translatePath('special://skin/')
    try:
        page = Page(sp.WINDOW, here, 'Default', '1080i')
    except RuntimeError:
        # Written while Kodi was running: its directory cache may not list it yet (build 173). Re-read and try once more.
        xbmcvfs.listdir(os.path.join(skin, 'portrait') + '/')
        page = Page(sp.WINDOW, here, 'Default', '1080i')
    page.doModal()
    if hasattr(page, 'stop'):
        page.stop.set()
    del page


if __name__ == '__main__':
    run(sys.argv[1:])
