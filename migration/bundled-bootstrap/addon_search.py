"""Search add-ons (RunScript(service.kodi.ios.bootstrap,addon_search)): the add-ons page's search field. With the native iOS
search field (glassbar, the same one Settings search uses) the page follows what is typed (resources/lib/addon_search.py);
without it Kodi's own search keyboard opens, as before."""
import os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,os.path.join(HERE,'resources','lib'))
import addon_search

POLL=0.3   # seconds between reads of the field
ACTIVE,QUERY,CLOSE='Settings.Search.Active','Settings.Search.Query','Settings.Search.Close'

def native_field():
 """The glassbar library when it can host a second search (kodi_search_context), else None."""
 import xbmcvfs
 try:
  import glassbar
  path=glassbar.library_path(xbmcvfs.translatePath('special://xbmc/'))
  lib=glassbar.load(path) if path else None
 except Exception:return None
 return lib if lib is not None and hasattr(lib,'kodi_search_context') else None

def run():
 import time,xbmc,xbmcgui
 lib=native_field();home=xbmcgui.Window(10000)
 if lib is None:
  xbmc.executebuiltin('Container.Update(%s,replace)'%addon_search.BASE);return
 home.clearProperty(QUERY);home.clearProperty(CLOSE);home.setProperty(ACTIVE,'1')
 go=lambda address,replace=True:xbmc.executebuiltin('Container.Update(%s%s)'%(address,',replace' if replace else ''))
 # The first step keeps the page you came from in Kodi's history (a replace would leave only the search address, and Back would
 # then climb to addons://search/ and open Kodi's keyboard); the steps after it replace each other.
 go(addon_search.BLANK,False)   # the page for a search, listing nothing yet
 follower=addon_search.Follower(lambda:home.getProperty(QUERY),lambda:xbmc.getInfoLabel('Container.FolderPath'),
                                lambda:home.getProperty(CLOSE)=='1',go,lambda:xbmc.executebuiltin('Action(Back)'),time.monotonic)
 monitor=xbmc.Monitor()
 try:
  while not monitor.waitForAbort(POLL):
   if not follower.tick():break
 finally:
  for key in (ACTIVE,QUERY,CLOSE):home.clearProperty(key)
  lib.kodi_search_focus(0);lib.kodi_search_show(0)

if __name__=='__main__':run()
