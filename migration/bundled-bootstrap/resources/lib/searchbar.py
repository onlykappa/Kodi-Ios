"""The Search page's field as a native iOS search field (KodiGlassBar.framework r3), with the results listed under it
as you type, like the Apple TV app. The field sits in a dark band at the top of the screen; portrait.py's Search
window starts its results under that band and shows them while Window(Home).Property(Portrait.Search.Path) holds a
TMDb Helper search (the category tiles show while it is empty)."""
import urllib.parse
PAGE='Window.IsActive(1105)'
PATH='Portrait.Search.Path'    # content of the results grid; '' shows the categories
QUERY='Portrait.Search.Query'  # what was searched, for the page's labels
CHANGED,SUBMITTED,CLOSED=1,2,4
SEARCH='plugin://plugin.video.themoviedb.helper/?info=search&tmdb_type=multi&query='

def results_path(query):
 query=' '.join(str(query or '').split())
 return SEARCH+urllib.parse.quote(query) if query else ''

def bind(lib):
 """Argument types for the r3 functions; False for an older framework without them."""
 import ctypes
 if not hasattr(lib,'kodi_search_take'):return False
 lib.kodi_search_show.argtypes=[ctypes.c_int];lib.kodi_search_show.restype=None
 lib.kodi_search_focus.argtypes=[ctypes.c_int];lib.kodi_search_focus.restype=None
 lib.kodi_search_set.argtypes=[ctypes.c_char_p];lib.kodi_search_set.restype=None
 lib.kodi_search_take.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_search_take.restype=ctypes.c_int
 return True

def taker(lib,size=1024):
 """take() -> (events, text) from the framework."""
 import ctypes
 buffer=ctypes.create_string_buffer(size)
 def take():
  events=lib.kodi_search_take(buffer,size)
  return events,buffer.value.decode('utf-8','replace')
 return take

def controller(lib,take,visible,portrait,set_property,clock,delay=0.45):
 """tick(): show the field on the Search page in portrait (every half second); poll(): read typing (twenty times a
 second) and list the results once typing pauses for `delay` seconds, at once on the Search key; X clears them."""
 state={'shown':False,'text':'','typed':None,'sent':None}
 def send(text):
  query=' '.join(text.split())
  state['typed']=None
  if query==state['sent']:return
  state['sent']=query;set_property(QUERY,query);set_property(PATH,results_path(query))
 def tick():
  show=bool(portrait()) and bool(visible(PAGE)) and not visible('System.HasActiveModalDialog')
  if show!=state['shown']:
   state['shown']=show;lib.kodi_search_show(int(show))
 def poll():
  events,text=take()
  if events&CHANGED:state['text']=text;state['typed']=clock()
  if events&(SUBMITTED|CLOSED):send(text)
  elif state['typed'] is not None and clock()-state['typed']>=delay:send(state['text'])
 def close():
  if state['shown']:lib.kodi_search_show(0);state['shown']=False
 return tick,poll,close
