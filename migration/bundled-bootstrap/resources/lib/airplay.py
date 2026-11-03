"""Apple's AirPlay button over Kodi, from Kodi.app/Frameworks/KodiAirPlay.framework (migration/airplay-ios)."""
import os
# Full-screen video or music only: on Fuse's menus the top-right corner holds the clock and the gear.
PLAYING='Player.HasMedia + [Window.IsActive(fullscreenvideo) | Window.IsActive(visualisation)]'

def library_path(xbmc_home):
 """special://xbmc lies inside Kodi.app; the framework sits in Kodi.app/Frameworks."""
 app=str(xbmc_home).rstrip('/')
 while app and not app.endswith('.app') and os.path.dirname(app)!=app:app=os.path.dirname(app)
 path=os.path.join(app,'Frameworks','KodiAirPlay.framework','KodiAirPlay')
 return path if app.endswith('.app') and os.path.isfile(path) else None

def load(path):
 import ctypes
 lib=ctypes.CDLL(path);lib.kodi_airplay_show.argtypes=[ctypes.c_int];lib.kodi_airplay_show.restype=None
 lib.kodi_airplay_open.argtypes=[];lib.kodi_airplay_open.restype=None
 if hasattr(lib,'kodi_airplay_play'):lib.kodi_airplay_play.argtypes=[ctypes.c_char_p,ctypes.c_char_p];lib.kodi_airplay_play.restype=None
 # r3: whether Apple's player could open the stream (0 idle/loading, 1 playing, -1 failed), closing it, and keeping
 # Kodi awake in the background (background.py).
 if hasattr(lib,'kodi_airplay_state'):lib.kodi_airplay_state.argtypes=[];lib.kodi_airplay_state.restype=ctypes.c_int
 if hasattr(lib,'kodi_airplay_close'):lib.kodi_airplay_close.argtypes=[];lib.kodi_airplay_close.restype=None
 # r5: MKV/AVI/WebM/TS converted on the phone for AirPlay; why it could not play, for the screen.
 if hasattr(lib,'kodi_airplay_message'):lib.kodi_airplay_message.argtypes=[ctypes.c_char_p,ctypes.c_int];lib.kodi_airplay_message.restype=ctypes.c_int
 if hasattr(lib,'kodi_background_keep'):lib.kodi_background_keep.argtypes=[ctypes.c_int];lib.kodi_background_keep.restype=None
 return lib

def converts(lib):
 """r5 frameworks convert MKV, AVI, WebM and MPEG-TS for AirPlay on the phone."""
 return hasattr(lib,'kodi_airplay_message')

def message(lib):
 """The framework's reason AirPlay could not play the last stream ('' when none or an older framework)."""
 if not converts(lib):return ''
 import ctypes
 buffer=ctypes.create_string_buffer(400)
 lib.kodi_airplay_message(buffer,400)
 return buffer.value.decode('utf-8','replace')

def watch(lib,playing,wait):
 """Shows the button while playing() is true, until wait(seconds) reports Kodi is closing."""
 shown=None
 while True:
  now=bool(playing())
  if now!=shown:lib.kodi_airplay_show(int(now));shown=now
  if wait(0.5):break
 if shown:lib.kodi_airplay_show(0)
