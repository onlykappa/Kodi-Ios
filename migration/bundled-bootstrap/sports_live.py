"""Sports › Live Now (DEC-055, DEC-057; sports_live_page.py draws it, approved boards 6-9, option B).

Shows every live game, the one closest to its end first, with its league label, teams, score, clock and its sources under it (best
first); a tap on a source plays it at once. The league chips filter the list. The page opens at once, asks the provider in a thread,
refreshes by itself every 30 seconds and on the refresh button; no add-on answering shows "Can't load live games right now".
"""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import sports_live_page as lp  # noqa: E402
import sports_model as sm  # noqa: E402

BACK_KEYS = (9, 10, 92, 110)
EVERY = 30   # seconds between automatic refreshes while the page is open (a fresh score batch, about every 8 s, refreshes it sooner)
LAST = {}    # the games of the last load by id: the page's one-second clock tick reads them
ERROR = {'state': 'error', 'sub': 'Not updated', 'err.title': 'Can’t load live games right now',
         'err.text': 'The sports add-ons didn’t answer. Check the connection, then try again.', 'err.button': 'Try again'}


def mono(addon):
    """'The Loop' -> 'TL', 'Loop TV' -> 'LT', 'Sports Hub' -> 'SH'."""
    words = [w for w in str(addon or '').split() if w]
    return (''.join(w[0] for w in words[:2]) if len(words) > 1 else str(addon or '')[:2]).upper()


def also_text(names):
    """'' | 'Also on Loop TV' | 'Also on Loop TV, Sports Hub' | 'Also on 3 add-ons' (one line: it never wraps under the play button)."""
    names = [n for n in names or [] if n]
    if not names:
        return ''
    if len(names) <= 2:
        return 'Also on ' + ', '.join(names)
    return 'Also on %d add-ons' % len(names)


def _empty_game(g):
    props = {}
    for k in ('id', 'league', 'clock', 'score'):
        props['g.%d.%s' % (g, k)] = ''
    for t in 'ah':
        for k in ('name', 'crest'):
            props['g.%d.%s.%s' % (g, t, k)] = ''
    return props


def game_props(g, game):
    """The properties of card number g (1-based) for a game of the contract: what the big card draws (option B, owner 2026-11-20)."""
    props = _empty_game(g)
    away, home = game['away'], game['home']
    props['g.%d.league' % g] = game.get('league') or ''
    props['g.%d.clock' % g] = sm.live_clock(game, time.time()) if game.get('state') == 'live' else game.get('clock') or ''
    props['g.%d.id' % g] = game.get('id') or ''
    for t, team in (('a', away), ('h', home)):
        props.update({'g.%d.%s.name' % (g, t): team.get('name') or '', 'g.%d.%s.crest' % (g, t): team.get('crest') or ''})
    a, h = away.get('score'), home.get('score')
    props['g.%d.score' % g] = '%s – %s' % (a, h) if a is not None and h is not None else ''   # the big score in the middle of the card
    return props


def with_crests(props, profile, get=None):
    """The cards' team crests as the phone's own copies (sports_logos.crests): a team whose logo cannot be had shows an empty ring, never letters.
    `get` is the download (tests replace it); outside Kodi, with no profile folder, the crest addresses are dropped (nothing is drawn for them)."""
    import sports_logos
    urls = [props.get('g.%d.%s.crest' % (g, t)) or '' for g in range(1, lp.GAMES + 1) for t in 'ah']
    found = sports_logos.crests(profile, urls, get) if get is not None else sports_logos.crests(profile, urls)
    for g in range(1, lp.GAMES + 1):
        for t in 'ah':
            key = 'g.%d.%s.crest' % (g, t)
            if key in props:
                props[key] = found.get(props[key], '')
    return props


