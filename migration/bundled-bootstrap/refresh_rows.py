"""RunScript(service.kodi.ios.bootstrap,refresh_rows,tab=<home|movies|tv>): the refresh button in the Home, Movies and
TV headers (round 5, portrait.refresh_button).

The tab's TMDb Helper rows and its hero move to the next page of their lists (portrait.next_page: 2, 3 ... then the
first again); Continue Watching, Up Next and library rows stay as they are. The tab's copies (listing cache) are turned
off so the new page shows at once; the service makes copies of the new page later (portrait.cache_lists). While the rows
load, Window(Home).Property(Portrait.Refreshing) is the tab (the arrow spins); then 'done.<tab>' for a moment ("New
picks on Home")."""
import importlib.util,os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
PROPERTY='Portrait.Refreshing'
TABS=('home','movies','tv')
SETTLE=1.0          # seconds before asking whether the rows are loading (Kodi starts them after the path changes)
LOADING_LIMIT=25.0  # never spin for longer than this
DONE_FOR=2.5        # how long the tick and "New picks" stay


def tab_from(args):
 """'tab=movies' (or 'movies') -> 'movies'; anything else -> 'home'."""
 for a in args:
  value=a.split('=',1)[1] if a.startswith('tab=') else a
  if value in TABS:return value
 return 'home'


def portrait_module():
 spec=importlib.util.spec_from_file_location('portrait_refresh',os.path.join(HERE,'resources','lib','portrait.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module


def refresh(tab,profile,info,visible,run,prop,set_prop,wait,portrait,clock):
 """One press. info/visible: xbmc.getInfoLabel/getCondVisibility; run: xbmc.executebuiltin; prop/set_prop: the Home
 window's properties; wait(seconds) True when Kodi is closing. Returns the page now shown (1 = the first)."""
 if prop(PROPERTY)==tab:return None   # a second press while it loads
 set_prop(PROPERTY,tab)
 try:
  page=portrait.next_page(info(portrait.page_of(tab)))
  keys,ids=portrait.tab_lists(profile,tab)
  # The copies hold the old page: off, so the rows load the new page live now (the service copies it later).
  for key in keys:run('Skin.Reset(%s%s)'%(portrait.CACHE_FLAG,key))
  if page<=1:run('Skin.Reset(%s)'%(portrait.PAGE_STRING%tab))
  else:run('Skin.SetString(%s,%d)'%(portrait.PAGE_STRING%tab,page))
  if wait(SETTLE):return page
  loading=' | '.join('Container(%d).IsUpdating'%i for i in ids)
  started=clock()
  while loading and visible(loading) and clock()-started<LOADING_LIMIT:
   if wait(0.25):return page
  set_prop(PROPERTY,'done.'+tab)
  if wait(DONE_FOR):return page
  return page
 finally:
  if prop(PROPERTY) in (tab,'done.'+tab):set_prop(PROPERTY,'')


def run(args=()):
 import time,xbmc,xbmcgui,xbmcvfs
 home=xbmcgui.Window(10000);monitor=xbmc.Monitor()
 page=refresh(tab_from(args),xbmcvfs.translatePath('special://profile/'),xbmc.getInfoLabel,xbmc.getCondVisibility,
              xbmc.executebuiltin,home.getProperty,home.setProperty,monitor.waitForAbort,portrait_module(),time.monotonic)
 if page is not None:xbmc.log('Kodi iOS refresh rows: %s now shows page %d'%(tab_from(args),page),xbmc.LOGINFO)

if __name__=='__main__':run(sys.argv[1:])
