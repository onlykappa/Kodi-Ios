"""Sports › Live Now (DEC-055, DEC-057; sports_live_page.py draws it; the owner's rows of 2026-11-21, ISSUE-437).

Shows every live game as a compact row, grouped by league under a small header (the league's logo, its name, a chevron, and "College Football" under
NCAAF): NFL games with NFL games, NBA with NBA. Inside a league the game closest to its end comes first. A tap opens the game's page. The page opens at
once, asks the provider in a thread, refreshes by itself every 30 seconds and when a score batch lands; no add-on answering shows "Can't load live
games right now".
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


LEAGUE_ORDER = ('NFL', 'NBA', 'NHL', 'MLB', 'WNBA', 'NCAAF', 'NCAAB', 'MLS', 'EPL', 'UCL', 'LIGA', 'BUN', 'SERA', 'LIG1')   # the big leagues first, the rest after
FOOTBALL_ICON = 'special://skin/extras/icons/football-american.png'
BASKETBALL_ICON = 'special://skin/extras/icons/basketball.png'
SHORT_NAME = 10   # a team name longer than this is drawn as its code ("UNC", "WVU"), as the ESPN app does


def team_label(team):
    """What sits under a team's logo: ESPN's short name ("Western KY"), or its code ("TNTC") when the name is too long to sit clear of the clock."""
    short = team.get('short') or team.get('name') or ''
    code = team.get('code') or ''
    return short if len(short) <= SHORT_NAME or not code or code == '???' else code


def dark_crest(url):
    """A team logo's address in ESPN's dark-page folder ('/500/' -> '/500-dark/'), or '' for an address that is not a team logo."""
    url = str(url or '')
    return url.replace('/500/', '/500-dark/', 1) if '/i/teamlogos/' in url and '/500/' in url else ''


def league_title(game):
    """(header name, subtitle): "NBA" / "" , "NCAAF" / "College Football", "Premier League" / ""."""
    code, name = str(game.get('league') or ''), str(game.get('league_name') or '')
    if code.startswith('NCAA'):
        return code, name
    return (name if name and len(name) <= 16 else code), ''


def grouped(games):
    """The games with each league's games together: the big leagues first, then the rest in the order they came; order inside a league is kept."""
    order = {}
    for game in games:
        order.setdefault(game.get('league'), len(order))
    rank = lambda code: (LEAGUE_ORDER.index(code), 0) if code in LEAGUE_ORDER else (len(LEAGUE_ORDER), order[code])
    return sorted(games, key=lambda game: rank(game.get('league')))


def _empty_game(g):
    props = {}
    for k in ('id', 'clock', 'ball', 'dn', 'yd', 'rz', 'gn', 'gs', 'hp', 'gl', 'et'):
        props['g.%d.%s' % (g, k)] = ''
    for t in 'ah':
        for k in ('name', 'short', 'score', 'crest'):
            props['g.%d.%s.%s' % (g, t, k)] = ''
    return props


def game_props(g, game, first=False):
    """The properties of row number g (1-based) for a game of the contract. first: the first game of its league, which carries the league's header."""
    props = _empty_game(g)
    away, home = game['away'], game['home']
    props['g.%d.clock' % g] = sm.live_clock(game, time.time()) if game.get('state') == 'live' else game.get('clock') or ''
    props['g.%d.id' % g] = game.get('id') or ''
    for t, team in (('a', away), ('h', home)):
        props.update({'g.%d.%s.name' % (g, t): team.get('name') or '', 'g.%d.%s.crest' % (g, t): team.get('crest') or '',
                      'g.%d.%s.short' % (g, t): team_label(team),
                      'g.%d.%s.score' % (g, t): '' if team.get('score') is None else str(team['score'])})
    if not home.get('name'):   # a race weekend, a tournament: one title, no two teams (Formula 1, golf): the row draws the title and the session
        props['g.%d.et' % g] = game.get('title') or away.get('name') or ''
    props['g.%d.dn' % g] = game.get('detail') or ''                           # football: "2nd & 10"
    props['g.%d.yd' % g] = game.get('yard') or ''                             # football: "WVU 45"
    props['g.%d.rz' % g] = 'true' if game.get('redzone') and game.get('yard') else ''   # inside the 20: the yard line is red
    props['g.%d.ball' % g] = game.get('ball') if game.get('ball') in ('a', 'h') else ''   # which side has the ball; it moves with every ESPN answer
    if first:
        props['g.%d.gn' % g], props['g.%d.gs' % g] = league_title(game)
        props['g.%d.hp' % g] = '' if props['g.%d.gs' % g] else 'true'   # the header without a subtitle
        props['g.%d.gl' % g] = str(game.get('league') or '')                  # the code for now: with_crests turns it into the logo's file
    return props


