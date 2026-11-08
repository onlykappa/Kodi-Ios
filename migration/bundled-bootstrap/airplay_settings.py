"""Open this app's iOS Settings through the r34 bridge, with instructions on older frameworks."""
import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))

def run():
 import airplay,work_state,xbmcvfs,xbmcgui
 path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
 if path:
  lib=airplay.load(path)
  if hasattr(lib,'kodi_airplay_settings'):
   lib.kodi_airplay_settings();return
 xbmcgui.Dialog().ok('Open Settings',work_state.NEEDS_TEXT['airplay_network']['text'])

if __name__=='__main__':run()
