"""Sports Upcoming (approved board 10). Only sports_provider supplies data; other pages follow in separate commits."""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'resources', 'lib'))
import choice_sheet
import page_wait
import sports_model as sm
import sports_provider
import sports_upcoming_page as page
import sports_filter as sf

_CACHE = None
BACK_KEYS = (9, 10, 92, 110)


def model(games, updated, now, offset, league='All', state='ready', logos=None):
    """Pure window projection. All wording/grouping/filter choices come from the Sports contract."""
    future = [g for g in games if g['state'] == 'upcoming' and g['start'] >= now]
    codes = sm.league_codes(future)
    league = league if league in codes else 'All'
    shown = sm.filter_league(future, None if league == 'All' else league)
    props = {'state': state, 'subtitle': '%s coming up · %s' % (sm.count_text(len(shown), 'game'),
             sm.updated_text(updated, now, offset).lower()) if updated else 'Updating',
             'empty.title': '', 'empty.text': '', 'empty.text.0':'', 'empty.text.1':''}
    shown_label = league if league != 'All' else 'All'
    props.update({'league.label': shown_label if future else '', 'league.size': str(min(7, max(3, len(shown_label))))})   # mockup A: the capsule says which league

    rows = []
    for day, entries in sm.group_by_day(shown, now, offset):
        for n, game in enumerate(entries):
            title = sm.versus(game)
            lines = choice_sheet.lines(title, 24)
            rows.append({'game': game, 'day': day if n == 0 else '',
                         'day.count': sm.count_text(len(entries), 'game') if n == 0 else '',
                         'firstday': 'true' if not rows else '',
                         'clock': sm.clock_text(game['start'], offset), 'clock.main': sm.clock_text(game['start'], offset).rsplit(' ', 1)[0], 'clock.ampm': (sm.clock_text(game['start'], offset).rsplit(' ', 1) + [''])[1], 'soon': sm.soon_text(game['start'], now),
                         'title': title, 'league': game['league'], 'logo': (logos or {}).get(game['league'], ''), 'sources': sm.sources_text(len(game['sources'])),
                         'lines': str(min(4, lines)),
                         'pos': 'only' if len(entries) == 1 else 'first' if n == 0 else 'last' if n == len(entries)-1 else 'mid'})
    for n in range(page.SLOTS):
        row = rows[n] if n < len(rows) else {}
        for key in ('day', 'day.count', 'firstday', 'clock', 'clock.main', 'clock.ampm', 'soon', 'title', 'league', 'logo', 'sources', 'lines', 'pos'):
            props['row.%d.%s' % (n,key)] = row.get(key, '')
    if state == 'loading' and not rows:
        # Preserve the list's shape while the first result is pending.
        for n in range(3):
            props['row.%d.lines' % n] = '2'
            props['row.%d.pos' % n] = 'only' if n else 'first'
    elif state == 'error':
        props.update(subtitle='Not updated', **{'empty.title': 'Can’t load games right now',
                     'empty.text': 'The sports add-ons didn’t answer. Check the connection, then try again.',
                     'empty.text.0':'The sports add-ons didn’t answer.',
                     'empty.text.1':'Check the connection, then try again.'})
    elif not rows:
        props.update(state='empty',subtitle=sm.updated_text(updated,now,offset) if updated else 'Not updated',
                     **{'empty.title': 'No games coming up','empty.text': 'Nothing is scheduled yet.',
                        'empty.text.0':'Nothing is scheduled yet.'})
    return props, rows, codes, league


def league_spec(games, current, now, logos=None):
    """The choice sheet behind the capsule: "All leagues" and the leagues that have a game (most games first), at most eight rows.
    Returns (spec, codes) with codes[i] the league of row i ('All' for the first)."""
    future = [g for g in games if g['state'] == 'upcoming' and g['start'] >= now]
    codes = sm.league_codes(future)[:8]
    names = {g['league']: g.get('league_name') or g['league'] for g in future}
    rows = [{'label': 'All leagues', 'detail': sm.count_text(len(future), 'game') + ' coming up', 'tag': 'Showing' if current == 'All' else '',
             'tint': 'FF0A84FF', 'glyph': 'medal.png'}]
    for code in codes[1:]:
        count = len([g for g in future if g['league'] == code])
        rows.append({'label': names[code], 'detail': sm.count_text(count, 'game'), 'tag': 'Showing' if current == code else '',
                     'tint': 'FFF2F2F7', 'glyph': (logos or {}).get(code, '')})
    more = len(sm.league_codes(future)) - len(codes)
    return {'heading': 'Show games from', 'sub': 'For this visit only. Edit chooses what the app shows.', 'rows': rows, 'button': 'Cancel',
            'foot': '%d more league%s: use Edit to see %s.' % (more, '' if more == 1 else 's', 'it' if more == 1 else 'them') if more > 0 else ''}, codes


