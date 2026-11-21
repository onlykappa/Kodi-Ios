"""Upcoming game detail; reads and plays only through the shared Sports provider door."""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import choice_sheet
import page_wait
import sports_model as sm
import sports_provider
import sports_game_page as page
import sports_reminders as sr

BACK_KEYS = (9,10,92,110)
LIVE_EVERY = 5   # seconds between score refreshes while a game is live


def _lines(text, width):
    # Count long words too: a name such as Mönchengladbach wraps inside its team column.
    words = ' '.join(word[n:n+width] for word in text.split() for n in range(0,len(word),width))
    return choice_sheet.lines(words,width)


WHITE_B = '[COLOR FFFFFFFF][B]%s[/B][/COLOR]'   # "Best source:" is bold white inside its grey line (the owner's live mockup)
NEUTRAL,TINT = '445F6B7A','B8'   # a team without a colour gets a soft grey glow; ESPN's colours are 6 hex digits


def lighten(color, amount=.3):
    """ESPN's team colours are often very dark (navy, maroon): mix them toward white so the glow behind the crest is a colour, not black."""
    return ''.join('%02X' % round(int(color[i:i+2],16)+(255-int(color[i:i+2],16))*amount) for i in (0,2,4))


MAX_GLOW = .62   # the brightest a glow may be (relative luminance): above it the hero washes out to white


def _luminance(rgb):
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255


def glow(color):
    """The tint of a team's glow behind its crest: its colour, lightened a little, but never bright. Owner, 2026-11-20: "the colors seem to flash white
    ... then goes to all white": a team whose ESPN colour is white or very light (Cologne's is ffffff) lit the hero up white at 72 % opacity, and two
    light teams washed the whole hero out. A light colour is pulled down to MAX_GLOW and a colour that is nearly white gets the soft grey of a team with
    no colour at all."""
    rgb = [int(color[i:i + 2], 16) for i in (0, 2, 4)]
    if _luminance(rgb) > .85:
        return NEUTRAL
    mixed = [round(c + (255 - c) * .3) for c in rgb]
    light = _luminance(mixed)
    if light > MAX_GLOW:
        mixed = [round(c * MAX_GLOW / light) for c in mixed]
    return TINT + ''.join('%02X' % c for c in mixed)


