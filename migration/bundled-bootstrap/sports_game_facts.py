"""The game's facts window (owner mockup page 8): kickoff and venue, recent form, standings; opened from the game page's "Game info" card."""
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

BACK_KEYS = (9,10,92,110)


def info_props(game, info, view, now, offset):
    """The Info section's properties (board D3 / D4): empty strings hide a part."""
    props = {'info.kickoff':'','info.venue':'','info.place':'','st.title':'','st.switch':'','st.n':'','matchup':sm.versus(game) if game else ''}
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



def run(game, clock=time.time):
    import xbmc
    import xbmcgui
    import diagnostics
    log = lambda text:xbmc.log(text,xbmc.LOGINFO)

    class Facts(xbmcgui.WindowXMLDialog):
        def onInit(self):
            if hasattr(self,'stop'):return
            self.stop = threading.Event()
            self.lock = threading.Lock()
            self.info = None
            self.view = 0
            self.draw()
            threading.Thread(target=self.load,daemon=True).start()

        def draw(self):
            props = info_props(game,self.info,self.view,clock(),sm.device_offset(clock()))
            for key,value in props.items():self.setProperty(key,value)

        def load(self):
            try:facts = info_mod.build(game)
            except Exception as error:
                log('sports: game info: %s: %s' % (type(error).__name__,diagnostics.error_text(error)))
                return
            with self.lock:
                if self.stop.is_set():return
                self.info = facts
                self.draw()

        def onClick(self,ident):
            if ident==page.BACK:self.finish()
            elif ident in (page.STANDINGS_SWITCH,page.STANDINGS_SWITCH_BACK):
                with self.lock:
                    self.view = 1 if ident==page.STANDINGS_SWITCH else 0
                    self.draw()

        def onAction(self,action):
            if action.getId() in BACK_KEYS:self.finish()

        def finish(self):
            self.stop.set()
            self.close()

    import xbmcvfs
    try:window = Facts(page.WINDOW,HERE,'Default','1080i')
    except RuntimeError:
        xbmcvfs.listdir(os.path.join(xbmcvfs.translatePath('special://skin/'),'portrait')+'/')
        window = Facts(page.WINDOW,HERE,'Default','1080i')
    window.doModal()
    if hasattr(window,'stop'):window.stop.set()
    del window
