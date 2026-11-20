"""The approved Sports Leagues list. Data and ordering come only from the shared Sports contract/provider."""
import os
import re
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import choice_sheet
import page_wait
import sports_model as sm
import sports_provider
import sports_leagues_page as page
import sports_filter as sf

_CACHE = None
BACK_KEYS = (9,10,92,110)


def _lines(text, width):
    words = ' '.join(word[n:n+width] for word in text.split() for n in range(0,len(word),width))
    return choice_sheet.lines(words,width)


def model(leagues, updated, now, offset, state='ready', logos=None):
    """Flat grouped rows for Kodi; order, live counts and next-game wording remain the shared helpers' decisions."""
    props = {'state':state,'subtitle':'%s · %s' % (sm.count_text(len(leagues),'league'),
             sm.updated_text(updated,now,offset).lower()) if updated else 'Updating',
             'error.title':'','error.text.0':'','error.text.1':'','empty.text':''}
    rows = []
    for sport, entries in sm.order_leagues(leagues):
        for n, league in enumerate(entries):
            live, nxt = sm.league_detail(league,now,offset)
            plain = ' · '.join(s for s in (live,nxt) if s) or 'Nothing coming up'
            detail = ' · '.join(s for s in ('[COLOR FFFF453A]%s[/COLOR]'%live if live else '',nxt) if s) or plain
            title_lines,detail_lines = _lines(league['name'],22),_lines(plain,30)
            form = page.FORMS.index((title_lines,detail_lines))
            rows.append({'league':league,'sport':sport if n==0 else '',
                         'sport.count':sm.count_text(len(entries),'league') if n==0 else '',
                         'firstsport':'true' if not rows else '', 'code':league['code'],'title':league['name'],
                         'logo':(logos or {}).get(league['code'],''),
                         'live':live,'next':nxt,'detail':detail,'form':str(form),
                         'pos':'only' if len(entries)==1 else 'first' if n==0 else 'last' if n==len(entries)-1 else 'mid'})
    for n in range(page.SLOTS):
        row = rows[n] if n<len(rows) else {}
        for key in ('sport','sport.count','firstsport','code','title','logo','live','next','detail','form','pos'):
            props['row.%d.%s'%(n,key)] = row.get(key,'')
    if state=='loading' and not rows:
        for n in range(3):
            props['row.%d.form'%n]='0'
            props['row.%d.pos'%n]='first' if n==0 else 'last' if n==2 else 'mid'
    elif state=='error':
        props.update(subtitle='Not updated',**{'error.title':'Can’t load leagues right now',
                     'error.text.0':'The sports add-ons didn’t answer.',
                     'error.text.1':'Check the connection, then try again.'})
    elif not rows:
        props['empty.text']='No leagues listed'
    return props,rows


def open_league(code, log):
    """Until the separately owned league page is installed and registered, a tap only logs its contract route."""
    log('sports: league %s'%code)
    import default as dispatcher
    if (not re.fullmatch(r'[A-Za-z0-9_-]+',str(code)) or 'sports_league' not in dispatcher.PAGES or
            not os.path.isfile(os.path.join(HERE,'sports_league.py'))):
        return
    import xbmc
    xbmc.executebuiltin('RunScript(service.kodi.ios.bootstrap,sports_league,%s)'%code)


def run(args=(), provider=None, clock=time.time, on_league=None, seed=None):
    import xbmc
    import xbmcgui
    import xbmcvfs
    import diagnostics
    global _CACHE
    provider = provider or sports_provider.get()
    on_league = on_league or open_league
    log = lambda text:xbmc.log(text,xbmc.LOGINFO)

    class Leagues(xbmcgui.WindowXMLDialog):
        def onInit(self):
            if hasattr(self,'stop'):return  # A child page returning keeps the list's focus and its one timer.
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.fetching = False
            self.failed = False
            self.data = seed if seed is not None else _CACHE
            self.logos = {}
            self.draw()
            self.refresh(reload=False)
            import sports_fresh
            sports_fresh.start(provider,self.stop,lambda:self.refresh(reload=False))
            def tick():
                monitor=xbmc.Monitor()
                last=clock()
                while not page_wait.idle(self.stop,monitor,1):
                    if clock()-last>=30:
                        with self.lock:
                            if self.stop.is_set():return
                            self.draw()
                        last=clock()
            threading.Thread(target=tick,daemon=True).start()

        def draw(self,error=None):
            if error is not None:self.failed=error
            leagues,updated = self.data if self.data is not None else ([],0)
            props,self.rows = model(leagues,updated,clock(),sm.device_offset(clock()),
                                   'error' if self.failed and self.data is None else 'ready' if self.data is not None else 'loading',
                                   logos=self.logos)
            props.update(sf.edit_state(provider))
            for key,value in props.items():self.setProperty(key,value)

        def refresh(self, reload=True):
            with self.lock:
                if self.fetching:return
                self.fetching=True
            def fetch():
                global _CACHE
                try:
                    if reload:provider.refresh()
                    data=(provider.leagues(),provider.overview()['updated'])
                    with self.lock:
                        if self.stop.is_set():return
                        self.data=_CACHE=data
                        self.draw(error=False)
                    # Real league logos: fetched once, kept on the phone; the rows draw first and gain them a moment later.
                    try:
                        import sports_logos
                        found=sports_logos.paths(xbmcvfs.translatePath('special://profile/'),[l['code'] for l in data[0]])
                        with self.lock:
                            if not self.stop.is_set():
                                self.logos=found
                                self.draw()
                    except Exception as error:
                        log('sports: league logos: %s'%type(error).__name__)
                except Exception as error:
                    log('sports: leagues refresh: %s: %s'%(type(error).__name__,diagnostics.error_text(error)))
                    with self.lock:
                        if not self.stop.is_set():self.draw(error=True)
                finally:
                    with self.lock:self.fetching=False
            threading.Thread(target=fetch,daemon=True).start()

        def onClick(self,ident):
            if ident==page.BACK:self.finish()
            elif ident in (page.REFRESH,page.RETRY):self.refresh()
            elif ident==page.edit_button.ID:
                import sports_edit
                if sports_edit.run():self.refresh(reload=False)
            elif page.ROW<=ident<page.ROW+page.SLOTS*len(page.FORMS):
                n=(ident-page.ROW)//len(page.FORMS)
                with self.lock:league=self.rows[n]['league'] if n<len(self.rows) else None
                if league is not None:on_league(league['code'],log)

        def onAction(self,action):
            if action.getId() in BACK_KEYS:self.finish()

        def finish(self):
            with self.lock:
                self.stop.set()
                self.close()

    try:window=Leagues(page.WINDOW,HERE,'Default','1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
        window=Leagues(page.WINDOW,HERE,'Default','1080i')
    window.doModal()
    if hasattr(window,'stop'):window.stop.set()
    del window


if __name__=='__main__':run(sys.argv[1:])
