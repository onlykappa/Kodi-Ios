import json,os,sys,time
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from bootstrap import initialize,restore,ensure_enabled
from navigation import upgrade,sync_skin_preferences,update_nodes,phone_defaults,REVISION
from startup import generate,failure,LOCK,FUSE
import calibration,updates

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 monitor=xbmc.Monitor()
 if monitor.waitForAbort(2):return
 root=Path(__file__).resolve().parent;profile=Path(xbmcvfs.translatePath('special://profile/')).resolve()
 window=xbmcgui.Window(10000);state={'stage':'prepare'};generated=False
 def stage(value):state['stage']=value
 def api(method,params):return json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
 def invoke(command):xbmc.executebuiltin(command,True)
 def prepare_generated(sync=True):
  nonlocal generated
  stage('skin_preferences')
  if sync:sync_skin_preferences(root/'seed',api,invoke,lambda id,is_bool:xbmc.getCondVisibility('Skin.HasSetting('+id+')') if is_bool else xbmc.getInfoLabel('Skin.String('+id+')'))
  # Before generation, so the rebuilt menus include Drive/recovery in the gear menu.
  stage('phone_menus');update_nodes(profile);phone_defaults(lambda id:xbmc.getInfoLabel('Skin.String('+id+')'),invoke)
  skin=Path(xbmcvfs.translatePath('special://skin/')).resolve()
  if skin.name!=FUSE or not skin.is_relative_to(home):raise RuntimeError('Writable Fuse path not selected')
  generate(skin,xbmc.getSkinDir,invoke,monitor.waitForAbort,xbmc.getInfoLabel('Skin.String(SkinVariables.SkinUser)'),stage)
  generated=True
 try:
  if len(sys.argv)>1 and sys.argv[1]=='--recover':
   if xbmcgui.Dialog().yesno('Recover Kodi setup','Restore pre-setup files and return to Estuary?'):restore(profile,api)
   return
  # The patched Home onloads honor this lock before Settings changes the skin.
  window.setProperty(LOCK,'true')
  def verify_skin():
   stage('await_skin_confirmation');start=time.monotonic()
   while time.monotonic()-start<30:
    if monitor.waitForAbort(0.25):return False
    if time.monotonic()-start>3 and xbmc.getSkinDir()==FUSE and not xbmc.getCondVisibility('Window.IsVisible(yesnodialog)'):
     prepare_generated();return True
   return False
  def refresh(paths):
   invoke('UpdateLocalAddons')
   for expected in paths:
    actual=Path(xbmcvfs.translatePath(xbmcaddon.Addon(expected.name).getAddonInfo('path'))).resolve()
    if actual!=expected.resolve():raise RuntimeError('Kodi did not select the writable skin copy')
  home=Path(xbmcvfs.translatePath('special://home/')).resolve()
  if not profile.is_relative_to(home):raise RuntimeError('Profile is outside the app home')
  navigation=upgrade(home,profile)
  # Load the guarded XML before a legacy completed profile runs its helpers again.
  if navigation.get('changed_files') and xbmc.getSkinDir()==FUSE:invoke('ReloadSkin()')
  stage('initialize')
  result=initialize(root/'seed',profile,api,verify_skin=verify_skin,home=home,refresh=refresh)
  upgrade(home,profile)
  stage('enable_addons')
  for addon in ensure_enabled(root/'seed',profile,api):xbmc.log('Kodi iOS setup enabled bundled add-on '+addon,xbmc.LOGINFO)
  if result=='IN PROGRESS':
   restore(profile,api);xbmcgui.Dialog().ok('Setup interrupted','Original files restored. Estuary remains available. Record this failure before retrying.')
  elif not generated and xbmc.getSkinDir()==FUSE:
   # One repair per revision on old COMPLETE profiles; preserve owner preferences.
   ready=profile/'addon_data/service.kodi.ios.bootstrap/startup-ready.json'
   previous=json.loads(ready.read_text()) if ready.exists() else {}
   if previous.get('revision')!=REVISION or navigation.get('changed_files'):prepare_generated(sync=False)
  if generated:
   ready=profile/'addon_data/service.kodi.ios.bootstrap/startup-ready.json'
   ready.parent.mkdir(parents=True,exist_ok=True);ready.write_text(json.dumps({'revision':REVISION,'host_contract_only':True,'device_verified':False})+'\n')
  stage('complete')
 except Exception as error:
  receipt=failure(error,state['stage']);dest=profile/'addon_data/service.kodi.ios.bootstrap/startup-error.json'
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(receipt,indent=2)+'\n')
  xbmc.log('Kodi iOS setup failed: '+json.dumps(receipt),xbmc.LOGERROR)
  xbmcgui.Dialog().ok('Kodi setup needs review','Automatic setup failed at '+state['stage']+'. Settings and Recovery remain available. Report startup-error.json; do not share credentials.')
 finally:
  window.clearProperty(LOCK)
  invoke('Action(reloadkeymaps)')
  # Exactly one reload after verified generation, never during Keep Skin confirmation.
  if generated and state['stage']=='complete' and xbmc.getSkinDir()==FUSE:invoke('ReloadSkin()')
  # After any reload has settled: the one-time calibration reset, then a quiet check for a newer build.
  if xbmc.getSkinDir()==FUSE and not monitor.waitForAbort(10):
   try:calibration.reset_once(profile,lambda command:xbmc.executebuiltin(command),xbmc.getCondVisibility,monitor.waitForAbort)
   except Exception as error:xbmc.log('Kodi iOS calibration reset skipped: '+type(error).__name__,xbmc.LOGWARNING)
   try:
    if xbmcaddon.Addon().getSettingBool('check_on_start'):updates.run(check_only=True)
   except Exception as error:xbmc.log('Kodi iOS update check skipped: '+type(error).__name__,xbmc.LOGWARNING)
if __name__=='__main__':run()
