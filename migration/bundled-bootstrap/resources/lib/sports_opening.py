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

def game_of(source):
    """The game dict a Sports play carries ({} when it carries none)."""
    try:
        first=(source.get('native_queue') or [source])[0]
        game=json.loads(first.get('play') or '{}').get('l',{}).get('game',{})
        return game if isinstance(game,dict) else {}
    except (ValueError,TypeError,AttributeError):
        return {}


def team_name(team):
    """The name for under a crest, never cut (DEC-050): ESPN's short name, else the full name, else its last word ("Bucks", "76ers"), else the team's code, the
    first that measures under the column at the card's size; the code, then the last word, when nothing does."""
    import notifications_skin
    team = team or {}
    full = str(team.get('name') or '').strip()
    short = str(team.get('short') or '').strip()
    last = full.split(' ')[-1] if full else ''
    code = str(team.get('code') or '').strip()
    for name in (short, full, last, code):
        if name and notifications_skin.text_width(name, page.NAME_SIZE, True) <= page.NAME_FIT:
            return name
    return code or last or short or full


def dark_crest(team):
    """The team's crest address in ESPN's dark-background version (`500-dark`): a dark crest such as Michigan State's green vanishes on the card's dark grey."""
    url = str((team or {}).get('crest') or '')
    return url.replace('/500/', '/500-dark/', 1) if '/teamlogos/' in url else url


def crest_url(team):
    import sports_rows
    return sports_rows.crest_url({'crest': dark_crest(team)})


def enrich(game):
    """A game whose teams lack short names, codes or crests (a link saved before they were kept) is looked up in ESPN's saved answer by its team names; the game
    as it was when nothing matches. Never raises."""
    try:
        teams = [game.get(side) or {} for side in ('away', 'home')]
        if all(t.get('short') and t.get('crest') for t in teams) and game.get('state'):
            return game
        import sports_provider
        provider = sports_provider.get()
        names = [str(t.get('name') or '').casefold() for t in teams]
        for known in list(provider.live_games()) + list(provider.upcoming_games()):
            if [str((known.get(side) or {}).get('name') or '').casefold() for side in ('away', 'home')] == names:
                return dict(game, state=known.get('state') or game.get('state') or '', away=dict(teams[0], **known['away']), home=dict(teams[1], **known['home']))
    except Exception:
        pass
    return game


def details(source,crests=None):
    """{property: value} for the card's game: live, tag, and each side's name, code and crest file (`crests`: {crest address: file} of crests already on the phone)."""
    game=enrich(game_of(source));crests=crests or {};props={'live':'1' if game.get('state')=='live' else '','tag':str(game.get('league') or '')[:12]}
    for side in ('away','home'):
        team=game.get(side) if isinstance(game.get(side),dict) else {}
        props[side+'.name']=team_name(team) if team else ''
        props[side+'.code']=str(team.get('code') or team.get('name') or '')[:4].upper() if team else ''
        props[side+'.logo']=crests.get(crest_url(team),'') if team else ''
    return props


def clock_text(seconds):
    return '%d:%02d'%(int(seconds)//60,int(seconds)%60)


SLOW=10
FAILED_STAGE,FAILED_SUB='This game didn’t open','None of its sources worked.'


def sub_text(elapsed,choice='',slow=False):
    """'Source 1 of 2 · 0:03' (the source part only when the queue has more than one); '... · You can cancel' once the wait is long."""
    parts=['Source %s of %s'%tuple(choice.split('/'))] if choice else []
    parts.append(clock_text(elapsed))
    if slow:parts.append('You can cancel')
    return ' · '.join(parts)


class Opening:
    def __init__(self,source,home):
        self.source,self.home=source,home
        self.owner=source.get('native_owner','')
        self.ready=threading.Event();self.closed=threading.Event()
        self.started=threading.Event();self.cancelled=False;self.dismissed=threading.Event();self.failed=False
        self.began=time.monotonic()
        self.stage_text='Connecting to the source'
        self.total=len(source.get('native_queue') or [])

    def open(self):
        import xbmc,xbmcgui,xbmcvfs
        parent=self
        class Surface(xbmcgui.WindowXMLDialog):
            def onInit(self):
                self.setProperty('matchup',matchup(parent.source))
                for key,value in details(parent.source).items():self.setProperty(key,value)
                self.setProperty('at','at')
                self.setProperty('stage',parent.stage_text);self.setProperty('sub',sub_text(0,parent.choice()))
                parent.ready.set()
            def onClick(self,control):
                if control==page.CANCEL:parent.cancel()
                elif control==page.BACK:parent.dismissed.set()
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
                try:   # this card is the loader: Crew's own busy circle drew over its text (owner, build 618)
                    for name in ('busydialognocancel','busydialog'):
                        if xbmc.getCondVisibility('Window.IsVisible(%s)'%name):xbmc.executebuiltin('Dialog.Close(%s)'%name)
                except Exception:pass
                if self.failed:continue
                elapsed=time.monotonic()-self.began;slow=elapsed>=SLOW
                self.window.setProperty('stage','Taking longer than usual' if slow else self.stage_text)
                self.window.setProperty('sub',sub_text(elapsed,self.choice(),slow))
        threading.Thread(target=tick,daemon=True).start()
        threading.Thread(target=self.crests,daemon=True).start()

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
        """The stage line (the router's and the player's words, short and plain); the clock and the source count are added by the tick."""
        self.stage_text=text
        if not self.closed.is_set() and not self.failed and hasattr(self,'window'):self.window.setProperty('stage',text)

    def choice(self):
        """'n/m' of the source being tried, from the router (Home property), '' when there is only one."""
        try:
            value=self.home.getProperty('KodiIOS.SportsOpeningChoice') or ''
            n,m=value.split('/');return value if int(m)>1 and 0<int(n)<=int(m) else ''
        except (ValueError,AttributeError):
            return ''

    def crests(self):
        """The crests already on the phone (the hub and the lists fetched them), given to the card as they are found; the team's code shows until then."""
        try:
            import xbmcvfs,sports_logos,sports_rows
            profile=xbmcvfs.translatePath('special://profile/')
            game=enrich(game_of(self.source));urls=[crest_url(game.get(side) or {}) for side in ('away','home')]
            found=sports_logos.crests(profile,urls)
            if found and not self.closed.is_set():
                for key,value in details(self.source,found).items():
                    if key.endswith('.logo') and value:self.window.setProperty(key,value)
        except Exception:pass

    def fail(self,wait=60):
        """Every source failed: say so on the card (one button, Back to Sports) and wait for it, at most `wait` seconds. Returns True when the card was shown."""
        if self.closed.is_set() or self.cancelled or not hasattr(self,'window'):return False
        self.failed=True
        try:
            self.window.setProperty('stage',FAILED_STAGE);self.window.setProperty('sub',FAILED_SUB);self.window.setProperty('failed','1')
            try:self.window.setFocusId(page.BACK)
            except Exception:pass
        except Exception:return False
        self.dismissed.wait(wait)
        return True

    def close(self):
        if self.closed.is_set():return
        self.closed.set()
        if hasattr(self,'window'):self.window.close()
        self.observer=None
