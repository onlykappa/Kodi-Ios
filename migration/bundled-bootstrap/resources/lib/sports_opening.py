"""Sports-owned opening surface. No fabricated byte speed or percent."""
import json,os,threading,time
import sports_opening_page as page
OWNER='KodiIOS.SportsNativeOwner'

def matchup(source):
    try:
        source=(source.get('native_queue') or [source])[0]
        value=json.loads(source.get('play') or '{}')
        game=value.get('l',{}).get('game',{})
        return '\n'.join(game[side]['name'] for side in ('away','home'))
    except (ValueError,TypeError,KeyError):
        return 'Live game'

class Opening:
    def __init__(self,source,home):
        self.source,self.home=source,home
        self.owner=source.get('native_owner','')
        self.ready=threading.Event();self.closed=threading.Event()
        self.started=threading.Event();self.cancelled=False
        self.began=time.monotonic()

    def open(self):
        import xbmc,xbmcgui,xbmcvfs
        parent=self
        class Surface(xbmcgui.WindowXMLDialog):
            def onInit(self):
                self.setProperty('matchup',matchup(parent.source))
                self.setProperty('stage','Opening your game')
                self.setProperty('detail','Connecting to the selected source.')
                parent.ready.set()
            def onClick(self,control):
                if control==page.CANCEL:parent.cancel()
            def onAction(self,action):
                if action.getId() in (9,10,92,110):parent.cancel()
        class Observer(xbmc.Player):
            def onAVStarted(self):
                if parent.owner and parent.home.getProperty(OWNER)!=parent.owner:return
                import sports_jet
                sports_jet.log('sports: opening surface observed AV start %.3fs after dispatch'%(time.monotonic()-parent.began))
                parent.started.set()
        self.observer=Observer()
        here=os.path.dirname(os.path.dirname(os.path.dirname(xbmcvfs.translatePath(__file__))))
        try:
            self.window=Surface(page.WINDOW,here,'Default','1080i')
        except RuntimeError:
            xbmcvfs.listdir(xbmcvfs.translatePath('special://skin/portrait/'))
            self.window=Surface(page.WINDOW,here,'Default','1080i')
        self.window.show()
        until=time.monotonic()+5
        while not self.ready.is_set() and time.monotonic()<until:
            xbmc.sleep(50)
        if not self.ready.is_set():
            self.close();raise RuntimeError('Sports opening surface did not initialize')
        def tick():
            while not self.closed.wait(.2):
                if self.owner and self.home.getProperty(OWNER)!=self.owner:
                    self.close();return
                if self.started.is_set():self.close();return
                elapsed=int(time.monotonic()-self.began)
                self.window.setProperty('elapsed','%d seconds elapsed'%elapsed)
                if elapsed>=10:self.window.setProperty('detail','This source is taking longer than usual. You can cancel.')
        threading.Thread(target=tick,daemon=True).start()

    def cancel(self):
        import xbmc
        self.cancelled=True
        if self.owner and self.home.getProperty(OWNER)==self.owner:
            self.home.clearProperty(OWNER)
            xbmc.Player().stop()
        self.close()

    def wait(self,timeout=45):
        import xbmc
        until=time.monotonic()+timeout
        while not self.closed.is_set() and not self.started.is_set() and time.monotonic()<until:
            xbmc.sleep(100)
        if not self.started.is_set() and not self.closed.is_set():self.cancel()

    def stage(self,text):
        if not self.closed.is_set():self.window.setProperty('detail',text)

    def close(self):
        if self.closed.is_set():return
        self.closed.set()
        if hasattr(self,'window'):self.window.close()
        self.observer=None
