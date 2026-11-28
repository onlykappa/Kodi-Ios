"""The game's Info / Standings window (owner mockups page 8 and D1/D2); opened from the game page's "Game info" card. It carries the game page's hero and action
capsule (Remind me opens the reminder sheet; Play closes this window and plays, see `run`) over the two tabs."""
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import page_wait
import sports_model as sm
import sports_game_facts_page as page
import sports_game_info as info_mod
import sports_game_detail as detail_mod
import sports_game as game_page
import sports_reminders as sr

BACK_KEYS = (9,10,92,110)


def info_props(game, info, view, now, offset, tab='stats', crests=None):
    """The Info section's properties (board D3 / D4): empty strings hide a part."""
    props = {'info.kickoff':'','info.when':'Starts','info.venue':'','info.place':'','st.title':'','st.switch':'','st.n':'','matchup':sm.versus(game) if game else ''}
    for n in range(2):
        for key in ('name','line'):props['form.%d.%s' % (n,key)] = ''
        for d in range(info_mod.FORM):props['form.%d.d%d' % (n,d)] = ''
    for i in range(4):props['st.h%d' % i] = ''
    for n in range(page.ST_ROWS):
        for key in ('rank','team','crest','c0','c1','c2','c3','me','pos'):props['st.%d.%s' % (n,key)] = ''
    props['tab'] = tab if tab in ('stats','plays','standings') else 'stats'
    props['strip.kind'] = ''
    props['has.tabs'] = ''
    if game:   # the compact score at the top (teams: crests and scores; an event: its name)
        live = game.get('state') == 'live'
        scores = (game['away'].get('score'),game['home'].get('score'))
        if game['home'].get('name'):
            props.update({'strip.kind':'teams','strip.away':'' if scores[0] is None else str(scores[0]),'strip.home':'' if scores[1] is None else str(scores[1]),
                          'strip.status':'LIVE' if live else sm.day_label(game['start'],now,offset),'strip.tint':'FFFF453A' if live else 'FFFFFFFF',
                          'strip.sub':sm.live_clock(game,now) if live else sm.clock_text(game['start'],offset)})
        else:props.update({'strip.kind':'event','strip.status':'','strip.sub':''})
    if not game or not info:return props
    props['info.when'] = 'Starts' if game.get('state')=='upcoming' else 'Started'
    props['info.kickoff'] = sm.day_label(game['start'],now,offset) + ' · ' + sm.clock_text(game['start'],offset)
    props['info.venue'],props['info.place'] = info.get('venue',''),info.get('place','')
    for n,team in enumerate(info.get('form') or []):
        props['form.%d.name' % n] = team['name']
        props['form.%d.line' % n] = ' · '.join(v for v in (team['record'],('%s %s' % (team['side'],team['split'])) if team['split'] else '') if v)
        for d,letter in enumerate(team['results']):props['form.%d.d%d' % (n,d)] = letter
    table = info.get('standings')
    if table and table['views']:
        props['has.tabs'] = 'true'
        shown = table['views'][view % len(table['views'])]
        props['st.title'] = shown['title']
        if len(table['views']) > 1:props['st.switch'] = 'wild' if shown['name'] == 'Divisional' else 'div'
        for i,label in enumerate(shown['cols']):props['st.h%d' % i] = label
        rows = shown['rows'][:page.ST_ROWS]
        for n,row in enumerate(rows):
            props.update({'st.%d.rank' % n:row['rank'],'st.%d.team' % n:row['team'],'st.%d.crest' % n:row['crest'] if crests is None else crests.get(row['crest'],''),
                          'st.%d.me' % n:'true' if row['me'] else '',
                          'st.%d.pos' % n:'last' if n==len(rows)-1 else 'mid'})
            for i,value in enumerate(row['cols']):props['st.%d.c%d' % (n,i)] = value
    return props