def open_game(game, log, provider=None, clock=time.time):
    """Keep the same provider and game identity when opening boards 12–13."""
    log('sports: game %s' % game['id'])
    import sports_game
    sports_game.run(game,provider=provider,clock=clock)


def run(args=(), provider=None, clock=time.time, on_game=None):
    import xbmc
    import xbmcgui
    import xbmcvfs
    global _CACHE
    provider = provider or sports_provider.get()
    on_game = on_game or (lambda game,log:open_game(game,log,provider,clock))
    log = lambda text: xbmc.log(text, xbmc.LOGINFO)

    class Upcoming(xbmcgui.WindowXMLDialog):
        def onInit(self):
            if hasattr(self,'stop'):
                return  # Kodi re-enters this window after the game's page closes.
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.fetching = False
            self.failed = False
            self.league = args[0] if args else 'All'   # a league page starts on its chip (an unknown code shows All)
            self.data = _CACHE
            self.draw()
            self.refresh(reload=False)
            def tick():
                monitor=xbmc.Monitor()
                last=clock()
                while not page_wait.idle(self.stop,monitor,1):
                    if clock()-last >= 30:
                        self.poll()
                        last=clock()
            threading.Thread(target=tick,daemon=True).start()

        def poll(self):
            # A scan can finish after the first bounded wait. Recover without
            # requiring a tap; refresh already guards against concurrent fetches.
            with self.lock:
                if self.stop.is_set(): return
                self.draw()
                retry = self.failed or self.data is None
            self.refresh(reload=retry)

        def draw(self, error=None):
            if error is not None:self.failed=error
            games, updated = self.data if self.data is not None else ([], 0)
            props, self.rows, self.codes, self.league = model(games,updated,clock(),sm.device_offset(clock()),self.league,
                'error' if self.failed and not self.data else 'ready' if self.data is not None else 'loading', logos=getattr(self,'logos',{}))
            props.update(sf.edit_state(provider))
            for key,value in props.items():
                if getattr(self,'_shown',{}).get(key)!=value:self.setProperty(key,value)
            self._shown = props.copy()

        def refresh(self, reload=True):
            with self.lock:
                if self.fetching: return
                self.fetching = True
            def fetch():
                global _CACHE
                try:
                    if reload: provider.refresh()
                    data = (provider.upcoming_games(), provider.overview()['updated'])
                    with self.lock:
                        if self.stop.is_set(): return
                        self.data = _CACHE = data
                        self.draw(error=False)
                    # Real league logos: fetched once, kept on the phone; the rows draw first and gain them a moment later.
                    try:
                        import sports_logos,xbmcvfs
                        found = sports_logos.paths(xbmcvfs.translatePath('special://profile/'),sorted({g['league'] for g in data[0]}))
                        with self.lock:
                            if not self.stop.is_set():
                                self.logos = found
                                self.draw()
                    except Exception as error:
                        log('sports: upcoming logos: %s' % type(error).__name__)
                except Exception as error:
                    import diagnostics
                    log('sports: upcoming refresh: %s: %s' % (type(error).__name__,diagnostics.error_text(error)))
                    with self.lock:
                        if not self.stop.is_set(): self.draw(error=True)
                finally:
                    with self.lock: self.fetching = False
            threading.Thread(target=fetch,daemon=True).start()

        def onClick(self, ident):
            if ident == page.BACK: self.finish()
            elif ident in (page.REFRESH,page.RETRY): self.refresh()
            elif ident == page.edit_button.ID:
                import sports_edit
                if sports_edit.run(): self.refresh(reload=False)
            elif ident in page.PICK_IDS:
                with self.lock:
                    games = self.data[0] if self.data is not None else []
                    league,logos = self.league,getattr(self,'logos',{})
                spec,codes = league_spec(games,league,clock(),logos)
                answer = choice_sheet.choose(spec)
                with self.lock:
                    if 0 <= answer < len(codes):
                        self.league = codes[answer]
                        self.draw()
            elif page.ROW <= ident < page.ROW+page.SLOTS*len(page.FORMS):
                n = (ident-page.ROW)//len(page.FORMS)
                with self.lock:
                    game = self.rows[n]['game'] if n < len(self.rows) else None
                if game is not None: on_game(game,log)
            elif ident == page.LEAGUES:
                log('sports: leagues')
                import sports_leagues
                sports_leagues.run(provider=provider,clock=clock)

        def onAction(self, action):
            if action.getId() in BACK_KEYS: self.finish()

        def finish(self):
            with self.lock:
                self.stop.set()
                self.close()

    try:
        window = Upcoming(page.WINDOW,HERE,'Default','1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
        window = Upcoming(page.WINDOW,HERE,'Default','1080i')
    window.doModal()
    if hasattr(window,'stop'): window.stop.set()
    del window


if __name__ == '__main__':
    run(sys.argv[1:])
