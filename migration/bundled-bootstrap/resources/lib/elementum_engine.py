"""Elementum's engine on iOS runs inside Kodi (elementum.framework, loaded by the add-on's service).
running(): whether it answers on its local port. restart(): start it now when this session skipped it."""
import urllib.error,urllib.request
ADDON='plugin.video.elementum'
URL='http://127.0.0.1:65220/'

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
