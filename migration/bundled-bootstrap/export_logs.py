"""Save a build-labelled diagnostic log to Files without uploading it anywhere."""
import os,sys
from pathlib import Path
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'resources','lib'))
import diagnostics,updates

def run():
 import xbmc,xbmcgui,xbmcvfs
 root=Path(__file__).resolve().parent
 profile=Path(xbmcvfs.translatePath('special://profile/'))
 home=Path(xbmcvfs.translatePath('special://home/'))
 destination=updates.updates_folder(home).with_name('Kodi Logs')
 try:
  dest=diagnostics.export(root,profile,xbmcvfs.translatePath('special://logpath/'),destination)
  xbmcgui.Dialog().ok('Diagnostic log saved','Build '+diagnostics.build_info(root)['build']+' · '+dest.name+'\nFiles → On My iPhone → Kodi → Kodi Logs. Share this .log when reporting a problem.')
 except Exception as error:
  diagnostics.log_exception(xbmc,'log_export',error)
  xbmcgui.Dialog().ok('Could not save diagnostic log','The original kodi.log is still available. '+type(error).__name__)
if __name__=='__main__':run()
