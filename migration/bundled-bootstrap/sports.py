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
import sports_filter as sf  # noqa: E402
from sports_routes import available  # noqa: E402,F401  (the page tests and the tiles use it)

ROUTES = {sp.LIVE: 'sports_live', sp.UPCOMING: 'sports_upcoming', sp.LEAGUES: 'sports_leagues', sp.SEE_ALL: 'sports_upcoming'}
BACK_KEYS = (9, 10, 92, 110)
REFRESH_EVERY = 15   # seconds between the hub's own refreshes while it is open
ERROR = {'state': 'error', 'sub': 'Not updated', 'err.title': 'Can’t load sports right now',
         'err.text': 'The sports add-ons didn’t answer. Check the connection, then try again.', 'err.button': 'Try again'}


def sports_line(names):
    """'Football', 'Football and Hockey', 'Football, Basketball and 2 more' (sports in the app's order)."""
    names = sorted(set(names), key=lambda s: (sm.SPORT_ORDER.index(s) if s in sm.SPORT_ORDER else len(sm.SPORT_ORDER), s))
    if len(names) <= 1:
        return names[0] if names else ''
    if len(names) == 2:
        return '%s and %s' % tuple(names)
    return '%s, %s\nand %d more' % (names[0], names[1], len(names) - 2)   # explicit break: "1 / more" must not be split


def _lines(props, key, text, limit=0):
    """The tile's one detail line (the slim tiles of the owner's 2026-11-20 request have room for one; d2 stays empty)."""
    props[key + '.d1'] = str(text).replace('\n', ' ')
    props[key + '.d2'] = ''
    props[key + '.lines'] = '1'


def _next_game(start, now, offset):
    """('Next at 7:30 PM', '9 more today') or ('Next tomorrow', '8:15 PM') for the Upcoming tile's two lines."""
    day = sm.day_label(start, now, offset)
    if day == 'Today':
        return 'Next at %s' % sm.clock_text(start, offset), ''
    return 'Next %s' % (day.lower() if day == 'Tomorrow' else day), sm.clock_text(start, offset)


def props_for(overview, now, offset):
    """Every window property of a loaded page, from the provider's overview."""
    props = {'state': 'ok', 'sub': sm.updated_text(overview['updated'], now, offset),
             'live.title': 'Live Now', 'up.title': 'Upcoming', 'lg.title': 'Leagues',
             'edit.label': 'Edit', 'edit.on': ''}   # the Edit button's plain state; the page's thread sets the filtered one
    if overview.get('live'):
        props['live.mode'] = 'live'
        props['live.badge'] = '%d live' % overview['live']
        props['live.title'] = 'Live right now'
        props['live.detail'] = sports_line(overview.get('live_sports') or []).replace('\n', ' ')
    else:
        props['live.mode'] = 'idle'
        props['live.badge'] = ''
        props['live.title'] = 'Nothing live right now'
        text = ''
        if overview.get('next') is not None:
            day = sm.day_label(overview['next'], now, offset)
            when = '' if day == 'Today' else ' tomorrow' if day == 'Tomorrow' else ' ' + day
            text = 'Next game starts%s at %s.' % (when, sm.clock_text(overview['next'], offset))
        props['live.detail'] = text
    if overview.get('next') is None:
        _lines(props, 'up', 'No games coming up')
    else:
        total = overview.get('upcoming')
        if total:   # "59 games · 2 more today" (mockup A1)
            _lines(props, 'up', sm.count_text(total, 'game'))   # "157 games"; the day's count is on the page itself
        else:
            first, second = _next_game(overview['next'], now, offset)
            if not second and overview.get('more_today'):
                second = '%d more today' % overview['more_today']
            _lines(props, 'up', first)   # one short line; the Live now card already says when the next game starts
    _lines(props, 'lg', sm.count_text(overview.get('leagues') or 0, 'league'))
    return props


def next_props(games, now, offset, crests=None, count=sp.NEXT_ROWS):
    """The Up next rows: the next `count` games not yet started, in the Upcoming page's row shape (sports_rows: logos, short names, records, league tag, time)."""
    import sports_rows
    coming = sorted((g for g in games if g.get('state') == 'upcoming' and g['start'] >= now), key=lambda g: g['start'])[:count]
    props = {}
    for n in range(count):
        game = coming[n] if n < len(coming) else None
        pos = ('only' if len(coming) == 1 else 'first' if n == 0 else 'last' if n == len(coming) - 1 else 'mid') if game else ''
        row = sports_rows.row_props(game, now, offset, crests, pos)
        for key in sports_rows.KEYS:
            props['next.%d.%s' % (n, key)] = row.get(key, '')
    return props


