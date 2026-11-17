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

BACK_KEYS = (9,10,92,110)


def _lines(text, width):
    # Count long words too: a name such as Mönchengladbach wraps inside its team column.
    words = ' '.join(word[n:n+width] for word in text.split() for n in range(0,len(word),width))
    return choice_sheet.lines(words,width)


def model(game, now, offset, state='ready'):
    """Project the contract without losing source identities or opaque play values."""
    props = {'state':state,'hero.lines':'','league':'','starts':'','clock':'','day':'',
             'sources.count':'','error.title':'','play.error':''}
    sources = sm.order_sources(game['sources']) if game else []
    for side in ('away','home'):
        for key in ('code','name','crest'):props[side+'.'+key] = game[side].get(key,'') if game else ''
    if game:
        props.update({'hero.lines':str(max(_lines(game[side]['name'],11) for side in ('away','home'))),
                      'league':game['league'],'starts':sm.start_text(game['start'],now,offset),
                      'clock':sm.clock_text(game['start'],offset),'day':sm.day_label(game['start'],now,offset),
                      'sources.count':str(len(sources)) if sources else '',
                      'state':'ready' if sources else 'empty'})
    elif state=='error':props['error.title']="Can't load this game right now"
    elif state=='loading':props.update({'hero.lines':'1'})
    else:props.update(state='gone',**{'error.title':'This game is no longer listed'})
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


def run(game, provider=None, clock=time.time):
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
            self.draw()
            self.refresh()
            def tick():
                monitor=xbmc.Monitor()
                last=clock()
                while not page_wait.idle(self.stop,monitor,1):
                    if clock()-last>=30:
                        with self.lock:
                            if self.stop.is_set():return
                            self.draw()
                        self.refresh(reload=False)
                        last=clock()
            threading.Thread(target=tick,daemon=True).start()

        def draw(self,error=False):
            props,self.sources = model(self.data,clock(),sm.device_offset(clock()),'error' if error else 'ready')
            for key,value in props.items():
                # The tap handler also writes play.error; a refresh must still clear it.
                if key=='play.error' or getattr(self,'_shown',{}).get(key)!=value:self.setProperty(key,value)
            self._shown = props.copy()

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
            elif ident in (page.REFRESH,page.RETRY):self.refresh()
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

        def onAction(self,action):
            if action.getId() in BACK_KEYS:self.finish()

        def finish(self):
            with self.lock:
                self.stop.set()
                self.close()

    try:window=Game(page.WINDOW,HERE,'Default','1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
        window=Game(page.WINDOW,HERE,'Default','1080i')
    window.doModal()
    if hasattr(window,'stop'):window.stop.set()
    del window
