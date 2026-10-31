"""The portrait tab bar as a native Liquid Glass view, from Kodi.app/Frameworks/KodiGlassBar.framework
(migration/glassbar-ios). Kodi's OpenGL skin cannot blur or refract what is behind it; this bar can.
While it shows, the skin hides its own tab bar (Window(Home).Property(Portrait.GlassBar))."""
import os
PAGES=[('home','Home'),('1102','Movies'),('1101','TV'),('1103|1104','Library'),('1105','Search')]
ACTIONS=['ReplaceWindow(Home)','ReplaceWindow(1102)','ReplaceWindow(1101)','ReplaceWindow(1103)','ReplaceWindow(1105)']
PROPERTY='Portrait.GlassBar'

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
 for index,(windows,_) in enumerate(PAGES):
  if visible(' | '.join('Window.IsActive(%s)'%w for w in windows.split('|'))):return index
 return None

def controller(lib,visible,portrait,set_property,invoke):
 """tick(): show the bar on the tab pages in portrait and mark the page; poll(): run a tapped tab."""
 state={'shown':False,'page':None}
 def tick():
  index=page(visible) if portrait() else None
  show=index is not None
  if index is not None and index!=state['page']:lib.kodi_glassbar_select(index)
  state['page']=index
  if show!=state['shown']:
   state['shown']=show;set_property(PROPERTY,'1' if show else '');lib.kodi_glassbar_show(int(show))
 def poll():
  tapped=lib.kodi_glassbar_take_tap()
  if 0<=tapped<len(ACTIONS) and tapped!=state['page']:invoke(ACTIONS[tapped])
 def close():
  if state['shown']:lib.kodi_glassbar_show(0);set_property(PROPERTY,'')
 return tick,poll,close
