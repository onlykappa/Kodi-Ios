"""Elementum's engine on iOS runs inside Kodi (elementum.framework, loaded by the add-on's service).
running(): whether it answers on its local port. restart(): start it now when this session skipped it.
ensure(): the engine is not started at launch (performance 1E.1: ~300 log lines, a libtorrent listener and a Go
runtime for nothing); whoever needs it asks here. The patched Elementum service (build_customized_ipa.py) waits for
the window property below and then starts the engine in the same session, without restarting the add-on."""
import urllib.error,urllib.request
ADDON='plugin.video.elementum'
URL='http://127.0.0.1:65220/'
WANTED='KodiIOS.ElementumEngine'  # Home window property; the service starts the engine when it reads '1'

def running(url=URL,open_url=urllib.request.urlopen):
 try:open_url(url,timeout=2).close();return True
 except urllib.error.HTTPError:return True  # any HTTP answer: the engine is up
 except Exception:return False

def restart(api,wait,is_running=running,attempts=45):
 """Turn Elementum off and on: Kodi restarts its service, which loads the engine. wait() sleeps ~1 s and returns
 True to give up (Kodi closing or the owner cancelled). Only for a session where the engine is not loaded: the
 Go runtime cannot be started twice in one process."""
 api('Addons.SetAddonEnabled',{'addonid':ADDON,'enabled':False})
 if wait():return False
 api('Addons.SetAddonEnabled',{'addonid':ADDON,'enabled':True})
 for _ in range(attempts):
  if is_running():return True
  if wait():return False
 return False

def ensure(want,wait,is_running=running,attempts=45):
 """True once the engine answers. want() asks the Elementum service to start it (idempotent); wait() sleeps ~1 s and
 returns True to give up. An engine already running costs one local request."""
 if is_running():return True
 want()
 for _ in range(attempts):
  if is_running():return True
  if wait():return False
 return False

def ensure_here(attempts=45,cancel=None):
 """ensure() for code running inside Kodi: the property goes on the Home window, waiting follows Kodi's abort."""
 import xbmc,xbmcgui
 monitor=xbmc.Monitor()
 def wait():
  for _ in range(10):
   if (cancel and cancel()) or monitor.waitForAbort(.1):return True
  return False
 return ensure(lambda:xbmcgui.Window(10000).setProperty(WANTED,'1'),wait,attempts=attempts)
