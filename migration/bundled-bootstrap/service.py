import json,os,sys,time
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from bootstrap import initialize,restore,ensure_enabled,install_players,elementum_defaults,follow_container,install_payload,umbrella_defaults,media_folders,elementum_library,umbrella_streaming_only
from navigation import upgrade,sync_skin_preferences,update_nodes,phone_defaults,REVISION
from startup import generate,failure,LOCK,FUSE
import airplay,calibration,driveupload,notices,updates,threading,portrait

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
  # e.g. Umbrella, once installed, appears in "How would you like to watch?" through its TMDb Helper player.
  for name in install_players(root,profile,lambda addon:xbmc.getCondVisibility('System.HasAddon('+addon+')')):xbmc.log('Kodi iOS setup added TMDb Helper player '+name,xbmc.LOGINFO)
  # CocoScrapers goes into the writable add-ons folder, where Umbrella looks for its scraper module.
  try:
   copied=install_payload(root,home)
   if copied:
    invoke('UpdateLocalAddons');monitor.waitForAbort(2)
    for addon in copied:api('Addons.SetAddonEnabled',{'addonid':addon,'enabled':True});xbmc.log('Kodi iOS setup installed '+addon,xbmc.LOGINFO)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)'):
    # Umbrella's sources open on the Deck's "Choose a version" page (again after each Umbrella update).
    import umbrella_picker
    # (Not "window": that name is the Home window, used again when setup finishes.)
    source_window=Path(xbmcvfs.translatePath(xbmcaddon.Addon('plugin.video.umbrella').getAddonInfo('path')))/'resources/lib/windows/source_results.py'
    if umbrella_picker.umbrella_hook(str(source_window)):xbmc.log('Kodi iOS setup added the Deck source page to Umbrella',xbmc.LOGINFO)
    elif source_window.is_file() and umbrella_picker.HOOK_MARK not in source_window.read_text(encoding='utf-8',errors='replace'):
     xbmc.log('Kodi iOS setup: this Umbrella version has a different source window; its own list stays',xbmc.LOGWARNING)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)') and xbmc.getCondVisibility('System.HasAddon(script.module.cocoscrapers)'):
    umbrella=xbmcaddon.Addon('plugin.video.umbrella')
    if umbrella_defaults(umbrella.getSetting,umbrella.setSetting):xbmc.log('Kodi iOS setup set Umbrella to CocoScrapers',xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS scraper setup skipped: '+type(error).__name__,xbmc.LOGWARNING)
  if xbmc.getCondVisibility('System.AddonIsEnabled(plugin.video.elementum)'):
   try:
    engine=xbmcaddon.Addon('plugin.video.elementum')
    for key in follow_container(home,engine.getSetting,engine.setSetting):xbmc.log('Kodi iOS setup moved Elementum '+key+' to the current app folder',xbmc.LOGINFO)
    folder=elementum_defaults(updates.updates_folder(home).with_name('Elementum Downloads'),engine.getSetting,engine.setSetting)
    if folder:xbmc.log('Kodi iOS setup set Elementum downloads to '+folder,xbmc.LOGINFO)
   except Exception as error:xbmc.log('Kodi iOS Elementum defaults skipped: '+type(error).__name__,xbmc.LOGWARNING)
  # Elementum videos you choose to keep land in Files › On My iPhone › Kodi › Kodi Downloads › Movies / TV Shows.
  # Umbrella only streams.
  try:
   folders=media_folders(updates.updates_folder(home).with_name('Kodi Downloads'))
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.elementum)'):
    engine=xbmcaddon.Addon('plugin.video.elementum')
    if elementum_library(folders,engine.getSetting,engine.setSetting):xbmc.log('Kodi iOS setup filed Elementum downloads into Movies and TV Shows',xbmc.LOGINFO)
   if xbmc.getCondVisibility('System.HasAddon(plugin.video.umbrella)'):
    umbrella=xbmcaddon.Addon('plugin.video.umbrella')
    if umbrella_streaming_only(folders,umbrella.getSetting,umbrella.setSetting):xbmc.log('Kodi iOS setup set Umbrella back to streaming only',xbmc.LOGINFO)
  except Exception as error:xbmc.log('Kodi iOS download folders skipped: '+type(error).__name__,xbmc.LOGWARNING)
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
 # r11: portrait rows follow the owner's widgets, rotating the phone reloads the matching layout, and Continue
 # Watching follows playback. Its own thread, since the AirPlay watch below also runs for the whole session.
 portrait_thread=threading.Thread(target=portrait.run_service,args=(xbmc,xbmcvfs,monitor,profile,invoke),daemon=True);portrait_thread.start()
 # Kept Elementum videos go to Google Drive in the background, never during playback.
 try:
  if xbmcaddon.Addon().getSettingBool('drive_upload'):
   threading.Thread(target=drive_uploads,args=(monitor,home,profile),daemon=True).start()
 except Exception as error:xbmc.log('Kodi iOS Drive upload unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 # Stays running for the rest of the session: Apple's AirPlay button in the top-right corner during playback.
 try:
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if path and xbmcaddon.Addon().getSettingBool('airplay_button'):
   airplay.watch(airplay.load(path),lambda:xbmc.getCondVisibility(airplay.PLAYING),monitor.waitForAbort)
 except Exception as error:xbmc.log('Kodi iOS AirPlay button unavailable: '+type(error).__name__,xbmc.LOGWARNING)
 while not monitor.waitForAbort(60):pass

def drive_uploads(monitor,home,profile):
 """Every two minutes while Kodi is idle: upload kept Elementum videos with the Google Drive add-on's sign-in."""
 import urllib.parse,xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.HasAddon(plugin.googledrive)'):return
 common=xbmcvfs.translatePath(xbmcaddon.Addon('script.module.clouddrive.common').getAddonInfo('path'))
 if common not in sys.path:sys.path.append(common)
 from clouddrive.common.account import AccountManager
 from clouddrive.common.remote.request import tls_context
 drive_addon=xbmcaddon.Addon('plugin.googledrive')
 accounts=AccountManager(xbmcvfs.translatePath(drive_addon.getAddonInfo('profile')))
 send=driveupload.sender(tls_context())
 def refresh(refresh_token):
  server=(drive_addon.getSetting('sign-in-server') or 'https://drive.signinserver.com').strip().rstrip('/')
  body=urllib.parse.urlencode({'provider':'googledrive','refresh_token':refresh_token}).encode()
  status,_,answer=send('POST',server+'/refresh',body,{'Content-Type':'application/x-www-form-urlencoded'})
  if status!=200:raise RuntimeError('Drive sign-in refresh: HTTP %s'%status)
  return json.loads(answer)
 drive=driveupload.Drive(driveupload.token_source(accounts.get_accounts,accounts.save_account,refresh),send)
 root=str(updates.updates_folder(home).with_name('Kodi Downloads'))
 state=str(profile/'addon_data/service.kodi.ios.bootstrap/drive-uploads.json')
 idle=lambda:not monitor.abortRequested() and not xbmc.Player().isPlayingVideo()
 log=lambda message:xbmc.log('Kodi iOS '+message,xbmc.LOGINFO)
 while not monitor.waitForAbort(120):
  if not idle() or not accounts.get_accounts() or not driveupload.pending(root):continue
  try:
   count=driveupload.run_once(root,drive,state,log,idle,xbmcaddon.Addon().getSettingBool('drive_upload_delete'))
   if count:notices.add(profile,'drive','Uploaded to Google Drive','%d video%s in Kodi Downloads'%(count,'' if count==1 else 's'))
  except driveupload.Stop:pass
  except Exception as error:
   xbmc.log('Kodi iOS Drive upload paused: %s %s'%(type(error).__name__,error),xbmc.LOGWARNING)
   notices.add(profile,'problem','Google Drive upload paused',str(error)[:160])
if __name__=='__main__':run()
