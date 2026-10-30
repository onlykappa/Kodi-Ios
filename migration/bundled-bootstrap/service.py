import json,os,sys,time
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from bootstrap import initialize,restore

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
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
  def verify_skin():
   start=time.monotonic()
   while time.monotonic()-start<20:
    if monitor.waitForAbort(0.25):return False
    if time.monotonic()-start>3 and xbmc.getSkinDir()=='skin.arctic.fuse.3' and not xbmc.getCondVisibility('Window.IsActive(yesnodialog)'):return True
   return False
  def refresh(paths):
   xbmc.executebuiltin('UpdateLocalAddons',True)
   for expected in paths:
    actual=Path(xbmcvfs.translatePath(xbmcaddon.Addon(expected.name).getAddonInfo('path'))).resolve()
    if actual!=expected.resolve():raise RuntimeError('Kodi did not select the writable skin copy')
  home=Path(xbmcvfs.translatePath('special://home/'))
  result=initialize(root/'seed',profile,api,verify_skin=verify_skin,home=home,refresh=refresh)
  if result=='IN PROGRESS':
   restore(profile,api);xbmcgui.Dialog().ok('Setup interrupted','Original files restored. Estuary remains available. Record this failure before retrying.')
 except Exception as error:
  xbmc.log('Kodi iOS setup failed: '+type(error).__name__,xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Kodi setup needs review','Automatic setup failed. Keep Estuary available and report the setup status; no credentials need to be shared.')
if __name__=='__main__':run()
