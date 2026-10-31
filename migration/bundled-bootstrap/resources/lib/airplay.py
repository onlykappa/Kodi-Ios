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
 return lib

def watch(lib,playing,wait):
 """Shows the button while playing() is true, until wait(seconds) reports Kodi is closing."""
 shown=None
 while True:
  now=bool(playing())
  if now!=shown:lib.kodi_airplay_show(int(now));shown=now
  if wait(0.5):break
 if shown:lib.kodi_airplay_show(0)
