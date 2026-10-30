import json,os,sys
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from bootstrap import initialize,restore

def run():
 import xbmc,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 monitor=xbmc.Monitor()
 # Service starts after Kodi's addon discovery; wait briefly for settings/UI availability.
 if monitor.waitForAbort(2):return
 root=Path(__file__).resolve().parent;profile=Path(xbmcvfs.translatePath('special://profile/'))
 def api(method,params):return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 try:
  if len(sys.argv)>1 and sys.argv[1]=='--recover':
   if xbmcgui.Dialog().yesno('Recover Kodi setup','Restore pre-setup files and return to Estuary?'):restore(profile,api)
   return
  if len(sys.argv)>1 and sys.argv[1]!='':
   if xbmcgui.Dialog().yesno('Kodi setup recovery','Restore pre-setup files and return to Estuary?'):restore(profile,api)
   return
  result=initialize(root/'seed',profile,api)
  if result=='IN PROGRESS':
   restore(profile,api);xbmcgui.Dialog().ok('Setup interrupted','Original files restored. Estuary remains available. Record this failure before retrying.')
 except Exception as error:
  xbmc.log('Kodi iOS setup failed: '+type(error).__name__,xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Kodi setup needs review','Automatic setup failed. Keep Estuary available and report the setup status; no credentials need to be shared.')
if __name__=='__main__':run()
