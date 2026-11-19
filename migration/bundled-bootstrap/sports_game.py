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
import sports_game_info as info_mod

BACK_KEYS = (9,10,92,110)


def _lines(text, width):
    # Count long words too: a name such as Mönchengladbach wraps inside its team column.
    words = ' '.join(word[n:n+width] for word in text.split() for n in range(0,len(word),width))
    return choice_sheet.lines(words,width)


def info_props(game, info, view, now, offset):
    """The Info section's properties (board D3 / D4): empty strings hide a part."""
    props = {'info.kickoff':'','info.venue':'','info.place':'','st.title':'','st.switch':'','st.n':''}
    for n in range(2):
        for key in ('name','line'):props['form.%d.%s' % (n,key)] = ''
        for d in range(info_mod.FORM):props['form.%d.d%d' % (n,d)] = ''
    for i in range(4):props['st.h%d' % i] = ''
    for n in range(page.ST_ROWS):
        for key in ('rank','team','crest','c0','c1','c2','c3','me','pos'):props['st.%d.%s' % (n,key)] = ''
    if not game or not info:return props
    props['info.kickoff'] = sm.day_label(game['start'],now,offset) + ' · ' + sm.clock_text(game['start'],offset)
    props['info.venue'],props['info.place'] = info.get('venue',''),info.get('place','')
    for n,team in enumerate(info.get('form') or []):
        props['form.%d.name' % n] = team['name']
        props['form.%d.line' % n] = ' · '.join(v for v in (team['record'],('%s %s' % (team['side'],team['split'])) if team['split'] else '') if v)
        for d,letter in enumerate(team['results']):props['form.%d.d%d' % (n,d)] = letter
    table = info.get('standings')
    if table and table['views']:
        shown = table['views'][view % len(table['views'])]
        props['st.title'] = shown['title']
        if len(table['views']) > 1:props['st.switch'] = 'wild' if shown['name'] == 'Divisional' else 'div'
        for i,label in enumerate(shown['cols']):props['st.h%d' % i] = label
        rows = shown['rows'][:page.ST_ROWS]
        for n,row in enumerate(rows):
            props.update({'st.%d.rank' % n:row['rank'],'st.%d.team' % n:row['team'],'st.%d.crest' % n:row['crest'],
                          'st.%d.me' % n:'true' if row['me'] else '',
                          'st.%d.pos' % n:'last' if n==len(rows)-1 else 'mid'})
            for i,value in enumerate(row['cols']):props['st.%d.c%d' % (n,i)] = value
    return props


def model(game, now, offset, state='ready', searching=False, reminder=None, info=None, view=0):
    """Project the contract without losing source identities or opaque play values."""
    props = {'state':state,'hero.lines':'','league':'','starts':'','clock':'','day':'',
             'sources.count':'','error.title':'','play.error':'','empty.text':'','game.live':'',
             'play.best':'','remind.on':'true' if reminder else '','remind.note':sr.summary(reminder)}
    sources = sm.order_sources(game['sources']) if game else []
    for side in ('away','home'):
        for key in ('code','name','crest'):props[side+'.'+key] = game[side].get(key,'') if game else ''
    if game:
        props.update({'hero.lines':str(max(_lines(game[side]['name'],11) for side in ('away','home'))),
                      'league':game['league'],'starts':sm.start_text(game['start'],now,offset),
                      'clock':sm.clock_text(game['start'],offset),'day':sm.day_label(game['start'],now,offset),
                      'sources.count':str(len(sources)) if sources else '',
                      'state':'ready' if sources else 'searching' if searching else 'empty',
                      'game.live':'true' if game.get('state')=='live' else '',
                      'empty.text':'No sources available yet. Try again.' if game.get('state')=='live' else 'Check back closer to the start. Refresh looks again.'})
    elif state=='error':props['error.title']="Can't load this game right now"
    elif state=='loading':props.update({'hero.lines':'1'})
    else:props.update(state='gone',**{'error.title':'This game is no longer listed'})
    if sources:   # the best source, named under Play (the same choice the Play button makes)
        try:
            import sports_loop_router
            best = sports_loop_router.automatic_source(sources)
            props['play.best'] = 'Best source: ' + ' · '.join(v for v in (best.get('addon'),best.get('quality'),best.get('language')) if v)
        except Exception:
            props['play.best'] = ''
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
    props.update(info_props(game,info,view,now,offset))
    return props,sources


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
            self.info = None
            self.view = 0
            threading.Thread(target=self.load_info,daemon=True).start()
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
                    if clock()-last>=30:
                        with self.lock:
                            if self.stop.is_set():return
                            self.draw()
                        self.refresh(reload=False)
                        last=clock()
            threading.Thread(target=tick,daemon=True).start()

        def draw(self,error=False):
            searching = bool(self.search_token and getattr(provider,'searching_game',lambda *args:False)(game_id,self.search_token))
            props,self.sources = model(self.data,clock(),sm.device_offset(clock()),'error' if error else 'ready',searching,
                                       sr.get(xbmcvfs.translatePath('special://profile/'),game_id),self.info,self.view)
            if self.search_failed and not self.sources:
                props['state']='error';props['error.title']="Can't search for sources right now"
            for key,value in props.items():
                # The tap handler also writes play.error; a refresh must still clear it.
                if key=='play.error' or getattr(self,'_shown',{}).get(key)!=value:self.setProperty(key,value)
            self._shown = props.copy()

        def load_info(self):
            try:facts = info_mod.build(self.data)
            except Exception as error:
                log('sports: game info: %s: %s' % (type(error).__name__,diagnostics.error_text(error)))
                return
            with self.lock:
                if self.stop.is_set():return
                self.info = facts
                self.draw()

        def refresh(self, reload=True):
            with self.lock:
                if self.fetching:return
                self.fetching=True
            def fetch():
                try:
                    if reload: provider.refresh()
                    current=provider.game(game_id)
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
            elif ident in (page.STANDINGS_SWITCH,page.STANDINGS_SWITCH_BACK):
                with self.lock:
                    self.view = 1 if ident==page.STANDINGS_SWITCH else 0
                    self.draw()
            elif ident==page.AUTO:
                with self.lock: sources=list(self.sources)
                if sources:
                    import sports_loop_router
                    self.start_play(sports_loop_router.automatic_source(sources))
            elif page.SOURCE<=ident<page.SOURCE+page.SLOTS*len(page.FORMS):
                n=(ident-page.SOURCE)//len(page.FORMS)
                with self.lock:source=self.sources[n] if n<len(self.sources) else None
                if source is not None:self.start_play(source)

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