def _chips(codes, chosen):
    codes = codes[:lp.CHIPS]
    props = {}
    for n in range(lp.CHIPS):
        props['chip.%d' % n] = codes[n] if n < len(codes) else ''
        props['chip.%d.on' % n] = 'true' if n < len(codes) and codes[n] == chosen else ''
    props['chips.rows'] = str(max(1, -(-len(codes) // lp.CHIPS_PER_ROW))) if len(codes) > 1 else '0'
    return props


def sub_text(count, updated):
    """'4 games on now · updated just now' (the board: the second half in lower case)."""
    return '%s on now · %s' % (sm.count_text(count, 'game'), updated[0].lower() + updated[1:])


def props_for(games, chosen, upcoming, now, offset, updated):
    """Every window property of a loaded page. games: the provider's live games (already closest-to-ending first); upcoming: its
    upcoming games (for the nothing-live text); chosen: 'All' or a league code; updated: the overview's time."""
    codes = sm.league_codes(games)
    if chosen not in codes:
        chosen = 'All'
    shown = sm.filter_league(games, None if chosen == 'All' else chosen)
    props = {'state': 'ok', 'none.title': '', 'none.text': '', 'none.button': '', 'more': ''}
    if not games:
        props['state'] = 'none'
        props['sub'] = sm.updated_text(updated, now, offset)
        props.update({'none.title': 'No games live right now', 'none.button': 'See Upcoming'})
        nxt = min((g['start'] for g in upcoming or [] if g['start'] >= now), default=None)
        if nxt is not None:
            day = sm.day_label(nxt, now, offset)
            when = '' if day == 'Today' else ' tomorrow' if day == 'Tomorrow' else ' ' + day
            props['none.text'] = 'The next game starts%s at %s.' % (when, sm.clock_text(nxt, offset))
        else:
            props['none.text'] = 'Nothing is scheduled yet.'
        props.update(_chips([], 'All'))
        for g in range(1, lp.GAMES + 1):
            props.update(_empty_game(g))
        return props, chosen
    props['sub'] = sub_text(len(shown), sm.updated_text(updated, now, offset))
    props.update(_chips(codes, chosen))
    for g in range(1, lp.GAMES + 1):
        props.update(game_props(g, shown[g - 1]) if g <= len(shown) else _empty_game(g))
    extra = len(shown) - lp.GAMES
    if extra > 0:
        props['more'] = '%s not shown. Pick a league above to narrow the list.' % sm.count_text(extra, 'more game')
    return props, chosen


def slots_for(games, chosen):
    """{(card, source): source dict} of what is on screen, so a tap on a play button finds its source."""
    shown = sm.filter_league(games, None if chosen == 'All' else chosen)[:lp.GAMES]
    return {(g, s): src for g, game in enumerate(shown, 1) for s, src in enumerate((game.get('sources') or [])[:lp.SOURCES], 1)}


def load(provider, chosen='All', now=None, offset=None, refresh=False):
    """(properties, chosen league, on-screen sources). No answer at all gives the can't-load state."""
    now = int(time.time()) if now is None else now
    offset = sm.device_offset(now) if offset is None else offset
    try:
        if refresh:
            provider.refresh()
        games = provider.live_games()
        updated = provider.overview().get('updated', now)
        upcoming = [] if games else provider.upcoming_games()
    except sm.SportsUnavailable:
        return dict(ERROR), chosen, {}
    props, chosen = props_for(games, chosen, upcoming, now, offset, updated)
    LAST.clear()
    LAST.update({g.get('id'): g for g in games})
    return props, chosen, slots_for(games, chosen)


def control_target(control):
    """('chip', n) | ('source', card, source) | None for a control id of the page."""
    for rows in (1, 2, 3):
        if lp.chip_id(rows, 0) <= control < lp.chip_id(rows, 0) + lp.CHIP_IDS:
            return ('chip', control - lp.chip_id(rows, 0))
    for offset in (0, lp.ALSO_IDS):
        local = control - lp.PLAY0 - offset
        if 0 <= local < lp.GAMES * 10 and local % 10 < lp.SOURCES:
            return ('source', local // 10 + 1, local % 10 + 1)
    if lp.SEARCH0 <= control < lp.SEARCH0 + lp.GAMES:
        return ('search', control - lp.SEARCH0 + 1)
    if lp.CARD0 <= control < lp.CARD0 + lp.GAMES:   # a tap on a game's team area opens its page (sources are looked for on open)
        return ('search', control - lp.CARD0 + 1)
    return None


def play_source(source, provider, finish, xbmc, notify, log):
    """Close the Sports modal stack before dispatching a native source."""
    pending = []
    try:
        path = provider.play(source, log, launch=lambda *args: pending.append(args))
    except Exception as error:
        log('live source handoff failed (%s)' % type(error).__name__)
        notify()
        return
    if pending:
        finish()
        xbmc.executebuiltin('Dialog.Close(all,true)')
        def handoff():
            xbmc.sleep(250)
            try:
                import sports_jet
                for args in pending:
                    sports_jet._launch(*args)
            except Exception as error:
                log('live source dispatch failed (%s)' % type(error).__name__)
                notify()
        threading.Thread(target=handoff, daemon=True).start()
    elif isinstance(path, str) and path and not path.startswith('sample://'):
        xbmc.Player().play(path)


def watch_handoff(stop, home, initial_owner, finish):
    """Stop the Live Now page when a child hands control to native playback."""
    while not stop.wait(.1):
        owner = home.getProperty('KodiIOS.SportsNativeOwner')
        if owner and owner != initial_owner:
            finish()
            return


def run(args=()):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import sports_provider
    import sports_routes
    log = lambda message: xbmc.log('Kodi iOS Sports: ' + message, xbmc.LOGINFO)

    class Page(xbmcgui.WindowXMLDialog):
        def onInit(self):
            import live_window
            if hasattr(self, 'stop') and not self.stop.is_set():
                return
            self.guard = live_window.Guard(self)
            self.stop = threading.Event()
            home = xbmcgui.Window(10000)
            initial_owner = home.getProperty('KodiIOS.SportsNativeOwner')
            threading.Thread(target=watch_handoff,args=(self.stop,home,initial_owner,self.finish),daemon=True).start()
            self.chosen, self.codes, self.slots, self.busy = (args[0] if args else 'All'), [], {}, threading.Lock()   # a league page starts on its chip
            self.setProperty('sub', 'Updating')
            self.fetch(False)
            threading.Thread(target=self.loop, daemon=True).start()

        def loop(self):
            import page_wait
            monitor = xbmc.Monitor()
            last, revision = time.monotonic(), 0
            while not page_wait.idle(self.stop, monitor, 1):
                provider = sports_provider.get()
                current = getattr(provider, 'score_revision', lambda: 0)()
                if current and current != revision:
                    revision = current
                    self.fetch(False, quiet=True)
                if time.monotonic() - last >= EVERY:
                    last = time.monotonic()
                    self.fetch(False, quiet=True)
                self.tick_clocks()

        def tick_clocks(self):
            """Every second: each card's game clock counted on from the last ESPN answer (only a changed clock is written)."""
            now = time.time()
            for n in range(1, lp.GAMES + 1):
                game = LAST.get(self.getProperty('g.%d.id' % n))
                if game and game.get('state') == 'live':
                    text = sm.live_clock(game, now)
                    if text and self.getProperty('g.%d.clock' % n) != text:
                        self.setProperty('g.%d.clock' % n, text)

        def show(self, props):
            for key, value in props.items():
                if self.getProperty(key) != value:
                    self.setProperty(key, value)

        def fetch(self, refresh, quiet=False):
            def work():
                with self.busy:
                    try:
                        props, chosen, slots = load(sports_provider.get(), self.chosen, refresh=refresh)
                        try:
                            import xbmcvfs
                            props = with_crests(props, xbmcvfs.translatePath('special://profile/'))   # real logos, kept on the phone
                        except Exception as error:
                            log('live crests (%s)' % type(error).__name__)
                    except Exception as error:   # the page must never stay on "Updating"
                        log('live now could not load (%s)' % type(error).__name__)
                        props, chosen, slots = dict(ERROR), self.chosen, {}
                    if not self.stop.is_set():
                        self.chosen, self.slots = chosen, slots
                        self.show(props)
            if refresh and not quiet:
                self.setProperty('sub', 'Updating')
            threading.Thread(target=work, daemon=True).start()

        def onAction(self, action):
            if action.getId() in BACK_KEYS:
                self.finish()

        def onClick(self, control):
            if control == lp.BACK:
                self.finish()
            elif control in (lp.REFRESH, lp.RETRY):
                self.fetch(True)
            elif control == lp.SEE_UPCOMING:
                if sports_routes.available('sports_upcoming'):
                    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,sports_upcoming)')
                else:
                    xbmcgui.Dialog().notification('Sports', 'That page is coming in an update.', xbmcgui.NOTIFICATION_INFO, 3000, False)
            else:
                target = control_target(control)
                if target and target[0] == 'chip':
                    code = self.getProperty('chip.%d' % target[1])
                    if code:
                        self.chosen = code
                        self.fetch(False, quiet=True)
                elif target and target[0] == 'source' and (target[1], target[2]) in self.slots:
                    play_source(self.slots[(target[1], target[2])], sports_provider, self.finish, xbmc,
                                lambda: xbmcgui.Dialog().notification('Sports', "Can't open the player right now. Try again.", xbmcgui.NOTIFICATION_WARNING, 4000), log)
                elif target and target[0] == 'search':
                    game_id = self.getProperty('g.%d.id' % target[1])
                    try:
                        provider = sports_provider.get()
                        game = provider.game(game_id) if game_id else None
                        if not game or game.get('state') != 'live':
                            raise sm.SportsUnavailable('game is no longer live')
                        import sports_game
                        sports_game.run(game, provider=provider, search=True)
                    except Exception as error:
                        log('live game search could not open (%s)' % type(error).__name__)
                        xbmcgui.Dialog().notification('Sports', "Can't search for this game right now. Try again.", xbmcgui.NOTIFICATION_WARNING, 4000)

        def finish(self):
            self.stop.set()
            self.guard.close()

    skin = xbmcvfs.translatePath('special://skin/')
    try:
        page = Page(lp.WINDOW, HERE, 'Default', '1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(skin, 'portrait') + '/')   # written while Kodi was running: its directory cache may not list it yet
        page = Page(lp.WINDOW, HERE, 'Default', '1080i')
    page.doModal()
    if hasattr(page, 'stop'):
        page.stop.set()
    del page


if __name__ == '__main__':
    run(sys.argv[1:])