def props_updating(last=None):
    """The same shape while the answer is on its way: the tiles stay, their small lines say so (approved board 7)."""
    props = dict(last or {})
    props.update({'state': 'ok', 'sub': 'Updating', 'live.title': 'Live Now', 'up.title': 'Upcoming', 'lg.title': 'Leagues',
                  'live.mode': props.get('live.mode') or 'idle', 'live.badge': '',
                  'live.title': props.get('live.title') or 'Checking what is on', 'live.detail': props.get('live.detail', '')})
    _lines(props, 'up', 'Checking games')
    _lines(props, 'lg', 'Checking leagues')
    return props


def load(provider, now=None, offset=None, refresh=False):
    """The properties for the page: refresh first when asked; no answer at all gives the can't-load state."""
    now = int(time.time()) if now is None else now
    offset = sm.device_offset(now) if offset is None else offset
    try:
        if refresh:
            provider.refresh()
        overview = provider.overview()
        try:
            overview['upcoming'] = len([g for g in provider.upcoming_games() if g['start'] >= now])   # the tile says "59 games"
        except Exception:
            pass
        return props_for(overview, now, offset)
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
            if hasattr(self, 'stop') and not self.stop.is_set():
                return
            self.guard = live_window.Guard(self)   # controls only while this page is open
            self.stop = threading.Event()
            self.last = {}
            self.show(props_updating())
            home = xbmcgui.Window(10000)
            initial_owner = home.getProperty('KodiIOS.SportsNativeOwner')
            def watch_handoff():
                while not self.stop.wait(.1):
                    owner = home.getProperty('KodiIOS.SportsNativeOwner')
                    if owner and owner != initial_owner:
                        self.finish()
                        return
            threading.Thread(target=watch_handoff, daemon=True).start()
            self.fetch(True)
            def refresh_loop():   # the hub keeps itself current: live count, next game, up next (owner: times must be live)
                import page_wait
                monitor = xbmc.Monitor()
                last = time.monotonic()
                while not page_wait.idle(self.stop, monitor, 1):
                    if time.monotonic() - last >= REFRESH_EVERY:
                        last = time.monotonic()
                        self.fetch(False)
            threading.Thread(target=refresh_loop, daemon=True).start()

        def show(self, props):
            for key, value in props.items():
                self.setProperty(key, value)

        def fetch(self, refresh):
            def work():
                try:
                    provider = sports_provider.get()
                    props = load(provider, refresh=refresh)
                    props.update(sf.edit_state(provider))
                    if props.get('state') == 'ok':
                        self.games = provider.upcoming_games()
                        props.update(next_props(self.games, time.time(), sm.device_offset(time.time()), getattr(self, 'logos', {})))
                    if props.get('state') == 'ok' and props.get('edit.summary'):   # "Showing NFL and NBA · Updated just now"
                        props['sub'] = '%s · %s' % (props['edit.summary'], props.get('sub', ''))
                except Exception as error:   # the page must never stay on "Updating"
                    log('could not load (%s)' % type(error).__name__)
                    props = dict(ERROR)
                if not self.stop.is_set():
                    if props.get('state') == 'ok':
                        self.last = props
                    self.show(props)
                    if props.get('state') == 'ok':   # the leagues' real logos: fetched once, kept on the phone; the rows draw first
                        try:
                            import sports_logos
                            import sports_rows
                            coming = sorted((g for g in self.games if g.get('state') == 'upcoming' and g['start'] >= time.time()), key=lambda g: g['start'])[:sp.NEXT_ROWS]
                            found = sports_logos.crests(xbmcvfs.translatePath('special://profile/'), sports_rows.crest_urls(coming))
                            if found and not self.stop.is_set():
                                self.logos = found
                                self.show(next_props(self.games, time.time(), sm.device_offset(time.time()), found))
                        except Exception as error:
                            log('crests (%s)' % type(error).__name__)
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
            elif control == sp.edit_button.ID:
                import sports_edit
                if sports_edit.run():
                    self.fetch(False)
            elif control in ROUTES:
                route = ROUTES[control]
                if available(route):
                    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,%s)' % route)
                else:
                    log('%s is not built yet' % route)
                    xbmcgui.Dialog().notification('Sports', 'That page is coming in an update.', xbmcgui.NOTIFICATION_INFO, 3000, False)
            elif sp.NEXT <= control < sp.NEXT + 4 * sp.NEXT_ROWS:   # an Up next row opens that game
                n = (control - sp.NEXT) // 4
                coming = sorted((g for g in getattr(self, 'games', []) if g.get('state') == 'upcoming' and g['start'] >= time.time()), key=lambda g: g['start'])
                if n < len(coming):
                    import sports_game
                    sports_game.run(coming[n], provider=sports_provider.get(), search=True)

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
    # No Crew window under the hub any more (owner, 2026-11-20: "no more Crew UI"): ESPN supplies the lists, and Crew's code runs only when a
    # game's page looks for its sources (sports_provider.crew_sources).
    try:
        page.doModal()
    finally:
        if hasattr(page, 'stop'):
            page.stop.set()
    del page


if __name__ == '__main__':
    run(sys.argv[1:])