def with_crests(props, profile, get=None):
    """The rows' team crests and the headers' league logos as the phone's own copies (sports_logos): a team whose logo cannot be had shows an empty ring,
    never letters; a league without a logo shows its name alone. `get` is the download (tests replace it); outside Kodi, with no profile folder, the
    addresses are dropped (nothing is drawn for them)."""
    import sports_logos
    urls = [props.get('g.%d.%s.crest' % (g, t)) or '' for g in range(1, lp.GAMES + 1) for t in 'ah']
    download = lambda wanted: sports_logos.crests(profile, wanted, get) if get is not None else sports_logos.crests(profile, wanted)
    # The page is black: a logo that is near black (Iowa's) is fetched from ESPN's dark-page folder instead; every other team keeps its coloured logo.
    probe = (lambda url: sports_logos.needs_dark(profile, url, get)) if get is not None else (lambda url: sports_logos.needs_dark(profile, url))
    target = {url: ((dark_crest(url) or url) if probe(url) else url) for url in dict.fromkeys(u for u in urls if u)}
    got = download(list(target.values()))
    for url, wanted in target.items():   # a dark-page logo ESPN does not have (a 404) falls back to the team's plain one
        if wanted != url and wanted not in got:
            got.update({wanted: download([url]).get(url, '')})
    found = {url: got.get(wanted, '') for url, wanted in target.items()}
    for g in range(1, lp.GAMES + 1):
        for t in 'ah':
            key = 'g.%d.%s.crest' % (g, t)
            if key in props:
                props[key] = found.get(props[key], '')
        key = 'g.%d.gl' % g
        code = props.get(key) or ''
        if code:
            fetch = (lambda c: sports_logos.fetch_dark(profile, c, get)) if get is not None else (lambda c: sports_logos.fetch_dark(profile, c))
            props[key] = FOOTBALL_ICON if code == 'NCAAF' else BASKETBALL_ICON if code == 'NCAAB' else fetch(code)
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
    shown = grouped(sm.filter_league(games, None if chosen == 'All' else chosen))
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
        props.update(game_props(g, shown[g - 1], g == 1 or shown[g - 2].get('league') != shown[g - 1].get('league')) if g <= len(shown) else _empty_game(g))
    extra = len(shown) - lp.GAMES
    if extra > 0:
        props['more'] = '%s not shown.' % sm.count_text(extra, 'more game')
    return props, chosen


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
    return props, chosen, {}


def control_target(control):
    """('chip', n) | ('source', card, source) | None for a control id of the page."""
    for rows in (1, 2, 3):
        if lp.chip_id(rows, 0) <= control < lp.chip_id(rows, 0) + lp.CHIP_IDS:
            return ('chip', control - lp.chip_id(rows, 0))
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


def _offline(url):
    raise OSError('not asked: the first frame uses only what is on the phone')


def first_frame(page, provider_module, chosen, profile, clock=None):
    """Before the page opens: the games from the answer saved on the phone, drawn with the crests that are already kept (no request: an unseen team's logo
    is asked for afterwards, one 8 s timeout at a time before this). Owner, 2026-11-22 (log 71e31b26): Live Now took 3-5 s to show anything. Returns True when
    it drew. Never raises."""
    try:
        provider = provider_module.get()
        if clock:
            clock.lap('provider')
        if not getattr(provider, 'has_answer', lambda: False)():
            return False
        props, chosen_now, slots = load(provider, chosen)
        if clock:
            clock.lap('saved answer')
        if props.get('state') not in ('ok', 'none'):
            return False
        props = with_crests(props, profile, get=_offline)
        if clock:
            clock.lap('crests on the phone')
        for key, value in props.items():
            page.setProperty(key, value)
        page.chosen, page.slots, page.drawn = chosen_now, slots, True
        return True
    except Exception:
        return False


def run(args=()):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import sports_provider
    import sports_routes
    import page_clock
    log = lambda message: xbmc.log('Kodi iOS Sports: ' + message, xbmc.LOGINFO)
    clock = page_clock.Clock('live now', log)

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
            if not getattr(self, 'drawn', False):
                self.chosen, self.codes, self.slots = (args[0] if args else 'All'), [], {}   # a league page starts on its chip
                self.setProperty('sub', 'Updating')
            self.codes = getattr(self, 'codes', [])
            self.busy = threading.Lock()
            clock.done('first frame' if getattr(self, 'drawn', False) else 'opened empty (nothing saved to draw)')
            self.fetch(False)
            import sports_fresh
            sports_fresh.start(sports_provider.get(), self.stop, lambda: self.fetch(False, quiet=True))
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
                            profile = xbmcvfs.translatePath('special://profile/')
                            if not self.stop.is_set():   # the games first, with the crests already on the phone; the logos still to be fetched follow
                                self.chosen, self.slots = chosen, slots
                                self.show(with_crests(dict(props), profile, get=_offline))
                            props = with_crests(props, profile)   # real logos, kept on the phone
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
            import gesture_note
            if not hasattr(self,'_gestures'):self._gestures=gesture_note.Tracker(lambda text:__import__('xbmc').log(text,__import__('xbmc').LOGINFO))
            self._gestures.feed(action)
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
    clock.lap('window')
    first_frame(page, sports_provider, args[0] if args else 'All', xbmcvfs.translatePath('special://profile/'), clock)
    import page_cover
    with page_cover.covering():   # the window under this opaque page stops drawing while it is open
        page.doModal()
    if hasattr(page, 'stop'):
        page.stop.set()
    del page


if __name__ == '__main__':
    run(sys.argv[1:])
