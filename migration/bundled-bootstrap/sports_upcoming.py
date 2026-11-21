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
import sports_rows
import sports_upcoming_page as page
import sports_filter as sf

_CACHE = None
BACK_KEYS = (9, 10, 92, 110)


def model(games, updated, now, offset, league='All', state='ready', logos=None, slots=None):
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
        if code:
            props['chipline.%d' % chipline] = 'true'
            chipwidth += width+(21 if chipwidth else 0)
        props.update({'chip.%d.label' % n: code, 'chip.%d.on' % n: 'true' if on else '',
                      'chip.%d.size' % n: str(size) if code else '',
                      'chip.%d.line' % n: str(chipline) if code else '',
                      'chip.%d.fill' % n: 'FFFFFFFF' if on else 'FF1C1C1E',
                      'chip.%d.textcolor' % n: 'FF000000' if on else 'FFFFFFFF'})
    for n in range(page.CHIP_LINES): props['chipline.%d' % n] = ''   # no chip row: the Edit filter already chooses leagues for every page (owner, 2026-11-19)
    if league != 'All' and props['subtitle'] != 'Updating': props['subtitle'] = league + ' · ' + props['subtitle']   # a league's own list says which
    rows = []
    for day, entries in sm.group_by_day(shown, now, offset):
        for n, game in enumerate(entries):
            pos = 'only' if len(entries) == 1 else 'first' if n == 0 else 'last' if n == len(entries)-1 else 'mid'
            row = sports_rows.row_props(game, now, offset, logos, pos)
            row.update({'game': game, 'day': day if n == 0 else '', 'day.count': sm.count_text(len(entries), 'game') if n == 0 else '',
                        'firstday': 'true' if not rows else ''})
            rows.append(row)
    for n in range(page.SLOTS if slots is None else slots):
        row = rows[n] if n < len(rows) else {}
        for key in ('day', 'day.count', 'firstday') + sports_rows.KEYS:
            props['row.%d.%s' % (n,key)] = row.get(key, '')
    if state == 'loading' and not rows:
        # Preserve the list's shape while the first result is pending.
        for n in range(3):
            props['row.%d.lines' % n] = '1'
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
    sports_game.run(game,provider=provider,clock=clock,search=True)   # opening a game looks for its sources (Crew, for this game only)


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
            self.slots, self.bigger = slots, False
            self.league = args[0] if args else 'All'   # a league page starts on its chip (an unknown code shows All)
            self.data = _CACHE
            self.draw()
            self.refresh(reload=False)
            import sports_fresh
            sports_fresh.start(provider,self.stop,lambda:self.refresh(reload=False))   # redraw when the real answer replaces the remembered one
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
                'error' if self.failed and not self.data else 'ready' if self.data is not None else 'loading', logos=getattr(self,'logos',{}),slots=self.slots)
            if len(self.rows) > self.slots and self.slots < page.SLOTS and not self.bigger:
                # More games than the short window has rows for (first open with nothing remembered): reopen into the long one, once.
                self.bigger = True
                threading.Thread(target=self.finish,daemon=True).start()
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
                        found = sports_logos.crests(xbmcvfs.translatePath('special://profile/'),sports_rows.crest_urls([g for g in data[0] if g['state'] == 'upcoming'][:60]))
                        with self.lock:
                            if not self.stop.is_set():
                                self.logos = found
                                self.draw()
                    except Exception as error:
                        log('sports: upcoming crests: %s' % type(error).__name__)
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
            import gesture_note
            if not hasattr(self,'_gestures'):self._gestures=gesture_note.Tracker(lambda text:__import__('xbmc').log(text,__import__('xbmc').LOGINFO))
            self._gestures.feed(action)
            if action.getId() in BACK_KEYS: self.finish()

        def finish(self):
            with self.lock:
                self.stop.set()
                self.close()

    # The window with room for the games already known (remembered from the last open); a bigger list reopens into the long one.
    slots = page.SLOTS_SHORT
    if _CACHE is not None:
        try:
            now = clock()
            slots = page.SLOTS_SHORT if len(model(_CACHE[0],_CACHE[1],now,sm.device_offset(now),args[0] if args else 'All')[1]) <= page.SLOTS_SHORT else page.SLOTS
        except Exception:
            slots = page.SLOTS_SHORT
    while True:
        name = page.WINDOW if slots <= page.SLOTS_SHORT else page.WINDOW_LONG
        try:
            window = Upcoming(name,HERE,'Default','1080i')
        except RuntimeError:
            xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
            window = Upcoming(name,HERE,'Default','1080i')
        import page_cover
        with page_cover.covering():   # the window under this opaque page stops drawing while it is open
            window.doModal()
        if hasattr(window,'stop'): window.stop.set()
        again = getattr(window,'bigger',False) and slots < page.SLOTS
        del window
        if not again:
            break
        slots = page.SLOTS


if __name__ == '__main__':
    run(sys.argv[1:])
