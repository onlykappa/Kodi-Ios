"""The portrait tab bar as a native Liquid Glass view, from Kodi.app/Frameworks/KodiGlassBar.framework
(migration/glassbar-ios). Kodi's OpenGL skin cannot blur or refract what is behind it; this bar can.
The skin draws its own tab bar only on a phone without this framework (Skin.HasSetting(Portrait.NativeTabBar))."""
import os
# Home, Movies and TV are groups of the Home window, picked by Window(Home).Property(Portrait.Tab) (portrait.py).
TAB='Window(Home).Property(Portrait.Tab)'
PAGES=[('Window.IsActive(home) + String.IsEmpty(%s)'%TAB,'Home'),('Window.IsActive(home) + String.IsEqual(%s,movies)'%TAB,'Movies'),
       ('Window.IsActive(home) + String.IsEqual(%s,tv)'%TAB,'TV'),('Window.IsActive(1103) | Window.IsActive(1104)','Library'),
       ('Window.IsActive(1105)','Search')]
# The tab actions come from portrait.tab_actions (one definition for the skin tab bar and this one).

def library_path(xbmc_home):
 """special://xbmc lies inside Kodi.app; the framework sits in Kodi.app/Frameworks."""
 app=str(xbmc_home).rstrip('/')
 while app and not app.endswith('.app') and os.path.dirname(app)!=app:app=os.path.dirname(app)
 path=os.path.join(app,'Frameworks','KodiGlassBar.framework','KodiGlassBar')
 return path if app.endswith('.app') and os.path.isfile(path) else None

def load(path):
 import ctypes
 lib=ctypes.CDLL(path)
 lib.kodi_glassbar_show.argtypes=[ctypes.c_int];lib.kodi_glassbar_show.restype=None
 lib.kodi_glassbar_select.argtypes=[ctypes.c_int];lib.kodi_glassbar_select.restype=None
 lib.kodi_glassbar_take_tap.argtypes=[];lib.kodi_glassbar_take_tap.restype=ctypes.c_int
 return lib

def page(visible):
 """Index of the tab page on screen, or None (another window, or a dialog over it)."""
 if visible('System.HasActiveModalDialog'):return None
 for index,(condition,_) in enumerate(PAGES):
  if visible(condition):return index
 return None

def controller(lib,visible,portrait,invoke,actions,on_show=None):
 """tick(): show the bar on the tab pages in portrait and mark the page; poll(): run a tapped tab."""
 state={'shown':False,'page':None}
 def tick():
  index=page(visible) if portrait() else None
  show=index is not None
  if index is not None and index!=state['page']:lib.kodi_glassbar_select(index)
  state['page']=index
  if show!=state['shown']:
   state['shown']=show;lib.kodi_glassbar_show(int(show))
   if show and on_show:on_show()
 def poll():
  tapped=lib.kodi_glassbar_take_tap()
  if 0<=tapped<len(actions) and tapped!=state['page']:
   for condition,action in actions[tapped]:
    if not condition or visible(condition):invoke(action)
 def close():
  if state['shown']:lib.kodi_glassbar_show(0)
 return tick,poll,close
