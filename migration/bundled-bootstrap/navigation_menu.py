"""Native Kodi navigation menu, independent of widgets/generated hub content."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from navigation import REVISION,DRIVE,UPDATES

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 # Touch-only: no d-pad focus entries. Back is a two-finger swipe left or a long press on empty space.
 entries=[('Home','ActivateWindow(home)'),('Google Drive',DRIVE),('Settings','ActivateWindow(settings)'),('Skin settings','RunScript(service.kodi.ios.bootstrap,skin_settings_page)'),('Movies / TV — TMDb Helper','ActivateWindow(Videos,plugin://plugin.video.themoviedb.helper/,return)'),('Library','ActivateWindow(Videos,plugin://plugin.video.kodi.ios.watch/?action=library&type=movie,return)'),('Add-ons','ActivateWindow(addonbrowser)'),('Rebuild saved views','RunScript(script.skinvariables,action=buildviews,force=true)'),('Rebuild saved menus','RunScript(script.skinvariables,"run_executebuiltin=special://skin/shortcuts/skinvariables-build-templates.json",use_rules)'),('Reload Arctic Fuse','ReloadSkin()'),('Rebuild phone layouts','portrait_refresh'),('Setup / navigation diagnostics',None),('Google Drive network diagnostics','netcheck'),('Check for updates',UPDATES),('AirPlay & Bluetooth devices','airplay'),('Reset screen calibration','calibration'),('Retry Elementum engine','elementum_retry'),('Restore pre-setup configuration (confirmation required)','RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/recover.py)')]
 choice=xbmcgui.Dialog().select('Arctic Fuse iOS — Navigation / Recovery',[e[0] for e in entries])
 if choice<0:return
 action=entries[choice][1]
 if action=='calibration':
  import calibration
  calibration.reset(xbmc.executebuiltin,xbmc.getCondVisibility,xbmc.Monitor().waitForAbort);return
 if action=='airplay':
  import airplay
  path=airplay.library_path(xbmcvfs.translatePath('special://xbmc/'))
  if path:airplay.load(path).kodi_airplay_open()
  else:xbmcgui.Dialog().ok('AirPlay','The AirPlay button is not part of this build.')
  return
 if action=='elementum_retry':
  # Elementum skips its engine after a start that took Kodi down; this clears that so the next launch tries again.
  marker=Path(xbmcvfs.translatePath('special://profile/addon_data/plugin.video.elementum/engine-starting'))
  if marker.exists():marker.unlink()
  import elementum_engine
  api=lambda method,params:json.loads(xbmc.executeJSONRPC(json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params})))
  if elementum_engine.running():xbmcgui.Dialog().ok('Elementum','The engine is already running.');return
  # Not loaded in this session: restarting Elementum's service starts the engine now, no need to reopen Kodi.
  progress=xbmcgui.DialogProgress();progress.create('Elementum','Starting the engine...')
  try:ok=elementum_engine.restart(api,lambda:xbmc.Monitor().waitForAbort(1) or progress.iscanceled())
  finally:progress.close()
  xbmcgui.Dialog().ok('Elementum','The engine is running.' if ok else 'The engine did not start. Send the log (gear menu) so it can be fixed.');return
 if action=='portrait_refresh':
  # Rewrites the portrait pages, the video controls and the source page into the skin Kodi is using.
  import portrait,traceback
  skin=Path(xbmcvfs.translatePath('special://skin/')).resolve();profile=Path(xbmcvfs.translatePath('special://profile/'))
  try:
   changed=list(portrait.build(skin,profile)) if portrait.missing(skin) else portrait.refresh(skin,profile)
  except Exception as error:
   xbmc.log('Kodi iOS portrait rebuild failed: %s\n%s'%(error,traceback.format_exc()),xbmc.LOGERROR)
   xbmcgui.Dialog().ok('Rebuild phone layouts','It failed: %s. Send the log from this menu.'%error);return
  xbmc.log('Kodi iOS portrait rebuild in %s: %d updated'%(skin,len(changed)),xbmc.LOGINFO)
  xbmcgui.Dialog().ok('Rebuild phone layouts','%d files updated in %s.'%(len(changed),skin.name))
  xbmc.executebuiltin('UpdateLocalAddons');xbmc.executebuiltin('ReloadSkin()');return
 if action=='netcheck':
  import netcheck
  try:certifi=os.path.join(xbmcvfs.translatePath(xbmcaddon.Addon('script.module.certifi').getAddonInfo('path')),'lib','certifi','cacert.pem')
  except Exception:certifi=None
  def kodi_fetch(url):
   # Copy, not readBytes(): that returns nothing for responses without a Content-Length.
   temp=Path(xbmcvfs.translatePath('special://temp/'))/'kodi-ios-netcheck.http'
   try:
    if not xbmcvfs.copy(url,str(temp)):raise RuntimeError('Kodi request failed')
    return temp.read_bytes()
   finally:
    if temp.exists():temp.unlink()
  progress=xbmcgui.DialogProgress();progress.create('Google Drive network diagnostics','Testing connections (up to a minute)...')
  try:report=netcheck.run(certifi if certifi and os.path.isfile(certifi) else None,kodi_fetch)
  finally:progress.close()
  state=Path(xbmcvfs.translatePath('special://profile/')).resolve()/'addon_data/service.kodi.ios.bootstrap';state.mkdir(parents=True,exist_ok=True)
  (state/'network-diagnostics.json').write_text(json.dumps(report,indent=2)+'\n');xbmcgui.Dialog().textviewer('Google Drive network diagnostics',json.dumps(report,indent=2));return
 if action:xbmc.executebuiltin(action);return
 report={'revision':REVISION,'skin':xbmc.getSkinDir(),'first_run_flag':xbmc.getCondVisibility('Skin.HasSetting(Home.FirstRun)'),'dependencies':{},'generated_includes':{},'phone_touch_verified':False}
 for id in ['script.skinvariables','script.module.jurialmunkey','plugin.video.themoviedb.helper','plugin.googledrive']:
  report['dependencies'][id]=bool(xbmc.getCondVisibility('System.AddonIsEnabled('+id+')'))
 skin=Path(xbmcvfs.translatePath(xbmcaddon.Addon('skin.arctic.fuse.3').getAddonInfo('path')))
 for name in ['script-skinviewtypes-includes.xml','script-skinvariables-generator-includes-.xml']:
  p=skin/'1080i'/name;report['generated_includes'][name]={'exists':p.is_file(),'bytes':p.stat().st_size if p.is_file() else None}
  if p.is_file() and name=='script-skinviewtypes-includes.xml':report['generated_includes'][name]['rebuild_trigger_still_present']='Exp_ViewTypes_RebuildPending' in p.read_text(errors='replace')
 profile=Path(xbmcvfs.translatePath('special://profile/')).resolve();state=profile/'addon_data/service.kodi.ios.bootstrap';state.mkdir(parents=True,exist_ok=True)
 status=state/'status.json'
 if status.exists():report['bootstrap_status']=json.loads(status.read_text()).get('status')
 (state/'navigation-status.json').write_text(json.dumps(report,indent=2)+'\n');xbmcgui.Dialog().textviewer('Local navigation diagnostics (no account data)',json.dumps(report,indent=2))
if __name__=='__main__':run()
