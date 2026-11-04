"""Lightweight owner of the native tab bar/search field, independent of setup, feeds and layout generation."""
import time
import glassbar,ios_tabs

NATIVE_TAB_BAR='Portrait.NativeTabBar'

def run(xbmc,xbmcvfs,monitor,fuse='skin.arctic.fuse.3'):
 started=time.monotonic();close=None;find_close=None
 xbmc.log('Kodi iOS startup: native UI worker entered',xbmc.LOGINFO)
 try:
  path=glassbar.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if not path:
   if xbmc.getCondVisibility('Skin.HasSetting(%s)'%NATIVE_TAB_BAR):xbmc.executebuiltin('Skin.Reset(%s)'%NATIVE_TAB_BAR)
   return
  lib=glassbar.load(path)
  if not xbmc.getCondVisibility('Skin.HasSetting(%s)'%NATIVE_TAB_BAR):xbmc.executebuiltin('Skin.SetBool(%s)'%NATIVE_TAB_BAR)
  def portrait():
   if xbmc.getSkinDir()!=fuse:return False
   try:return int(xbmc.getInfoLabel('System.ScreenHeight'))>int(xbmc.getInfoLabel('System.ScreenWidth'))
   except (ValueError,TypeError):return False
  logged=False
  def shown():
   nonlocal logged
   if not logged:
    logged=True;xbmc.log('Kodi iOS startup: native tab bar show requested +%.3fs (UI worker clock)'%(time.monotonic()-started),xbmc.LOGINFO)
  bar,poll,close=glassbar.controller(lib,xbmc.getCondVisibility,portrait,xbmc.executebuiltin,
                                  [ios_tabs.tab_actions(t[0]) for t in ios_tabs.TABS],on_show=shown)
  # Before search/GUI imports, feed add-on lookup, setup, portrait generation or the first polling wait.
  bar()
  ticks=[bar];polls=[poll]
  try:
   import searchbar
   if searchbar.bind(lib):
    import xbmcgui
    home=xbmcgui.Window(10000)
    find,typed,find_close=searchbar.controller(lib,searchbar.taker(lib),xbmc.getCondVisibility,portrait,
                                             home.setProperty,time.monotonic,info=xbmc.getInfoLabel)
    home.setProperty('Portrait.SearchBar','1');ticks.append(find);polls.append(typed)
  except Exception as error:xbmc.log('Kodi iOS search field unavailable: '+type(error).__name__,xbmc.LOGWARNING)
  playing=False;count=0
  while not monitor.waitForAbort(0.5 if playing else 0.05):
   count+=1
   if playing or count%10==0:
    playing=bool(xbmc.getCondVisibility('Window.IsActive(fullscreenvideo)'))
    for tick in ticks:tick()
   if not playing:
    for take in polls:take()
 except Exception as error:
  xbmc.log('Kodi iOS native UI unavailable: '+type(error).__name__,xbmc.LOGWARNING)
  xbmc.executebuiltin('Skin.Reset(%s)'%NATIVE_TAB_BAR)
 finally:
  if find_close:find_close()
  if close:close()
