"""Native Kodi navigation menu, independent of widgets/generated hub content."""
import json,os,sys
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(__file__),'resources','lib'))
from navigation import REVISION,DRIVE

def run():
 import xbmc,xbmcaddon,xbmcgui,xbmcvfs
 if not xbmc.getCondVisibility('System.Platform.IOS'):return
 # Touch-only: no d-pad focus entries. Back is a two-finger swipe left or a long press on empty space.
 entries=[('Home','ActivateWindow(home)'),('Google Drive',DRIVE),('Settings','ActivateWindow(settings)'),('Skin settings','ActivateWindow(skinsettings)'),('Movies / TV — TMDb Helper','ActivateWindow(Videos,plugin://plugin.video.themoviedb.helper/,return)'),('Local videos','ActivateWindow(Videos)'),('Add-ons','ActivateWindow(addonbrowser)'),('Rebuild saved views','RunScript(script.skinvariables,action=buildviews,force=true)'),('Rebuild saved menus','RunScript(script.skinvariables,"run_executebuiltin=special://skin/shortcuts/skinvariables-build-templates.json",use_rules)'),('Reload Arctic Fuse','ReloadSkin()'),('Setup / navigation diagnostics',None),('Restore pre-setup configuration (confirmation required)','RunScript(special://xbmc/addons/service.kodi.ios.bootstrap/recover.py)')]
 choice=xbmcgui.Dialog().select('Arctic Fuse iOS — Navigation / Recovery',[e[0] for e in entries])
 if choice<0:return
 action=entries[choice][1]
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