def checked_text(checked, now):
    """'Checked just now' / 'Checked 2 minutes ago' / 'Checked 1 hour ago' for the Sources card."""
    if checked is None:return ''
    minutes = max(0,int(now-checked)//60)
    if minutes < 1:return 'Checked just now'
    if minutes < 60:return 'Checked %d minute%s ago' % (minutes,'' if minutes==1 else 's')
    hours = minutes//60
    return 'Checked %d hour%s ago' % (hours,'' if hours==1 else 's')


def model(game, now, offset, state='ready', searching=False, reminder=None, checked=None, crests=None):
    """Project the contract without losing source identities or opaque play values."""
    props = {'state':state,'hero.lines':'','league':'','starts':'','clock':'','day':'',
             'sources.count':'','error.title':'','play.error':'','empty.text':'','game.live':'',
             'play.best':'','remind.on':'true' if reminder else '','remind.note':'Reminders are set for this game.' if reminder else '',
             'other.text':'','when':'','checked':'','info.title':'','info.sub':'','away.record':'','home.record':'','away.tint':NEUTRAL,'home.tint':NEUTRAL}
    sources = sm.order_sources(game['sources']) if game else []
    for side in ('away','home'):
        props[side+'.code'] = game[side].get('code','') if game else ''
        crest = game[side].get('crest','') if game else ''
        # The team's real crest from the phone's own copy (sports_logos.crests); until it is there the code shows on a ring. No `crests` at all: the address as is.
        props[side+'.crest'] = crest if crests is None else crests.get(crest,'')
        if game:   # the short name on the hero ("Colts"), the record under it, the team's colour behind it
            props[side+'.name'] = game[side].get('short') or game[side].get('name','')
            props[side+'.record'] = game[side].get('record','')
            color = str(game[side].get('color') or '')
            if len(color) == 6 and all(c in '0123456789abcdefABCDEF' for c in color):props[side+'.tint'] = glow(color)
        else:props[side+'.name'] = ''
    if game:
        until = sm.until_text(game['start'],now)
        week = game.get('week')
        props.update({'when':sm.day_label(game['start'],now,offset)+(' · '+until if until else ''),
                      'checked':checked_text(checked,now),
                      'info.title':game.get('league_name','')+(' · Week %d' % week if week else ''),
                      'info.sub':sm.day_label(game['start'],now,offset)+' at '+sm.clock_text(game['start'],offset)})
        props.update({'hero.lines':str(min(3,max(_lines(props[side+'.name'],11) for side in ('away','home')))),
                      'league':game['league'],'starts':sm.start_text(game['start'],now,offset),
                      'clock':sm.clock_text(game['start'],offset),'day':sm.day_label(game['start'],now,offset),
                      'sources.count':str(len(sources)) if sources else '',
                      'state':'ready' if sources else 'searching' if searching else 'empty',
                      'game.live':'true' if game.get('state')=='live' else '',
                      'empty.text':'No sources available yet. Try again.' if game.get('state')=='live' else 'Check back closer to the start. Refresh looks again.'})
        if game.get('state')=='live':   # "● LIVE", the score, the clock (owner mockup C5); no score (golf, F1): just the clock
            scores = (game['away'].get('score'),game['home'].get('score'))
            live_clock = sm.live_clock(game,now)   # counted down second by second between ESPN answers
            if None not in scores:props.update({'clock':'%s – %s' % scores,'when':live_clock})
            else:props.update({'clock':live_clock,'when':''})
    elif state=='error':props['error.title']="Can't load this game right now"
    elif state=='loading':props.update({'hero.lines':'1'})
    else:props.update(state='gone',**{'error.title':'This game is no longer listed'})
    if game and not sources and state != 'error' and not reminder and not game.get('state')=='live':
        props['remind.note'] = "No source yet. Tap Remind me for a notification when one is ready."
    if sources:   # the best source, named under Play (the same choice the Play button makes)
        try:
            import sports_loop_router
            best = sports_loop_router.automatic_source(sources)
            props['play.best'] = (WHITE_B % 'Best source:') + ' ' + ' · '.join(v for v in (best.get('addon'),best.get('quality'),best.get('language')) if v)
        except Exception:
            props['play.best'] = ''
        props['other.text'] = 'Other sources (%d)' % (len(sources)-1) if len(sources)>1 else ''
    for n in range(page.SLOTS):
        values = {}
        if n < len(sources):
            source = sources[n]
            tag = source.get('tag') if source.get('tag') in ('best','good') else 'plain'
            title = source['addon']
            detail = ' · '.join(value for value in (source['quality'],source['language']) if value) or 'Quality not reported'
            if source.get('also'):detail += '\nAlso on '+', '.join(source['also'])
            title_cols,detail_cols = {'best':(20,22),'good':(16,18),'plain':(27,30)}[tag]
            title_lines = _lines(title,title_cols)
            detail_lines = sum(_lines(line,detail_cols) for line in detail.splitlines())
            values = {'title':title,'detail':detail,'tag':tag,
                      'code':''.join(w[0] for w in title.split())[:2].upper(),
                      'form':str(page.FORMS.index((title_lines,detail_lines))),
                      'pos':'only' if len(sources)==1 else 'first' if n==0 else 'last' if n==len(sources)-1 else 'mid'}
        for key in ('title','detail','tag','code','form','pos'):props['source.%d.%s' % (n,key)] = values.get(key,'')
    return props,sources


AUTO_SEARCH = 180   # seconds a live game's page keeps looking for sources by itself
AUTO_EVERY = 5      # seconds between those looks


def auto_wanted(live, has_sources, now, until, failed=False):
    """True while a live game's page should be looking for sources without being asked: it is live, has none, has not given up and was opened less than AUTO_SEARCH
    ago. Owner, build 646 log 317cd411: a live game tapped right after launch said "None yet" while Crew's first scan was still running; the sources came a
    moment later but only after "Check now"."""
    return bool(live and not has_sources and not failed and now < until)


def auto_due(now, last, searching):
    """True when another look is due (none running and AUTO_EVERY seconds since the last)."""
    return not searching and now - last >= AUTO_EVERY


def warm_best(sources, warm=None):
    """The best source is a Crew link: do Crew's folder listing for it now, while the page is open, so the Play tap does not (owner, build 639 log fd1d028c: two
    folder listings, 2.7 s, after every tap). Off the main thread; never raises. True when a link was warmed."""
    try:
        import json
        import sports_loop_router
        best = sports_loop_router.automatic_source(sources)
        value = json.loads(best['play'])
        if value.get('e') != 'TheCrewRoute':
            return False
        try:
            import xbmc
            if xbmc.Player().isPlayingVideo():
                return False
        except Exception:
            pass
        if warm is None:
            import sports_crew_routes
            warm = sports_crew_routes.warm
        return bool(warm(value['l']))
    except Exception:
        return False


def run(game, provider=None, clock=time.time, search=False):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import diagnostics
    provider = provider or sports_provider.get()
    log = lambda text:xbmc.log(text,xbmc.LOGINFO)
    game_id = game['id']

    class Game(xbmcgui.WindowXMLDialog):
        def onInit(self):
            if hasattr(self,'stop'):
                return
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.fetching = False
            self.data = game
            self.search_token = None
            self.search_failed = False
            self.checked = clock()   # when the sources were last looked for (the Sources card says so)
            self.auto_until = clock() + AUTO_SEARCH   # a live game keeps looking for sources by itself for this long (auto_wanted)
            self.auto_last = 0.0
            self.sources = []
            self.crests = {}
            threading.Thread(target=self.load_crests,daemon=True).start()
            if search:
                self.find_sources()
            self.draw()
            self.refresh(reload=False)
            def tick():
                monitor=xbmc.Monitor()
                last=clock()
                last_search=time.monotonic()
                while not page_wait.idle(self.stop,monitor,1):
                    token = self.search_token
                    if token and time.monotonic()-last_search>=3:
                        last_search=time.monotonic()
                        try:searching = getattr(provider,'searching_game',lambda *args:False)(game_id,token)
                        except Exception:searching = False;self.search_failed = True
                        if not searching and self.search_token == token:
                            try:self.search_failed = self.search_failed or getattr(provider,'game_search_failed',lambda value:False)(token)
                            except Exception:self.search_failed = True
                            self.search_token = None
                        self.refresh(reload=False)
                    if auto_wanted((self.data or {}).get('state') == 'live', bool(self.sources), clock(), self.auto_until, self.search_failed) and \
                            auto_due(time.monotonic(), self.auto_last, bool(self.search_token)):
                        self.auto_last = time.monotonic()
                        self.find_sources()
                    # Every second: the clock and "in 1 h 14 min" are worked out again (only what changed is written). A live game asks for fresh
                    # scores every 5 s, any other every 30 s (owner: scores and times must be live).
                    with self.lock:
                        if self.stop.is_set():return
                        live=(self.data or {}).get('state')=='live'
                        self.draw()
                    if clock()-last>=(LIVE_EVERY if live else 30):
                        self.refresh(reload=False)
                        last=clock()
            threading.Thread(target=tick,daemon=True).start()

        def draw(self,error=False):
            searching = bool(self.search_token and getattr(provider,'searching_game',lambda *args:False)(game_id,self.search_token))
            # A live game with no source yet is still being looked for: "Searching for sources", not "None yet" (auto_wanted).
            searching = searching or auto_wanted((self.data or {}).get('state') == 'live', bool(self.sources), clock(), self.auto_until, self.search_failed)
            props,self.sources = model(self.data,clock(),sm.device_offset(clock()),'error' if error else 'ready',searching,
                                       sr.get(xbmcvfs.translatePath('special://profile/'),game_id),self.checked,self.crests)
            if self.search_failed and not self.sources:
                props['state']='error';props['error.title']="Can't search for sources right now"
            for key,value in props.items():
                # The tap handler also writes play.error; a refresh must still clear it.
                if key=='play.error' or getattr(self,'_shown',{}).get(key)!=value:self.setProperty(key,value)
            self._shown = props.copy()
            if self.sources:   # the best source's Crew folder is listed now, not at the tap
                best = str((self.sources[0] if self.sources else {}).get('play') or '')
                if getattr(self, '_warmed', None) != best:
                    self._warmed = best
                    threading.Thread(target=warm_best, args=(list(self.sources),), daemon=True).start()

        def load_crests(self):
            """The teams' real crests, downloaded once and kept on the phone; the page draws first (a ring with the code) and gains them a moment later."""
            try:
                import sports_logos
                with self.lock:current=self.data
                urls = [current[side].get('crest','') for side in ('away','home')] if current else []
                found = sports_logos.crests(xbmcvfs.translatePath('special://profile/'),urls)
                with self.lock:
                    if found and not self.stop.is_set():
                        self.crests = found
                        self.draw()
            except Exception as error:log('sports: crests: %s' % type(error).__name__)

        def refresh(self, reload=True):
            with self.lock:
                if self.fetching:return
                self.fetching=True
            def fetch():
                try:
                    if reload: provider.refresh()
                    current=provider.game(game_id)
                    self.checked=clock()
                    with self.lock:
                        if self.stop.is_set():return
                        self.data=current
                        self.draw()
                except Exception as error:
                    log('sports: game refresh: %s: %s' % (type(error).__name__,diagnostics.error_text(error)))
                    with self.lock:
                        if not self.stop.is_set():self.draw(error=True)
                finally:
                    with self.lock:self.fetching=False
            threading.Thread(target=fetch,daemon=True).start()

        def onClick(self,ident):
            if ident==page.BACK:self.finish()
            elif ident==page.RETRY and self.search_failed:
                self.find_sources()
                self.draw()
            elif ident in (page.REFRESH,page.RETRY):self.refresh()
            elif ident==page.SEARCH_RETRY:
                self.find_sources()
                self.draw()
            elif ident in (page.REMIND,page.REMIND_ON):
                import sports_remind
                with self.lock: current=self.data
                if current is not None:
                    sports_remind.ask(current,xbmcvfs.translatePath('special://profile/'))
                    with self.lock: self.draw()
            elif ident==page.OTHER:   # jump to the first source (the list scrolls to the focused row)
                try:self.setFocusId(page.SOURCE+int(self.getProperty('source.0.form') or 0))
                except Exception:pass
            elif ident==page.INFO_OPEN:
                with self.lock: current=self.data
                if current is not None:
                    import sports_game_facts
                    if sports_game_facts.run(current,clock=clock):   # Play was tapped on the Info page
                        with self.lock:sources=list(self.sources)
                        if sources:
                            import sports_loop_router
                            self.start_play(sports_loop_router.automatic_source(sources))
                    with self.lock:self.draw()
            elif ident==page.AUTO:
                with self.lock: sources=list(self.sources)
                if sources:
                    import sports_loop_router
                    self.start_play(sports_loop_router.automatic_source(sources))
            elif page.SOURCE<=ident<page.SOURCE+page.SLOTS*len(page.FORMS):
                n=(ident-page.SOURCE)//len(page.FORMS)
                with self.lock:source=self.sources[n] if n<len(self.sources) else None;every=list(self.sources)
                if source is not None:
                    import sports_loop_router
                    # A tap opens that source and, if it is dead or freezes, goes on to the game's other sources by itself (owner, 2026-11-20).
                    self.start_play(sports_loop_router.tapped_source(source,every))

        def start_play(self,source):
            self.setProperty('play.error','')
            pending=[]
            try:sports_provider.play(source,log,launch=lambda *args:pending.append(args))
            except Exception as error:
                log('sports: play: %s: %s' % (type(error).__name__,diagnostics.error_text(error)))
                self.setProperty('play.error',"Can't play this source right now. Try another source.")
                return
            if pending:
                # Native Loop may open its own selector. Dismiss the Sports modal
                # stack before dispatch, instead of opening over this callback.
                self.finish()
                xbmc.executebuiltin('Dialog.Close(all,true)')
                def handoff():
                    xbmc.sleep(250)
                    import sports_jet
                    try:
                        for args in pending:sports_jet._launch(*args)
                    except Exception as error:
                        log('sports: player handoff failed (%s)' % type(error).__name__)
                        try:xbmcgui.Dialog().notification('Sports',"Can't open the player right now. Try again.",xbmcgui.NOTIFICATION_WARNING,4000)
                        except Exception:pass
                threading.Thread(target=handoff,daemon=True).start()

        def find_sources(self):
            self.checked = clock()
            try:
                self.search_token = provider.request_game(game_id)
                self.search_failed = False
            except Exception as error:
                self.search_token = None
                self.search_failed = True
                log('sports: game search failed (%s)' % type(error).__name__)
                try:xbmcgui.Dialog().notification('Sports',"Can't search for sources right now. Try again.",xbmcgui.NOTIFICATION_WARNING,4000)
                except Exception:pass

        def onAction(self,action):
            import gesture_note
            if not hasattr(self,'_gestures'):self._gestures=gesture_note.Tracker(lambda text:__import__('xbmc').log(text,__import__('xbmc').LOGINFO))
            self._gestures.feed(action)
            if action.getId() in BACK_KEYS:self.finish()

        def finish(self):
            with self.lock:
                self.stop.set()
                if self.search_token:
                    try:provider.cancel_game_search(self.search_token)
                    except Exception:pass
                self.close()

    try:window=Game(page.WINDOW,HERE,'Default','1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
        window=Game(page.WINDOW,HERE,'Default','1080i')
    import page_cover
    with page_cover.covering():   # the window under this opaque page stops drawing while it is open
        window.doModal()
    if hasattr(window,'stop'):window.stop.set()
    del window


def main(args):
    """RunScript(service.kodi.ios.bootstrap,sports_game,<URL-quoted game id>): the page a reminder's notification opens."""
    from urllib.parse import unquote
    provider = sports_provider.get()
    found = None
    try:
        found = provider.game(unquote(args[0])) if args else None
    except Exception:
        found = None
    if found is not None:
        run(found, provider=provider)


if __name__ == '__main__':
    main(sys.argv[1:])