class Section:
    """The game's facts (kickoff, venue, form, ESPN's stats, plays and standings) for a window that shows them: the Info window and, below the sources, the game page (owner,
    2026-11-28: "the game info tabs should be when I scroll down, so we don't need to press Game info"). It loads in background threads and calls `redraw()` (the window
    draws under its own lock) when something arrived; `props()` gives the properties and the bar percentages to set."""

    def __init__(self, game, profile, lock, stop, redraw, log=lambda text:None):
        self.game, self.profile, self.lock, self.stop, self.redraw, self.log = game, profile, lock, stop, redraw, log
        self.info = None
        self.view = 0
        self.tab = 'stats'
        self.detail = None
        self.detail_state = 'loading'
        self.crests = {}

    def start(self):
        for work in (self.load, self.load_detail, self.load_crests):
            threading.Thread(target=work,daemon=True).start()

    def props(self, now, offset):
        props = info_props(self.game,self.info,self.view,now,offset,self.tab,self.crests)
        more,bars = detail_mod.props(self.detail,self.detail_state,self.crests,page.BAR_BASE)
        props.update(more)
        return props,bars

    def load_crests(self,table=True):
        """Real crests (the standings rows once the table is known, the players' team logos): downloaded once, kept on the phone."""
        try:
            import sports_logos
            urls = [self.game[side].get('crest','') for side in ('away','home')]
            if table and self.info and self.info.get('standings'):
                urls += [r['crest'] for v in self.info['standings']['views'] for r in v['rows']]
            urls += detail_mod.logos(self.detail)
            found = sports_logos.crests(self.profile,urls)
            with self.lock:
                if found and not self.stop.is_set():
                    self.crests.update(found)
                    self.redraw()
        except Exception as error:self.log('sports: crests: %s' % type(error).__name__)

    def load_detail(self):
        """ESPN's summary of the game (stats, plays); again every 25 s while the game is live and the window is open."""
        while not self.stop.is_set():
            try:found = detail_mod.fetch(self.game)
            except Exception:found = None
            with self.lock:
                if self.stop.is_set():return
                changed = found is not None and found != self.detail
                if found is not None:self.detail,self.detail_state = found,'ready'
                elif self.detail is None:self.detail_state = 'none'
                self.redraw()
            if changed:self.load_crests(table=False)
            if self.game.get('state')!='live':return
            if self.stop.wait(detail_mod.TTL_LIVE):return

    def load(self):
        try:facts = info_mod.build(self.game)
        except Exception as error:
            self.log('sports: game info: %s: %s' % (type(error).__name__,self.error_text(error)))
            return
        with self.lock:
            if self.stop.is_set():return
            self.info = facts
            self.redraw()
        self.load_crests()

    @staticmethod
    def error_text(error):
        import diagnostics
        return diagnostics.error_text(error)

    def click(self, ident, tabs=None):
        """True when `ident` was one of this section's controls (a tab or the Divisional / Wild Card switch); the caller holds no lock."""
        if ident in (page.STANDINGS_SWITCH,page.STANDINGS_SWITCH_BACK):
            with self.lock:
                self.view = 1 if ident==page.STANDINGS_SWITCH else 0
                self.redraw()
            return True
        stats,plays,table = tabs or (page.TAB_INFO,page.TAB_PLAYS,page.TAB_STANDINGS)
        ident = ident-page.TAB_ALT if ident in (stats+page.TAB_ALT,plays+page.TAB_ALT) else ident
        if ident in (stats,plays,table):
            with self.lock:
                self.tab = {table:'standings',plays:'plays'}.get(ident,'stats')
                self.redraw()
            return True
        return False


def run(game, clock=time.time):
    """Open the window. Returns True when Play was tapped (the caller plays the game's best source)."""
    import xbmc
    import xbmcgui
    import xbmcvfs
    log = lambda text:xbmc.log(text,xbmc.LOGINFO)
    profile = xbmcvfs.translatePath('special://profile/')
    answer = {'play':False}

    class Facts(xbmcgui.WindowXMLDialog):
        def onInit(self):
            if hasattr(self,'stop'):return
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.section = Section(game,profile,self.lock,self.stop,self.draw,log)
            self.draw()
            self.section.start()

        def draw(self):
            now = clock()
            offset = sm.device_offset(now)
            props,_ = game_page.model(game,now,offset,'ready',False,sr.get(profile,game['id']),now,self.section.crests)
            more,bars = self.section.props(now,offset)
            props.update(more)
            for key,value in props.items():
                if getattr(self,'_shown',{}).get(key)!=value:self.setProperty(key,value)
            self._shown = props.copy()
            for ident,percent in bars.items():
                try:self.getControl(ident).setPercent(float(percent))
                except Exception:pass

        def onClick(self,ident):
            if ident==page.BACK:self.finish()
            elif self.section.click(ident):pass
            elif ident in (page.REMIND,page.REMIND_ON):
                import sports_remind
                sports_remind.ask(game,profile)
                with self.lock:self.draw()
            elif ident==page.AUTO:
                answer['play'] = True
                self.finish()

        def onAction(self,action):
            if action.getId() in BACK_KEYS:self.finish()

        def finish(self):
            self.stop.set()
            self.close()

    try:window = Facts(page.WINDOW,HERE,'Default','1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
        window = Facts(page.WINDOW,HERE,'Default','1080i')
    window.doModal()
    if hasattr(window,'stop'):window.stop.set()
    del window
    return answer['play']
