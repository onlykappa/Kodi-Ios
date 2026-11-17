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

_CACHE = None
BACK_KEYS = (9, 10, 92, 110)


def model(games, updated, now, offset, league='All', state='ready'):
    """Pure window projection. All wording/grouping/filter choices come from the Sports contract."""
    future = [g for g in games if g['state'] == 'upcoming' and g['start'] >= now]
    codes = sm.league_codes(future)
    league = league if league in codes else 'All'
    shown = sm.filter_league(future, None if league == 'All' else league)
    props = {'state': state, 'subtitle': '%s coming up · %s' % (sm.count_text(len(shown), 'game'),
             sm.updated_text(updated, now, offset).lower()) if updated else 'Updating',
             'empty.title': '', 'empty.text': '', 'empty.text.0':'', 'empty.text.1':''}
    chipline, chipwidth = 0, 0
    for n in range(page.CHIP_LINES): props['chipline.%d' % n] = ''
    for n in range(page.CHIPS):
        code = codes[n] if n < len(codes) and future else ''
        on = code == league
        size = 2 if code == 'All' else max(2,len(code))
        width = 126+(size-2)*24
        if chipwidth and chipwidth+21+width > 972:
            chipline,chipwidth = chipline+1,0
        if code:
            props['chipline.%d' % chipline] = 'true'
            chipwidth += width+(21 if chipwidth else 0)
        props.update({'chip.%d.label' % n: code, 'chip.%d.on' % n: 'true' if on else '',
                      'chip.%d.size' % n: str(size) if code else '',
                      'chip.%d.line' % n: str(chipline) if code else '',
                      'chip.%d.fill' % n: 'FFFFFFFF' if on else 'FF1C1C1E',
                      'chip.%d.textcolor' % n: 'FF000000' if on else 'FFFFFFFF'})
    rows = []
    for day, entries in sm.group_by_day(shown, now, offset):
        for n, game in enumerate(entries):
            title = sm.versus(game)
            lines = choice_sheet.lines(title, 24)
            rows.append({'game': game, 'day': day if n == 0 else '',
                         'day.count': sm.count_text(len(entries), 'game') if n == 0 else '',
                         'firstday': 'true' if not rows else '',
                         'clock': sm.clock_text(game['start'], offset), 'soon': sm.soon_text(game['start'], now),
                         'title': title, 'league': game['league'], 'sources': sm.sources_text(len(game['sources'])),
                         'lines': str(min(4, lines)),
                         'pos': 'only' if len(entries) == 1 else 'first' if n == 0 else 'last' if n == len(entries)-1 else 'mid'})
    for n in range(page.SLOTS):
        row = rows[n] if n < len(rows) else {}
        for key in ('day', 'day.count', 'firstday', 'clock', 'soon', 'title', 'league', 'sources', 'lines', 'pos'):
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
            self.refresh()
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
            if retry: self.refresh()

        def draw(self, error=None):
            if error is not None:self.failed=error
            games, updated = self.data if self.data is not None else ([], 0)
            props, self.rows, self.codes, self.league = model(games,updated,clock(),sm.device_offset(clock()),self.league,
                'error' if self.failed and not self.data else 'ready' if self.data is not None else 'loading')
            for key,value in props.items():
                if getattr(self,'_shown',{}).get(key)!=value:self.setProperty(key,value)
            self._shown = props.copy()

        def refresh(self):
            with self.lock:
                if self.fetching: return
                self.fetching = True
            def fetch():
                global _CACHE
                try:
                    provider.refresh()
                    data = (provider.upcoming_games(), provider.overview()['updated'])
                    with self.lock:
                        if self.stop.is_set(): return
                        self.data = _CACHE = data
                        self.draw(error=False)
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
            elif page.CHIP <= ident < page.CHIP+page.CHIP_LINES*page.CHIPS*7:
                n = ((ident-page.CHIP) % (page.CHIPS*7))//7
                with self.lock:
                    if n < len(self.codes):
                        self.league = self.codes[n]
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
