"""Script entry of service.kodi.ios.bootstrap: RunScript(service.kodi.ios.bootstrap[,page[,arguments...]]).

The phone's buttons (bell, Play on TV, speed, Accounts, gear menu...) used to run their scripts by file path, so Kodi
could not tell which add-on they belong to: it logged "Script invoked without an addon" and put every installed
add-on's modules on the Python path before each one started (owner's logs, ISSUE-071). By add-on id it sets up only
this add-on. Without a page this is the recovery script, as the add-on's script entry always was.
"""
import os,runpy,sys
HERE=os.path.dirname(os.path.abspath(__file__))
PAGES=('addon_changelog','addon_search','debrid_signin_page','export_logs','notifications','cast','airplay_settings','speed','accounts_page','profiles_page','favourites_page','favourites_manager','favourites_import_page','anticipated_bell','settings_search','addon_updates','navigation_menu','check_updates','download','library_scan','prepare_check','library_status','tool_pages','refresh_rows','customise_counts','customise_rows','sports','sports_live','sports_jet_run','next_episode','tracks','resume_uploads','section_page','skin_settings_page','upscale_test','upscale_settings','library_manager','library_repair_page','picture_page','copy_problems','quality_choice','sports_upcoming','sports_leagues','sports_edit','sports_game','sports_league','recover')

def target(argv):
 """(script path, its argv) for RunScript's arguments."""
 page=argv[1] if len(argv)>1 and argv[1] in PAGES else 'recover'
 rest=argv[2:] if len(argv)>1 and argv[1] in PAGES else argv[1:]
 path=os.path.join(HERE,page+'.py')
 return path,[path]+list(rest)

if __name__=='__main__':
 path,sys.argv=target(sys.argv)
 import time,xbmc,xbmcvfs
 sys.path.insert(0,os.path.join(HERE,'resources','lib'))
 import diagnostics
 diagnostics.attach(HERE,xbmcvfs.translatePath('special://profile/'))
 write=lambda message:xbmc.log(message,xbmc.LOGINFO)
 page=os.path.basename(path).removesuffix('.py');begun=time.monotonic()
 diagnostics.event(write,'ui','open',page=page)
 if page.startswith('sports') and page not in ('sports_jet_run','sports_remind'):   # a Sports page was opened: source prefetch may run for a few hours (sports_sources_prefetch)
  try:
   import xbmcgui;xbmcgui.Window(10000).setProperty('KodiIOS.SportsSeen',str(time.time()));xbmcgui.Window(10000).setProperty('KodiIOS.SportsPoke','1')   # and the service looks for sources now
  except Exception:pass
 try:runpy.run_path(path,run_name='__main__')
 except Exception as error:
  diagnostics.log_exception(xbmc,'ui',error,page=page);raise
 finally:diagnostics.event(write,'ui','close',page=page,elapsed_s=round(time.monotonic()-begun,3))
